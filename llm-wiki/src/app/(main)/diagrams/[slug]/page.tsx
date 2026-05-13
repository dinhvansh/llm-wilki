'use client'

import { use, useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { GitBranch, History, Plus, Save, Trash2 } from 'lucide-react'

import { ErrorState } from '@/components/data-display/error-state'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { StatusBadge } from '@/components/data-display/status-badge'
import { OpenFlowCanvas } from '@/components/diagram/openflow-canvas'
import { PageHeader } from '@/components/layout/page-header'
import {
  useApproveDiagramReview,
  useDiagram,
  useDiagramAudit,
  useDiagramVersions,
  usePublishDiagram,
  useRequestDiagramChanges,
  useSubmitDiagramReview,
  useUnpublishDiagram,
  useUpdateDiagram,
} from '@/hooks/use-diagrams'
import { useCollections } from '@/hooks/use-collections'
import { emptyFlowDocument, firstFlowPage, makeFlowNode, updateFirstFlowPage, updateFlowMetadata } from '@/lib/openflow'
import type { FlowDocument, FlowNode } from '@/lib/types'
import { formatDateTime } from '@/lib/utils'

function snapshot(value: unknown) {
  return JSON.stringify(value ?? {})
}

function flowActorLanes(document: FlowDocument): string[] {
  return (firstFlowPage(document).lanes ?? []).map(lane => lane.label).filter(Boolean)
}

function flowEntryPoints(document: FlowDocument): string[] {
  return firstFlowPage(document).nodes.filter(node => node.type === 'start').map(node => node.label).filter(Boolean)
}

function flowExitPoints(document: FlowDocument): string[] {
  return firstFlowPage(document).nodes.filter(node => node.type === 'end').map(node => node.label).filter(Boolean)
}

function nodeTypeOptions() {
  return ['start', 'task', 'decision', 'handoff', 'end']
}

export default function DiagramDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params)
  const { data: diagram, isLoading, isError, error, refetch } = useDiagram(slug)
  const { data: versions } = useDiagramVersions(diagram?.id ?? '')
  const { data: auditLogs } = useDiagramAudit(diagram?.id ?? '')
  const { data: collections } = useCollections()
  const publishMutation = usePublishDiagram()
  const unpublishMutation = useUnpublishDiagram()
  const submitReviewMutation = useSubmitDiagramReview()
  const approveReviewMutation = useApproveDiagramReview()
  const requestChangesMutation = useRequestDiagramChanges()
  const updateMutation = useUpdateDiagram()

  const [flowDocument, setFlowDocument] = useState<FlowDocument>(() => emptyFlowDocument('Untitled flow'))
  const [title, setTitle] = useState('')
  const [objective, setObjective] = useState('')
  const [owner, setOwner] = useState('')
  const [collectionId, setCollectionId] = useState('')
  const [changeSummary, setChangeSummary] = useState('Updated OpenFlow document')
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [lastSavedSnapshot, setLastSavedSnapshot] = useState('')
  const [lastSavedAt, setLastSavedAt] = useState('')
  const [saveStatus, setSaveStatus] = useState('Loaded')

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
    setTitle(diagram.title)
    setObjective(diagram.objective)
    setOwner(diagram.owner)
    setCollectionId(diagram.collectionId ?? '')
    setLastSavedSnapshot(snapshot(withMetadata))
    setLastSavedAt(diagram.updatedAt)
    setSaveStatus('OpenFlow document loaded')
  }, [diagram])

  const selectedNode = useMemo(() => {
    if (!selectedNodeId) return null
    return firstFlowPage(flowDocument).nodes.find(node => node.id === selectedNodeId) ?? null
  }, [flowDocument, selectedNodeId])

  const metadata = flowDocument.metadata ?? {}
  const reviewStatus = metadata.reviewStatus ?? 'needs_review'
  const validation = metadata.validation ?? {}
  const openQuestions = metadata.openQuestions ?? []
  const citations = metadata.citations ?? []
  const isDirty = snapshot(flowDocument) !== lastSavedSnapshot || title !== (metadata.title ?? title) || objective !== (metadata.objective ?? objective)

  const syncMetadata = useCallback(
    (document: FlowDocument) =>
      updateFlowMetadata(document, {
        title,
        objective,
        owner,
        sourceIds: diagram?.sourceIds ?? [],
        sourcePageIds: diagram?.sourcePageIds ?? [],
      }),
    [diagram?.sourceIds, diagram?.sourcePageIds, objective, owner, title],
  )

  const saveDraft = useCallback(async () => {
    if (!diagram) return
    const nextDocument = syncMetadata(flowDocument)
    try {
      const updated = await updateMutation.mutateAsync({
        diagramId: diagram.id,
        payload: {
          title,
          objective,
          owner,
          collectionId: collectionId || null,
          actorLanes: flowActorLanes(nextDocument),
          entryPoints: flowEntryPoints(nextDocument),
          exitPoints: flowExitPoints(nextDocument),
          sourceIds: diagram.sourceIds,
          sourcePageIds: diagram.sourcePageIds,
          relatedDiagramIds: diagram.relatedDiagramIds,
          specJson: diagram.specJson,
          flowDocument: nextDocument,
          drawioXml: '',
          changeSummary,
          expectedVersion: diagram.currentVersion,
        },
      })
      setFlowDocument(updated.flowDocument)
      setLastSavedSnapshot(snapshot(updated.flowDocument))
      setLastSavedAt(updated.updatedAt)
      setSaveStatus('OpenFlow document saved')
    } catch (saveError) {
      setSaveStatus(saveError instanceof Error ? saveError.message : 'Save failed')
    }
  }, [changeSummary, collectionId, diagram, flowDocument, objective, owner, syncMetadata, title, updateMutation])

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

  if (isLoading) return <LoadingSpinner label="Loading flow..." />
  if (isError) return <ErrorState message={(error as Error)?.message ?? 'Failed to load flow'} onRetry={() => refetch()} />
  if (!diagram) return <ErrorState message="Flow not found" />

  const page = firstFlowPage(flowDocument)

  function updateNode(nodeId: string, patch: Partial<FlowNode>) {
    setFlowDocument(current => {
      const currentPage = firstFlowPage(current)
      return updateFirstFlowPage(current, {
        nodes: currentPage.nodes.map(node => node.id === nodeId ? { ...node, ...patch } : node),
      })
    })
  }

  function addNode(type = 'task') {
    setFlowDocument(current => {
      const currentPage = firstFlowPage(current)
      const node = makeFlowNode(currentPage.nodes.length, type)
      setSelectedNodeId(node.id)
      return updateFirstFlowPage(current, { nodes: [...currentPage.nodes, node] })
    })
  }

  function deleteSelectedNode() {
    if (!selectedNodeId) return
    setFlowDocument(current => {
      const currentPage = firstFlowPage(current)
      return updateFirstFlowPage(current, {
        nodes: currentPage.nodes.filter(node => node.id !== selectedNodeId),
        edges: currentPage.edges.filter(edge => edge.source !== selectedNodeId && edge.target !== selectedNodeId),
      })
    })
    setSelectedNodeId(null)
  }

  return (
    <div className="flex min-h-full flex-col">
      <PageHeader
        title={title || diagram.title}
        description={objective || 'OpenFlow document'}
        breadcrumbs={[{ label: 'Process Diagrams', href: '/diagrams' }, { label: title || diagram.title }]}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={diagram.status} type="page" />
            <StatusBadge status={reviewStatus} type="page" />
            {diagram.status === 'draft' && reviewStatus !== 'in_review' && (
              <button onClick={() => submitReviewMutation.mutate(diagram.id)} className="rounded-md border border-input px-3 py-1.5 text-sm hover:bg-accent">Submit Review</button>
            )}
            {diagram.status === 'in_review' && (
              <>
                <button onClick={() => approveReviewMutation.mutate({ diagramId: diagram.id, comment: 'OpenFlow structure approved.' })} className="rounded-md bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700">Approve</button>
                <button onClick={() => requestChangesMutation.mutate({ diagramId: diagram.id, comment: 'Check flow structure and citations.' })} className="rounded-md border border-input px-3 py-1.5 text-sm hover:bg-accent">Request Changes</button>
              </>
            )}
            {diagram.status === 'draft' ? (
              <button onClick={() => publishMutation.mutate(diagram.id)} className="rounded-md bg-green-600 px-3 py-1.5 text-sm text-white hover:bg-green-700">Publish</button>
            ) : (
              <button onClick={() => unpublishMutation.mutate(diagram.id)} className="rounded-md bg-amber-600 px-3 py-1.5 text-sm text-white hover:bg-amber-700">Unpublish</button>
            )}
            <button onClick={() => void saveDraft()} disabled={updateMutation.isPending} className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
              <Save className="h-4 w-4" />
              {updateMutation.isPending ? 'Saving...' : 'Save'}
            </button>
          </div>
        }
      />

      <div className="border-b border-border bg-card/50 px-6 py-2 text-xs text-muted-foreground">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <span>{isDirty ? 'Unsaved changes' : 'Saved'}</span>
          <span>{saveStatus}</span>
          <span>Engine: OpenFlow</span>
          <span>Version: v{diagram.currentVersion}</span>
          <span>Last saved: {lastSavedAt ? formatDateTime(lastSavedAt) : 'Not yet'}</span>
        </div>
      </div>

      <div className="grid min-h-[calc(100vh-13rem)] flex-1 grid-cols-1 xl:grid-cols-[280px_minmax(0,1fr)_340px]">
        <aside className="border-r border-border bg-card/55 p-4">
          <div className="space-y-3">
            <label className="block space-y-1 text-xs font-medium text-muted-foreground">
              Title
              <input value={title} onChange={event => setTitle(event.target.value)} className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground" />
            </label>
            <label className="block space-y-1 text-xs font-medium text-muted-foreground">
              Objective
              <textarea value={objective} onChange={event => setObjective(event.target.value)} rows={4} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground" />
            </label>
            <label className="block space-y-1 text-xs font-medium text-muted-foreground">
              Owner
              <input value={owner} onChange={event => setOwner(event.target.value)} className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground" />
            </label>
            <label className="block space-y-1 text-xs font-medium text-muted-foreground">
              Collection
              <select value={collectionId} onChange={event => setCollectionId(event.target.value)} className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground">
                <option value="">Standalone</option>
                {collections?.map(collection => <option key={collection.id} value={collection.id}>{collection.name}</option>)}
              </select>
            </label>
            <label className="block space-y-1 text-xs font-medium text-muted-foreground">
              Change summary
              <input value={changeSummary} onChange={event => setChangeSummary(event.target.value)} className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground" />
            </label>
          </div>

          <div className="mt-6 border-t border-border pt-4">
            <div className="mb-2 text-xs font-semibold uppercase text-muted-foreground">Add</div>
            <div className="grid grid-cols-2 gap-2">
              {nodeTypeOptions().map(type => (
                <button key={type} onClick={() => addNode(type)} className="flex items-center justify-center gap-1 rounded-md border border-border bg-background px-2 py-2 text-xs hover:bg-accent">
                  <Plus className="h-3.5 w-3.5" />
                  {type}
                </button>
              ))}
            </div>
          </div>
        </aside>

        <main className="min-h-[34rem]">
          <OpenFlowCanvas document={flowDocument} onChange={setFlowDocument} onSelectNode={setSelectedNodeId} />
        </main>

        <aside className="overflow-y-auto border-l border-border bg-card/60 p-4">
          <div className="space-y-5">
            <section>
              <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
                <GitBranch className="h-4 w-4" />
                Properties
              </div>
              {selectedNode ? (
                <div className="space-y-3">
                  <label className="block space-y-1 text-xs font-medium text-muted-foreground">
                    Label
                    <input value={selectedNode.label} onChange={event => updateNode(selectedNode.id, { label: event.target.value })} className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground" />
                  </label>
                  <label className="block space-y-1 text-xs font-medium text-muted-foreground">
                    Type
                    <select value={selectedNode.type} onChange={event => updateNode(selectedNode.id, { type: event.target.value })} className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground">
                      {nodeTypeOptions().map(type => <option key={type} value={type}>{type}</option>)}
                    </select>
                  </label>
                  <label className="block space-y-1 text-xs font-medium text-muted-foreground">
                    Owner
                    <input value={selectedNode.owner ?? ''} onChange={event => updateNode(selectedNode.id, { owner: event.target.value })} className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground" />
                  </label>
                  <button onClick={deleteSelectedNode} className="flex h-9 items-center gap-2 rounded-md border border-destructive/40 px-3 text-sm text-destructive hover:bg-destructive/10">
                    <Trash2 className="h-4 w-4" />
                    Delete node
                  </button>
                </div>
              ) : (
                <div className="rounded-md border border-dashed border-border p-3 text-sm text-muted-foreground">Select a node to edit it.</div>
              )}
            </section>

            {(validation.warnings?.length ?? 0) > 0 || openQuestions.length > 0 || citations.length > 0 ? (
              <section className="space-y-3 border-t border-border pt-4">
                {(validation.warnings?.length ?? 0) > 0 && (
                  <div>
                    <div className="mb-1 text-sm font-semibold">Validation</div>
                    <ul className="space-y-1 text-xs text-muted-foreground">
                      {(validation.warnings ?? []).map((item, index) => <li key={`${item}-${index}`}>- {item}</li>)}
                    </ul>
                  </div>
                )}
                {openQuestions.length > 0 && (
                  <div>
                    <div className="mb-1 text-sm font-semibold">Open questions</div>
                    <ul className="space-y-1 text-xs text-muted-foreground">
                      {openQuestions.map((item, index) => <li key={`${item}-${index}`}>- {item}</li>)}
                    </ul>
                  </div>
                )}
                {citations.length > 0 && (
                  <div>
                    <div className="mb-1 text-sm font-semibold">Citations</div>
                    <div className="space-y-2">
                      {citations.slice(0, 5).map((item, index) => (
                        <div key={String(item.chunkId ?? item.claimId ?? index)} className="rounded-md border border-border p-2 text-xs">
                          <div className="font-medium">{String(item.sourceTitle ?? 'Source')}</div>
                          <div className="text-muted-foreground">{String(item.chunkSectionTitle ?? item.claimText ?? item.snippet ?? 'Evidence')}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </section>
            ) : null}

            <section className="border-t border-border pt-4">
              <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
                <History className="h-4 w-4" />
                Versions
              </div>
              <div className="space-y-2">
                {versions?.slice(0, 6).map(version => (
                  <div key={version.id} className="rounded-md border border-border p-2 text-xs">
                    <div className="font-medium">v{version.versionNo}</div>
                    <div className="text-muted-foreground">{version.changeSummary || 'No summary'}</div>
                    <div className="text-muted-foreground">{formatDateTime(version.createdAt)}</div>
                  </div>
                ))}
              </div>
            </section>

            {(diagram.relatedDiagrams.length > 0 || diagram.linkedPages.length > 0 || diagram.linkedSources.length > 0) && (
              <section className="space-y-3 border-t border-border pt-4">
                {diagram.linkedPages.map(item => (
                  <Link key={item.id} href={`/pages/${item.slug}`} className="block rounded-md border border-border p-2 text-xs hover:bg-accent">{item.title}</Link>
                ))}
                {diagram.linkedSources.map(item => (
                  <Link key={item.id} href={`/sources/${item.id}`} className="block rounded-md border border-border p-2 text-xs hover:bg-accent">{item.title}</Link>
                ))}
              </section>
            )}

            {auditLogs?.length ? (
              <section className="border-t border-border pt-4">
                <div className="mb-2 text-sm font-semibold">Audit</div>
                <div className="space-y-2">
                  {auditLogs.slice(0, 5).map(log => (
                    <div key={log.id} className="rounded-md border border-border p-2 text-xs">
                      <div className="font-medium">{log.action}</div>
                      <div className="text-muted-foreground">{log.summary}</div>
                    </div>
                  ))}
                </div>
              </section>
            ) : null}
          </div>
        </aside>
      </div>
    </div>
  )
}
