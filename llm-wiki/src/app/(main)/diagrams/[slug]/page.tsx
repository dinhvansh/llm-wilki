'use client'
import { use, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { GitBranch, History, Save } from 'lucide-react'
import Link from 'next/link'

import { ErrorState } from '@/components/data-display/error-state'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { StatusBadge } from '@/components/data-display/status-badge'
import { DrawioEmbed } from '@/components/diagram/drawio-embed'
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
import type { Diagram } from '@/lib/types'
import { formatDateTime } from '@/lib/utils'

function splitLines(value: string) {
  return value.split('\n').map(item => item.trim()).filter(Boolean)
}

function stringifySpec(value: Record<string, unknown>) {
  return JSON.stringify(value ?? {}, null, 2)
}

function buildDraftSnapshot(input: {
  title: string
  objective: string
  owner: string
  collectionId: string
  actorLanes: string
  entryPoints: string
  exitPoints: string
  sourceIds: string
  sourcePageIds: string
  relatedDiagramIds: string
  drawioXml: string
  specJson: string
}) {
  return JSON.stringify({
    title: input.title.trim(),
    objective: input.objective.trim(),
    owner: input.owner.trim(),
    collectionId: input.collectionId || '',
    actorLanes: splitLines(input.actorLanes),
    entryPoints: splitLines(input.entryPoints),
    exitPoints: splitLines(input.exitPoints),
    sourceIds: splitLines(input.sourceIds),
    sourcePageIds: splitLines(input.sourcePageIds),
    relatedDiagramIds: splitLines(input.relatedDiagramIds),
    drawioXml: input.drawioXml.trim(),
    specJson: input.specJson.trim(),
  })
}

function snapshotFromDiagram(diagram: Diagram) {
  return buildDraftSnapshot({
    title: diagram.title,
    objective: diagram.objective,
    owner: diagram.owner,
    collectionId: diagram.collectionId ?? '',
    actorLanes: diagram.actorLanes.join('\n'),
    entryPoints: diagram.entryPoints.join('\n'),
    exitPoints: diagram.exitPoints.join('\n'),
    sourceIds: diagram.sourceIds.join('\n'),
    sourcePageIds: diagram.sourcePageIds.join('\n'),
    relatedDiagramIds: diagram.relatedDiagramIds.join('\n'),
    drawioXml: diagram.drawioXml,
    specJson: stringifySpec(diagram.specJson ?? {}),
  })
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

  const [title, setTitle] = useState('')
  const [objective, setObjective] = useState('')
  const [owner, setOwner] = useState('')
  const [collectionId, setCollectionId] = useState('')
  const [actorLanes, setActorLanes] = useState('')
  const [entryPoints, setEntryPoints] = useState('')
  const [exitPoints, setExitPoints] = useState('')
  const [sourceIds, setSourceIds] = useState('')
  const [sourcePageIds, setSourcePageIds] = useState('')
  const [relatedDiagramIds, setRelatedDiagramIds] = useState('')
  const [drawioXml, setDrawioXml] = useState('')
  const [specJson, setSpecJson] = useState('{}')
  const [changeSummary, setChangeSummary] = useState('Updated diagram')
  const [currentVersion, setCurrentVersion] = useState(0)
  const [saveStatus, setSaveStatus] = useState('Draft loaded from backend')
  const [lastSavedSnapshot, setLastSavedSnapshot] = useState('')
  const [lastSavedAt, setLastSavedAt] = useState('')
  const [editorEvent, setEditorEvent] = useState('idle')
  const [editorAutosaveTick, setEditorAutosaveTick] = useState(0)
  const autosaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const hasHydratedRef = useRef(false)

  const textAreas: Array<{ label: string; value: string; setter: (value: string) => void }> = [
    { label: 'Actor lanes', value: actorLanes, setter: setActorLanes },
    { label: 'Entry points', value: entryPoints, setter: setEntryPoints },
    { label: 'Exit points', value: exitPoints, setter: setExitPoints },
    { label: 'Source IDs', value: sourceIds, setter: setSourceIds },
    { label: 'Source page IDs', value: sourcePageIds, setter: setSourcePageIds },
    { label: 'Related diagram IDs', value: relatedDiagramIds, setter: setRelatedDiagramIds },
  ]

  useEffect(() => {
    if (!diagram) return
    setTitle(diagram.title)
    setObjective(diagram.objective)
    setOwner(diagram.owner)
    setCollectionId(diagram.collectionId ?? '')
    setActorLanes(diagram.actorLanes.join('\n'))
    setEntryPoints(diagram.entryPoints.join('\n'))
    setExitPoints(diagram.exitPoints.join('\n'))
    setSourceIds(diagram.sourceIds.join('\n'))
    setSourcePageIds(diagram.sourcePageIds.join('\n'))
    setRelatedDiagramIds(diagram.relatedDiagramIds.join('\n'))
    setDrawioXml(diagram.drawioXml)
    setSpecJson(stringifySpec(diagram.specJson ?? {}))
    setCurrentVersion(diagram.currentVersion)
    setLastSavedSnapshot(snapshotFromDiagram(diagram))
    setLastSavedAt(diagram.updatedAt)
    setSaveStatus('Draft loaded from backend')
    hasHydratedRef.current = true
  }, [diagram])

  const draftSnapshot = useMemo(
    () =>
      buildDraftSnapshot({
        title,
        objective,
        owner,
        collectionId,
        actorLanes,
        entryPoints,
        exitPoints,
        sourceIds,
        sourcePageIds,
        relatedDiagramIds,
        drawioXml,
        specJson,
      }),
    [title, objective, owner, collectionId, actorLanes, entryPoints, exitPoints, sourceIds, sourcePageIds, relatedDiagramIds, drawioXml, specJson],
  )
  const isDirty = hasHydratedRef.current && draftSnapshot !== lastSavedSnapshot

  const parseSpec = useCallback(() => {
    return JSON.parse(specJson || '{}') as Record<string, unknown>
  }, [specJson])

  const saveDraft = useCallback(
    async (summaryOverride?: string, silent = false) => {
      if (!diagram) return false
      let parsedSpec: Record<string, unknown> = {}
      try {
        parsedSpec = parseSpec()
      } catch {
        window.alert('Spec JSON is invalid.')
        setSaveStatus('Cannot save: invalid spec JSON')
        return false
      }
      const effectiveSummary = (summaryOverride ?? changeSummary).trim() || 'Updated diagram'
      try {
        const updated = await updateMutation.mutateAsync({
          diagramId: diagram.id,
          payload: {
            title,
            objective,
            owner,
            collectionId: collectionId || null,
            actorLanes: splitLines(actorLanes),
            entryPoints: splitLines(entryPoints),
            exitPoints: splitLines(exitPoints),
            sourceIds: splitLines(sourceIds),
            sourcePageIds: splitLines(sourcePageIds),
            relatedDiagramIds: splitLines(relatedDiagramIds),
            specJson: parsedSpec,
            drawioXml,
            changeSummary: effectiveSummary,
            expectedVersion: currentVersion || diagram.currentVersion,
          },
        })
        setCurrentVersion(updated.currentVersion)
        setLastSavedSnapshot(snapshotFromDiagram(updated))
        setLastSavedAt(updated.updatedAt)
        setSaveStatus(silent ? 'Autosaved draw.io draft to backend' : 'Draft saved to backend')
        return true
      } catch (saveError) {
        setSaveStatus('Save failed')
        if (!silent) {
          const message = saveError instanceof Error ? saveError.message : 'Failed to save diagram draft'
          window.alert(message)
        }
        return false
      }
    },
    [
      actorLanes,
      changeSummary,
      collectionId,
      currentVersion,
      diagram,
      drawioXml,
      entryPoints,
      exitPoints,
      objective,
      owner,
      parseSpec,
      relatedDiagramIds,
      sourceIds,
      sourcePageIds,
      title,
      updateMutation,
    ],
  )

  useEffect(() => {
    function onBeforeUnload(event: BeforeUnloadEvent) {
      if (!isDirty) return
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', onBeforeUnload)
    return () => window.removeEventListener('beforeunload', onBeforeUnload)
  }, [isDirty])

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

  useEffect(() => {
    if (!editorAutosaveTick || !isDirty) return
    if (autosaveTimerRef.current) {
      clearTimeout(autosaveTimerRef.current)
    }
    autosaveTimerRef.current = setTimeout(() => {
      void saveDraft('Autosave draw.io editor changes', true)
    }, 1500)
    return () => {
      if (autosaveTimerRef.current) {
        clearTimeout(autosaveTimerRef.current)
        autosaveTimerRef.current = null
      }
    }
  }, [editorAutosaveTick, isDirty, saveDraft])

  if (isLoading) return <LoadingSpinner label="Loading diagram..." />
  if (isError) return <ErrorState message={(error as Error)?.message ?? 'Failed to load diagram'} onRetry={() => refetch()} />
  if (!diagram) return <ErrorState message="Diagram not found" />

  let specObject: Record<string, unknown> = {}
  try {
    specObject = parseSpec()
  } catch {
    specObject = {}
  }
  const openQuestions = Array.isArray(specObject.openQuestions) ? (specObject.openQuestions as string[]) : []
  const validation = (specObject.validation ?? {}) as { isValid?: boolean; warnings?: string[] }
  const citations = Array.isArray(specObject.citations) ? (specObject.citations as Array<Record<string, unknown>>) : []
  const nodeCitations = Array.isArray(specObject.nodeCitations) ? (specObject.nodeCitations as Array<Record<string, unknown>>) : []
  const edgeCitations = Array.isArray(specObject.edgeCitations) ? (specObject.edgeCitations as Array<Record<string, unknown>>) : []
  const scopeSummary = typeof specObject.scopeSummary === 'string' ? specObject.scopeSummary : ''
  const reviewStatus = typeof specObject.reviewStatus === 'string' ? specObject.reviewStatus : 'needs_review'
  const reviewNotes = Array.isArray(specObject.reviewNotes) ? (specObject.reviewNotes as Array<Record<string, unknown>>) : []

  return (
    <div className="flex flex-col min-h-full">
      <PageHeader
        title={diagram.title}
        description={diagram.objective || 'BPM process artifact backed by draw.io XML and diagram spec.'}
        breadcrumbs={[{ label: 'Process Diagrams', href: '/diagrams' }, { label: diagram.title }]}
        actions={
          <div className="flex items-center gap-2">
            <StatusBadge status={diagram.status} type="page" />
            <StatusBadge status={reviewStatus} type="page" />
            {diagram.status === 'draft' && reviewStatus !== 'in_review' && (
              <button
                onClick={() => submitReviewMutation.mutate(diagram.id)}
                className="px-3 py-1.5 text-sm rounded-md border border-input hover:bg-accent"
              >
                Submit Review
              </button>
            )}
            {diagram.status === 'in_review' && (
              <>
                <button
                  onClick={() => approveReviewMutation.mutate({ diagramId: diagram.id, comment: 'Flow structure approved.' })}
                  className="px-3 py-1.5 text-sm rounded-md bg-blue-600 text-white hover:bg-blue-700"
                >
                  Approve Review
                </button>
                <button
                  onClick={() => requestChangesMutation.mutate({ diagramId: diagram.id, comment: 'Check citations and subprocess splits.' })}
                  className="px-3 py-1.5 text-sm rounded-md border border-input hover:bg-accent"
                >
                  Request Changes
                </button>
              </>
            )}
            {diagram.status === 'draft' ? (
              <button
                onClick={() => publishMutation.mutate(diagram.id)}
                className="px-3 py-1.5 text-sm rounded-md bg-green-600 text-white hover:bg-green-700"
              >
                Publish
              </button>
            ) : (
              <button
                onClick={() => unpublishMutation.mutate(diagram.id)}
                className="px-3 py-1.5 text-sm rounded-md bg-amber-600 text-white hover:bg-amber-700"
              >
                Unpublish
              </button>
            )}
            <button
              onClick={() => void saveDraft()}
              disabled={updateMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              {updateMutation.isPending ? 'Saving...' : 'Save Draft'}
            </button>
          </div>
        }
      />

      <div className="border-b border-border bg-card/40 px-6 py-2 text-xs text-muted-foreground">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <span>{isDirty ? 'Unsaved changes' : 'Saved'}</span>
          <span>{saveStatus}</span>
          <span>Editor: {editorEvent}</span>
          <span>Version: v{currentVersion || diagram.currentVersion}</span>
          <span>Last saved: {lastSavedAt ? formatDateTime(lastSavedAt) : 'Not yet'}</span>
          <span>Shortcut: Ctrl/Cmd+S</span>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_340px] gap-0 flex-1">
        <div className="p-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">Title</span>
              <input value={title} onChange={event => setTitle(event.target.value)} className="w-full h-10 rounded-md border border-input bg-background px-3" />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">Owner</span>
              <input value={owner} onChange={event => setOwner(event.target.value)} className="w-full h-10 rounded-md border border-input bg-background px-3" />
            </label>
          </div>

          <label className="space-y-1 text-sm block">
            <span className="text-muted-foreground">Objective</span>
            <textarea value={objective} onChange={event => setObjective(event.target.value)} className="w-full min-h-24 rounded-md border border-input bg-background px-3 py-2" />
          </label>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">Collection</span>
              <select value={collectionId} onChange={event => setCollectionId(event.target.value)} className="w-full h-10 rounded-md border border-input bg-background px-3">
                <option value="">Standalone</option>
                {collections?.map(collection => (
                  <option key={collection.id} value={collection.id}>{collection.name}</option>
                ))}
              </select>
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">Change summary</span>
              <input value={changeSummary} onChange={event => setChangeSummary(event.target.value)} className="w-full h-10 rounded-md border border-input bg-background px-3" />
            </label>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {textAreas.map(({ label, value, setter }) => (
              <label key={label} className="space-y-1 text-sm block">
                <span className="text-muted-foreground">{label}</span>
                <textarea value={value} onChange={event => setter(event.target.value)} className="w-full min-h-24 rounded-md border border-input bg-background px-3 py-2" />
              </label>
            ))}
          </div>

          <label className="space-y-1 text-sm block">
            <span className="text-muted-foreground">Diagram spec JSON</span>
            <textarea value={specJson} onChange={event => setSpecJson(event.target.value)} className="w-full min-h-[24rem] rounded-md border border-input bg-background px-3 py-2 font-mono text-xs" />
          </label>

          <DrawioEmbed
            title={title || diagram.title}
            xml={drawioXml}
            onXmlChange={(nextXml) => {
              setDrawioXml(nextXml)
            }}
            onEditorEvent={(eventName) => {
              setEditorEvent(eventName)
              if (eventName === 'autosave' || eventName === 'save') {
                setEditorAutosaveTick(value => value + 1)
              }
            }}
          />

          <label className="space-y-1 text-sm block">
            <span className="text-muted-foreground">draw.io XML snapshot</span>
            <textarea value={drawioXml} onChange={event => setDrawioXml(event.target.value)} className="w-full min-h-[20rem] rounded-md border border-input bg-background px-3 py-2 font-mono text-xs" />
          </label>
        </div>

        <aside className="border-l border-border bg-card/50 p-5 space-y-5">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold mb-2">
              <GitBranch className="w-4 h-4" />
              Diagram metadata
            </div>
            <div className="space-y-1 text-xs text-muted-foreground">
              <div>Slug: {diagram.slug}</div>
              <div>Version: v{currentVersion || diagram.currentVersion}</div>
              <div>Updated: {formatDateTime(lastSavedAt || diagram.updatedAt)}</div>
              {diagram.publishedAt && <div>Published: {formatDateTime(diagram.publishedAt)}</div>}
            </div>
          </div>

          {(scopeSummary || openQuestions.length > 0 || citations.length > 0 || (validation.warnings?.length ?? 0) > 0) && (
            <div className="space-y-3">
              {scopeSummary && (
                <div>
                  <div className="text-sm font-semibold mb-1">Scope summary</div>
                  <p className="text-xs leading-relaxed text-muted-foreground">{scopeSummary}</p>
                </div>
              )}
              {openQuestions.length > 0 && (
                <div>
                  <div className="text-sm font-semibold mb-1">Open questions</div>
                  <ul className="space-y-1 text-xs text-muted-foreground">
                    {openQuestions.map((item, index) => <li key={`${item}-${index}`}>- {item}</li>)}
                  </ul>
                </div>
              )}
              {(validation.warnings?.length ?? 0) > 0 && (
                <div>
                  <div className="text-sm font-semibold mb-1">Validation</div>
                  <div className="mb-1 text-xs text-muted-foreground">
                    {validation.isValid ? 'Ready' : 'Needs reviewer attention'}
                  </div>
                  <ul className="space-y-1 text-xs text-muted-foreground">
                    {(validation.warnings ?? []).map((item, index) => <li key={`${item}-${index}`}>- {item}</li>)}
                  </ul>
                </div>
              )}
              {citations.length > 0 && (
                <div>
                  <div className="text-sm font-semibold mb-1">Citations</div>
                  <div className="space-y-2">
                    {citations.slice(0, 4).map((item, index) => (
                      <div key={`${String(item.chunkId ?? item.claimId ?? index)}`} className="rounded-md border border-border p-2">
                        <div className="text-xs font-medium">{String(item.sourceTitle ?? 'Source')}</div>
                        <div className="text-[11px] text-muted-foreground">{String(item.chunkSectionTitle ?? item.claimText ?? 'Evidence')}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {nodeCitations.length > 0 && (
                <div>
                  <div className="text-sm font-semibold mb-1">Node traceability</div>
                  <div className="space-y-2">
                    {nodeCitations.slice(0, 5).map((item, index) => {
                      const citation = (item.citation ?? {}) as Record<string, unknown>
                      return (
                        <div key={`${String(item.nodeId ?? index)}`} className="rounded-md border border-border p-2 text-xs">
                          <div className="font-medium">{String(item.nodeId ?? 'node')}</div>
                          <div className="text-muted-foreground">{String(citation.sourceTitle ?? citation.claimText ?? 'Evidence')}</div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
              {edgeCitations.length > 0 && (
                <div>
                  <div className="text-sm font-semibold mb-1">Edge traceability</div>
                  <div className="space-y-2">
                    {edgeCitations.slice(0, 5).map((item, index) => {
                      const citation = (item.citation ?? {}) as Record<string, unknown>
                      return (
                        <div key={`${String(item.edgeKey ?? index)}`} className="rounded-md border border-border p-2 text-xs">
                          <div className="font-medium">{String(item.edgeKey ?? 'edge')}</div>
                          <div className="text-muted-foreground">{String(citation.sourceTitle ?? citation.claimText ?? 'Evidence')}</div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {(diagram.relatedDiagrams.length > 0 || diagram.linkedPages.length > 0 || diagram.linkedSources.length > 0) && (
            <div className="space-y-3">
              {diagram.relatedDiagrams.length > 0 && (
                <div>
                  <div className="text-sm font-semibold mb-2">Related flows</div>
                  <div className="space-y-2">
                    {diagram.relatedDiagrams.map(item => (
                      <Link key={item.id} href={`/diagrams/${item.slug}`} className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-xs hover:bg-accent">
                        <span>{item.title}</span>
                        <StatusBadge status={item.status} type="page" />
                      </Link>
                    ))}
                  </div>
                </div>
              )}
              {diagram.linkedPages.length > 0 && (
                <div>
                  <div className="text-sm font-semibold mb-2">Linked pages</div>
                  <div className="space-y-2">
                    {diagram.linkedPages.map(item => (
                      <Link key={item.id} href={`/pages/${item.slug}`} className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-xs hover:bg-accent">
                        <span>{item.title}</span>
                        <StatusBadge status={item.status} type="page" />
                      </Link>
                    ))}
                  </div>
                </div>
              )}
              {diagram.linkedSources.length > 0 && (
                <div>
                  <div className="text-sm font-semibold mb-2">Linked sources</div>
                  <div className="space-y-2">
                    {diagram.linkedSources.map(item => (
                      <Link key={item.id} href={`/sources/${item.id}`} className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-xs hover:bg-accent">
                        <span>{item.title}</span>
                        <span className="text-muted-foreground">{item.sourceType}</span>
                      </Link>
                    ))}
                  </div>
                </div>
              )}
              {reviewNotes.length > 0 && (
                <div>
                  <div className="text-sm font-semibold mb-2">Review notes</div>
                  <div className="space-y-2">
                    {reviewNotes.map((item, index) => (
                      <div key={index} className="rounded-md border border-border p-2 text-xs">
                        <div className="font-medium">{String(item.actor ?? 'Reviewer')}</div>
                        <div className="text-muted-foreground">{String(item.comment ?? '')}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          <div>
            <div className="flex items-center gap-2 text-sm font-semibold mb-2">
              <History className="w-4 h-4" />
              Versions
            </div>
            <div className="space-y-2">
              {versions?.map(version => (
                <div key={version.id} className="rounded-md border border-border p-2">
                  <div className="text-sm font-medium">v{version.versionNo}</div>
                  <div className="text-xs text-muted-foreground">{version.changeSummary || 'No summary'}</div>
                  <div className="text-xs text-muted-foreground">{formatDateTime(version.createdAt)} by {version.createdByAgentOrUser}</div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="text-sm font-semibold mb-2">Audit</div>
            <div className="space-y-2">
              {auditLogs?.map(log => (
                <div key={log.id} className="rounded-md border border-border p-2">
                  <div className="text-sm font-medium">{log.action}</div>
                  <div className="text-xs text-muted-foreground">{log.summary}</div>
                  <div className="text-xs text-muted-foreground">{formatDateTime(log.createdAt)} by {log.actor}</div>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}
