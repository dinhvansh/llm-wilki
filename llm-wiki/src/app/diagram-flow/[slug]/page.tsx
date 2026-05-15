'use client'

import { use, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, Save } from 'lucide-react'

import { AuthGuard } from '@/components/auth/auth-guard'
import { ErrorState } from '@/components/data-display/error-state'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { OPENFLOWKIT_EMBED_URL, OpenFlowKitEmbed, type OpenFlowKitEmbedHandle } from '@/components/diagram/openflowkit-embed'
import { useDiagram, useUpdateDiagram } from '@/hooks/use-diagrams'
import { emptyFlowDocument, firstFlowPage, updateFlowMetadata } from '@/lib/openflow'
import type { FlowDocument } from '@/lib/types'
import { formatDateTime } from '@/lib/utils'

function flowActorLanes(document: FlowDocument): string[] {
  return (firstFlowPage(document).lanes ?? []).map(lane => lane.label).filter(Boolean)
}

function flowEntryPoints(document: FlowDocument): string[] {
  return firstFlowPage(document).nodes.filter(node => node.type === 'start').map(node => node.label).filter(Boolean)
}

function flowExitPoints(document: FlowDocument): string[] {
  return firstFlowPage(document).nodes.filter(node => node.type === 'end').map(node => node.label).filter(Boolean)
}

function DiagramFlowWorkspace({ slug }: { slug: string }) {
  const { data: diagram, isLoading, isError, error, refetch } = useDiagram(slug)
  const updateMutation = useUpdateDiagram()
  const openFlowKitRef = useRef<OpenFlowKitEmbedHandle | null>(null)
  const [flowDocument, setFlowDocument] = useState<FlowDocument>(() => emptyFlowDocument('Untitled flow'))
  const [saveStatus, setSaveStatus] = useState('Loading flow...')
  const [lastSavedAt, setLastSavedAt] = useState('')

  useEffect(() => {
    if (!diagram) return
    const nextDocument = diagram.flowDocument?.pages?.length
      ? diagram.flowDocument
      : emptyFlowDocument(diagram.title, diagram.objective, diagram.owner)
    const withMetadata = updateFlowMetadata(nextDocument, {
      title: diagram.title,
      objective: diagram.objective,
      owner: diagram.owner,
      sourceIds: diagram.sourceIds,
      sourcePageIds: diagram.sourcePageIds,
    })
    setFlowDocument(withMetadata)
    setLastSavedAt(diagram.updatedAt)
    setSaveStatus('OpenFlow document loaded')
  }, [diagram])

  const title = diagram?.title ?? 'OpenFlow editor'
  const detailHref = useMemo(() => (diagram ? `/diagrams/${diagram.slug}` : '/diagrams'), [diagram])

  const persistDocument = useCallback(async (document: FlowDocument) => {
    if (!diagram) return
    const nextDocument = updateFlowMetadata(document, {
      title: diagram.title,
      objective: diagram.objective,
      owner: diagram.owner,
      sourceIds: diagram.sourceIds,
      sourcePageIds: diagram.sourcePageIds,
    })
    try {
      const updated = await updateMutation.mutateAsync({
        diagramId: diagram.id,
        payload: {
          title: diagram.title,
          objective: diagram.objective,
          owner: diagram.owner,
          collectionId: diagram.collectionId ?? null,
          actorLanes: flowActorLanes(nextDocument),
          entryPoints: flowEntryPoints(nextDocument),
          exitPoints: flowExitPoints(nextDocument),
          sourceIds: diagram.sourceIds,
          sourcePageIds: diagram.sourcePageIds,
          relatedDiagramIds: diagram.relatedDiagramIds,
          flowDocument: nextDocument,
          changeSummary: 'Updated OpenFlow document from full-screen editor',
          expectedVersion: diagram.currentVersion,
        },
      })
      setFlowDocument(updated.flowDocument)
      setLastSavedAt(updated.updatedAt)
      setSaveStatus('OpenFlow document saved')
    } catch (saveError) {
      setSaveStatus(saveError instanceof Error ? saveError.message : 'Save failed')
    }
  }, [diagram, updateMutation])

  const saveDraft = useCallback(async () => {
    if (!openFlowKitRef.current) return
    try {
      const embeddedDocument = await openFlowKitRef.current.requestSave()
      await persistDocument(embeddedDocument)
    } catch (saveError) {
      setSaveStatus(saveError instanceof Error ? saveError.message : 'OpenFlowKit save failed')
    }
  }, [persistDocument])

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        event.preventDefault()
        void saveDraft()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [saveDraft])

  if (!OPENFLOWKIT_EMBED_URL) {
    return <ErrorState message="OpenFlowKit embed is not configured." />
  }
  if (isLoading) return <LoadingSpinner label="Loading flow..." />
  if (isError) return <ErrorState message={(error as Error)?.message ?? 'Failed to load flow'} onRetry={() => refetch()} />
  if (!diagram) return <ErrorState message="Flow not found" />

  return (
    <div className="flex h-screen min-h-screen flex-col bg-background">
      <header className="flex min-h-14 flex-wrap items-center justify-between gap-3 border-b border-border bg-card px-4 py-2">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <Link href={detailHref} className="flex h-9 w-9 items-center justify-center rounded-md border border-input hover:bg-accent" aria-label="Back to diagram detail">
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <div className="min-w-0">
              <h1 className="truncate text-sm font-semibold text-foreground">{title}</h1>
              <div className="truncate text-xs text-muted-foreground">
                {saveStatus} | Last saved: {lastSavedAt ? formatDateTime(lastSavedAt) : 'Not yet'}
              </div>
            </div>
          </div>
        </div>
        <button
          onClick={() => void saveDraft()}
          disabled={updateMutation.isPending}
          className="flex h-9 items-center gap-2 rounded-md bg-primary px-3 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          <Save className="h-4 w-4" />
          {updateMutation.isPending ? 'Saving...' : 'Save'}
        </button>
      </header>
      <main className="min-h-0 flex-1">
        <OpenFlowKitEmbed
          ref={openFlowKitRef}
          diagramId={diagram.id}
          title={diagram.title}
          objective={diagram.objective}
          owner={diagram.owner}
          document={flowDocument}
          onDocumentSaved={setFlowDocument}
          onStatusChange={setSaveStatus}
        />
      </main>
    </div>
  )
}

export default function DiagramFlowPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params)
  return (
    <AuthGuard>
      <DiagramFlowWorkspace slug={slug} />
    </AuthGuard>
  )
}
