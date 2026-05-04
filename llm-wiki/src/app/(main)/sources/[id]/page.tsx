'use client'
import { useEffect, useMemo, useState, use } from 'react'
import { useRouter } from 'next/navigation'
import { PageHeader } from '@/components/layout/page-header'
import { StatusBadge } from '@/components/data-display/status-badge'
import { EmptyState } from '@/components/data-display/empty-state'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { ErrorState } from '@/components/data-display/error-state'
import { ConfidenceBar } from '@/components/data-display/confidence-bar'
import { formatDate, formatDateTime, truncate, cn } from '@/lib/utils'
import {
  useAcceptSourceSuggestion,
  useAcceptAllSourceSuggestions,
  useAffectedPages,
  useArchiveSource,
  useCancelSourceJob,
  useChangeSourceSuggestionTarget,
  useMarkSourceStandalone,
  useRejectSourceSuggestion,
  useRejectAllSourceSuggestions,
  useRestoreSource,
  useRetrySourceJob,
  useSource,
  useSourceChunks,
  useSourceClaims,
  useSourceExtractionRuns,
  useSourceEntities,
  useSourceKnowledgeUnits,
  useSourceJobs,
  useSourceSuggestions,
} from '@/hooks/use-sources'
import { useAssignSourceCollection, useCollections } from '@/hooks/use-collections'
import { useAssessDiagramSource, useDiagrams, useGenerateDiagramFromSource } from '@/hooks/use-diagrams'
import { useAuth } from '@/providers/auth-provider'
import Link from 'next/link'
import { Search, FileText, Hash, Eye } from 'lucide-react'

const TABS = ['Overview', 'Chunks', 'Claims', 'Knowledge Units', 'Extraction Runs', 'Entities', 'Related Pages', 'Jobs'] as const
type Tab = typeof TABS[number]

export default function SourceDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const [tab, setTab] = useState<Tab>('Overview')
  const [chunkSearch, setChunkSearch] = useState('')
  const [selectedChunkId, setSelectedChunkId] = useState<string | null>(null)
  const { data: source, isLoading, isError, error, refetch } = useSource(id)
  const { data: collections } = useCollections()
  const assignCollection = useAssignSourceCollection()
  const { data: chunksData, isLoading: chunksLoading } = useSourceChunks(id)
  const { data: claims, isLoading: claimsLoading } = useSourceClaims(id)
  const { data: knowledgeUnits, isLoading: knowledgeUnitsLoading } = useSourceKnowledgeUnits(id)
  const { data: extractionRuns, isLoading: extractionRunsLoading } = useSourceExtractionRuns(id)
  const { data: entities, isLoading: entitiesLoading } = useSourceEntities(id)
  const { data: affectedPages, isLoading: pagesLoading } = useAffectedPages(id)
  const { data: suggestions, isLoading: suggestionsLoading } = useSourceSuggestions(id)
  const { data: jobs, isLoading: jobsLoading } = useSourceJobs(id)
  const acceptSuggestion = useAcceptSourceSuggestion(id)
  const rejectSuggestion = useRejectSourceSuggestion(id)
  const acceptAllSuggestions = useAcceptAllSourceSuggestions(id)
  const rejectAllSuggestions = useRejectAllSourceSuggestions(id)
  const changeSuggestionTarget = useChangeSourceSuggestionTarget(id)
  const markStandalone = useMarkSourceStandalone(id)
  const retryJob = useRetrySourceJob(id)
  const cancelJob = useCancelSourceJob(id)
  const archiveSource = useArchiveSource(id)
  const restoreSource = useRestoreSource(id)
  const generateDiagramMutation = useGenerateDiagramFromSource()
  const { data: bpmAssessment } = useAssessDiagramSource(source?.id ?? '')
  const { data: relatedDiagrams } = useDiagrams({ sourceId: source?.id, pageSize: 20 })
  const { hasRole } = useAuth()
  const router = useRouter()
  const canMutate = hasRole('editor', 'reviewer', 'admin')
  const chunks = useMemo(() => chunksData?.data ?? [], [chunksData?.data])

  useEffect(() => {
    const chunkId = new URLSearchParams(window.location.search).get('chunkId')
    if (chunkId && chunks.some(chunk => chunk.id === chunkId)) {
      setSelectedChunkId(chunkId)
      setTab('Chunks')
    }
  }, [chunks])

  if (isLoading) return <LoadingSpinner label="Loading source..." />
  if (isError) return <ErrorState message={(error as Error)?.message ?? 'Failed to load source'} onRetry={() => refetch()} />
  if (!source) return <ErrorState message="Source not found" />

  const statusSteps = ['uploaded', 'parsing', 'parsed', 'chunked', 'extracted', 'indexed', 'failed']
  const currentStepIndex = statusSteps.indexOf(source.parseStatus)
  const filteredChunks = chunks.filter(chunk =>
    [chunk.sectionTitle, chunk.content, String(chunk.pageNumber ?? '')]
      .join(' ')
      .toLowerCase()
      .includes(chunkSearch.trim().toLowerCase())
  )
  const selectedChunk = chunks.find(chunk => chunk.id === selectedChunkId) ?? filteredChunks[0]
  const sourceOutline = chunks.reduce<Array<{ title: string; count: number; firstChunkId: string }>>((outline, chunk) => {
    const title = chunk.sectionTitle || `Page ${chunk.pageNumber ?? chunk.chunkIndex + 1}`
    const current = outline.find(item => item.title === title)
    if (current) {
      current.count += 1
    } else {
      outline.push({ title, count: 1, firstChunkId: chunk.id })
    }
    return outline
  }, [])
  const pendingSuggestionCount = suggestions?.filter(suggestion => suggestion.status === 'pending').length ?? 0
  const isArchived = Boolean(source.metadataJson?.archived)

  return (
    <div>
      <PageHeader
        title={source.title}
        description={source.description}
        breadcrumbs={[{ label: 'Sources', href: '/sources' }, { label: source.title }]}
        actions={
          <div className="flex items-center gap-2">
            <StatusBadge status={source.sourceType} type="source" />
            <StatusBadge status={source.parseStatus} type="source" />
            <button
              onClick={() => {
                if (!canMutate) return
                generateDiagramMutation.mutate(
                  { sourceId: source.id, payload: { title: `${source.title} BPM Flow`, objective: source.description } },
                  { onSuccess: (diagram) => router.push(`/diagrams/${diagram.slug}`) },
                )
              }}
              disabled={generateDiagramMutation.isPending || !canMutate}
              className="rounded-md border border-input px-3 py-1.5 text-sm hover:bg-accent disabled:opacity-50"
            >
              {generateDiagramMutation.isPending ? 'Generating BPM...' : bpmAssessment?.classification === 'not_recommended' ? 'Generate BPM Anyway' : 'Generate BPM Draft'}
            </button>
            {isArchived ? (
              <button
                onClick={() => restoreSource.mutate()}
                disabled={restoreSource.isPending || !canMutate}
                className="rounded-md border border-input px-3 py-1.5 text-sm hover:bg-accent disabled:opacity-50"
              >
                Restore
              </button>
            ) : (
              <button
                onClick={() => archiveSource.mutate()}
                disabled={archiveSource.isPending || !canMutate}
                className="rounded-md border border-input px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent disabled:opacity-50"
              >
                Archive
              </button>
            )}
          </div>
        }
      />

      {isArchived && (
        <div className="border-b border-amber-200 bg-amber-50 px-6 py-2 text-sm text-amber-800">
          This source is archived. Linked page versions and source links are preserved.
        </div>
      )}

      {/* Tabs */}
      <div className="px-6 border-b border-border">
        <div className="flex gap-1">
          {TABS.map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn('px-3 py-2 text-sm font-medium border-b-2 transition-colors -mb-px', tab === t ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground')}
            >
              {t}
              {t === 'Chunks' && chunksData && <span className="ml-1.5 text-xs text-muted-foreground">({chunksData.total})</span>}
              {t === 'Claims' && claims && <span className="ml-1.5 text-xs text-muted-foreground">({claims.length})</span>}
              {t === 'Knowledge Units' && knowledgeUnits && <span className="ml-1.5 text-xs text-muted-foreground">({knowledgeUnits.length})</span>}
              {t === 'Extraction Runs' && extractionRuns && <span className="ml-1.5 text-xs text-muted-foreground">({extractionRuns.length})</span>}
              {t === 'Jobs' && jobs && <span className="ml-1.5 text-xs text-muted-foreground">({jobs.length})</span>}
            </button>
          ))}
        </div>
      </div>

      <div className="p-6">
        {tab === 'Overview' && (
          <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-6">
            <div className="space-y-6">
            {/* Metadata */}
            <div className="bg-card border border-border rounded-lg p-4 space-y-3">
              <h3 className="text-sm font-semibold">Source Metadata</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                <div><span className="text-muted-foreground">Type:</span> <StatusBadge status={source.sourceType} type="source" /></div>
                <div><span className="text-muted-foreground">Trust:</span> <StatusBadge status={source.trustLevel} type="trust" /></div>
                <div><span className="text-muted-foreground">Uploaded:</span> {formatDateTime(source.uploadedAt)}</div>
                <div><span className="text-muted-foreground">Updated:</span> {formatDateTime(source.updatedAt)}</div>
                <div><span className="text-muted-foreground">By:</span> {source.createdBy}</div>
                {source.url && <div className="md:col-span-2"><span className="text-muted-foreground">URL:</span> <a href={source.url} target="_blank" rel="noreferrer" className="text-primary hover:underline">{source.url}</a></div>}
                {typeof source.metadataJson?.inputConnector === 'string' && (
                  <div><span className="text-muted-foreground">Connector:</span> <span className="capitalize">{String(source.metadataJson.inputConnector).replace(/_/g, ' ')}</span></div>
                )}
                {typeof source.metadataJson?.sourceKind === 'string' && (
                  <div><span className="text-muted-foreground">Kind:</span> <span className="capitalize">{String(source.metadataJson.sourceKind).replace(/_/g, ' ')}</span></div>
                )}
                <div>
                  <span className="text-muted-foreground">Collection:</span>{' '}
                  <select
                    value={source.collectionId ?? ''}
                    onChange={event => assignCollection.mutate({ sourceId: source.id, collectionId: event.target.value || null })}
                    disabled={assignCollection.isPending}
                    className="h-7 max-w-[180px] rounded-md border border-input bg-background px-2 text-xs"
                  >
                    <option value="">Standalone</option>
                    {collections?.map(collection => (
                      <option key={collection.id} value={collection.id}>{collection.name}</option>
                    ))}
                  </select>
                </div>
                <div><span className="text-muted-foreground">Checksum:</span> <code className="text-xs bg-muted px-1 rounded">{truncate(source.checksum, 16)}</code></div>
                {source.fileSize && <div><span className="text-muted-foreground">Size:</span> {(source.fileSize / 1024 / 1024).toFixed(2)} MB</div>}
              </div>
              {source.tags.length > 0 && (
                <div className="flex gap-1.5 flex-wrap">
                  {source.tags.map(tag => (
                    <span key={tag} className="px-2 py-0.5 text-xs bg-secondary text-secondary-foreground rounded-full">{tag}</span>
                  ))}
                </div>
              )}
            </div>

            {/* Parse Progress */}
            <div className="bg-card border border-border rounded-lg p-4">
              <h3 className="text-sm font-semibold mb-4">Processing Pipeline</h3>
              <div className="flex items-center gap-1">
                {statusSteps.map((step, i) => {
                  const isPassed = i <= currentStepIndex
                  const isFailed = source.parseStatus === 'failed'
                  return (
                    <div key={step} className="flex items-center flex-1">
                      <div className="flex flex-col items-center flex-1">
                        <div className={cn(
                          'w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold',
                          isPassed && !isFailed ? 'bg-green-500 text-white' : isFailed && i === statusSteps.indexOf('failed') ? 'bg-red-500 text-white' : 'bg-muted text-muted-foreground'
                        )}>
                          {i + 1}
                        </div>
                        <span className="text-xs mt-1 text-center capitalize" style={{ fontSize: '0.6rem' }}>{step}</span>
                      </div>
                      {i < statusSteps.length - 1 && (
                        <div className={cn('h-0.5 flex-1 mx-1', isPassed ? 'bg-green-500' : 'bg-muted')} />
                      )}
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: 'Chunks', value: chunksData?.total ?? 0 },
                { label: 'Claims', value: claims?.length ?? 0 },
                { label: 'Entities', value: entities?.length ?? 0 },
                { label: 'Related Pages', value: affectedPages?.length ?? 0 },
              ].map(s => (
                <div key={s.label} className="bg-card border border-border rounded-lg p-3 text-center">
                  <div className="text-xl font-bold">{s.value}</div>
                  <div className="text-xs text-muted-foreground">{s.label}</div>
                </div>
              ))}
            </div>
            </div>

            <aside className="space-y-4">
              <div className="bg-card border border-border rounded-lg p-4">
                <div className="mb-3 flex items-center justify-between gap-2">
                  <h3 className="text-sm font-semibold">Ingest Suggestions</h3>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => acceptAllSuggestions.mutate()}
                      disabled={acceptAllSuggestions.isPending || pendingSuggestionCount === 0 || !canMutate}
                      className="rounded-md bg-primary px-2 py-1 text-[11px] font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                    >
                      Accept all
                    </button>
                    <button
                      onClick={() => rejectAllSuggestions.mutate()}
                      disabled={rejectAllSuggestions.isPending || pendingSuggestionCount === 0 || !canMutate}
                      className="rounded-md border border-border px-2 py-1 text-[11px] hover:bg-accent disabled:opacity-50"
                    >
                      Reject all
                    </button>
                  </div>
                </div>
                <button
                  onClick={() => markStandalone.mutate()}
                  disabled={markStandalone.isPending || !canMutate}
                  className="mb-3 w-full rounded-md border border-border px-2 py-1.5 text-[11px] text-muted-foreground hover:bg-accent"
                >
                  Keep source standalone and reject collection/page suggestions
                </button>
                {suggestionsLoading ? (
                  <p className="text-xs text-muted-foreground">Loading suggestions...</p>
                ) : suggestions && suggestions.length > 0 ? (
                  <div className="space-y-3">
                    {suggestions.map(suggestion => {
                      const canChangeCollection = suggestion.targetType === 'collection'
                      const canChangePage = suggestion.targetType === 'page'
                      return (
                        <div key={suggestion.id} className="rounded-lg border border-border bg-background p-3">
                          <div className="mb-2 flex items-start justify-between gap-2">
                            <div>
                              <div className="text-xs font-semibold capitalize">{suggestion.suggestionType.replace(/_/g, ' ')}</div>
                              <div className="text-[11px] text-muted-foreground">{suggestion.targetLabel}</div>
                            </div>
                            <span className={cn(
                              'rounded-full px-2 py-0.5 text-[10px] capitalize',
                              suggestion.status === 'accepted' ? 'bg-green-100 text-green-700' : suggestion.status === 'rejected' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
                            )}>
                              {suggestion.status}
                            </span>
                          </div>
                          <div className="mb-2 flex items-center gap-2">
                            <ConfidenceBar score={suggestion.confidenceScore} className="w-28" />
                          </div>
                          <p className="mb-3 text-xs leading-relaxed text-muted-foreground">{suggestion.reason}</p>
                          {suggestion.status === 'pending' && (canChangeCollection || canChangePage) && (
                            <select
                              value={suggestion.targetId ?? ''}
                              onChange={event => changeSuggestionTarget.mutate({ suggestionId: suggestion.id, targetId: event.target.value || null })}
                              disabled={changeSuggestionTarget.isPending || !canMutate}
                              className="mb-2 h-8 w-full rounded-md border border-input bg-background px-2 text-xs"
                            >
                              <option value="">Choose target...</option>
                              {canChangeCollection && collections?.map(collection => (
                                <option key={collection.id} value={collection.id}>{collection.name}</option>
                              ))}
                              {canChangePage && affectedPages?.map(page => (
                                <option key={page.id} value={page.id}>{page.title}</option>
                              ))}
                            </select>
                          )}
                          {suggestion.status === 'pending' && (
                            <div className="flex gap-2">
                              <button
                                onClick={() => acceptSuggestion.mutate(suggestion.id)}
                                disabled={acceptSuggestion.isPending || !canMutate}
                                className="flex-1 rounded-md bg-primary px-2 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90"
                              >
                                Accept
                              </button>
                              <button
                                onClick={() => rejectSuggestion.mutate(suggestion.id)}
                                disabled={rejectSuggestion.isPending || !canMutate}
                                className="flex-1 rounded-md border border-border px-2 py-1.5 text-xs font-medium hover:bg-accent"
                              >
                                Reject
                              </button>
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">Suggestions appear after ingest or rebuild.</p>
                )}
              </div>

              <div className="bg-card border border-border rounded-lg p-4">
                <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  Source Outline
                </h3>
                {sourceOutline.length > 0 ? (
                  <div className="space-y-1">
                    {sourceOutline.slice(0, 8).map(item => (
                      <button
                        key={item.title}
                        onClick={() => {
                          setSelectedChunkId(item.firstChunkId)
                          setTab('Chunks')
                        }}
                        className="w-full flex items-center justify-between gap-2 px-2 py-1.5 rounded-md text-left text-xs text-muted-foreground hover:bg-accent hover:text-foreground"
                      >
                        <span className="truncate">{item.title}</span>
                        <span>{item.count}</span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">Outline appears after chunking.</p>
                )}
              </div>

              <div className="bg-card border border-border rounded-lg p-4">
                <h3 className="text-sm font-semibold mb-3">Extraction Snapshot</h3>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between"><span className="text-muted-foreground">Claims</span><span>{claims?.length ?? 0}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">Knowledge units</span><span>{knowledgeUnits?.length ?? 0}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">Extraction runs</span><span>{extractionRuns?.length ?? 0}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">Entities</span><span>{entities?.length ?? 0}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">Pages</span><span>{affectedPages?.length ?? 0}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">Chunks</span><span>{chunksData?.total ?? 0}</span></div>
                </div>
              </div>

              <div className="bg-card border border-border rounded-lg p-4">
                <h3 className="text-sm font-semibold mb-3">Linked Process Diagrams</h3>
                {(relatedDiagrams?.data?.length ?? 0) > 0 ? (
                  <div className="space-y-2">
                    {relatedDiagrams?.data.map(diagram => (
                      <Link key={diagram.id} href={`/diagrams/${diagram.slug}`} className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-xs hover:bg-accent">
                        <span>{diagram.title}</span>
                        <StatusBadge status={diagram.status} type="page" />
                      </Link>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">No BPM diagrams linked to this source yet.</p>
                )}
              </div>

              {bpmAssessment && (
                <div className="bg-card border border-border rounded-lg p-4">
                  <h3 className="text-sm font-semibold mb-3">BPM Suitability</h3>
                  <div className="mb-2 flex items-center gap-2 text-xs">
                    <StatusBadge status={bpmAssessment.classification} type="page" />
                    <span className="text-muted-foreground">Score {Math.round(bpmAssessment.score * 100)}%</span>
                  </div>
                  <p className="mb-3 text-xs text-muted-foreground">
                    Recommended action: {bpmAssessment.recommendedAction.replaceAll('_', ' ')}
                  </p>
                  <ul className="space-y-1 text-xs text-muted-foreground">
                    {bpmAssessment.reasons.map((reason, index) => <li key={index}>• {reason}</li>)}
                  </ul>
                </div>
              )}
            </aside>
          </div>
        )}

        {tab === 'Chunks' && (
          chunksLoading ? <LoadingSpinner /> :
          chunksData?.data.length === 0 ? <EmptyState icon="database" title="No chunks extracted" description="Chunks will appear here after processing." /> :
          <div className="grid grid-cols-1 xl:grid-cols-[360px_1fr] gap-4">
            <div className="space-y-3">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
                <input
                  value={chunkSearch}
                  onChange={event => setChunkSearch(event.target.value)}
                  placeholder="Search chunks..."
                  className="w-full h-9 pl-8 pr-2 text-sm border border-input rounded-md bg-background"
                />
              </div>
              <div className="space-y-2 max-h-[68vh] overflow-y-auto pr-1">
                {filteredChunks.map(chunk => (
                  <button
                    key={chunk.id}
                    onClick={() => setSelectedChunkId(chunk.id)}
                    className={cn(
                      'w-full text-left bg-card border rounded-lg p-3 transition-colors',
                      selectedChunk?.id === chunk.id ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
                    )}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <span className="text-xs text-muted-foreground">Chunk #{chunk.chunkIndex + 1}</span>
                        <div className="text-sm font-medium line-clamp-1">{chunk.sectionTitle || 'Untitled section'}</div>
                      </div>
                      <div className="text-xs text-muted-foreground">{chunk.tokenCount} tokens</div>
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">{chunk.content}</p>
                  </button>
                ))}
                {filteredChunks.length === 0 && (
                  <p className="py-8 text-center text-xs text-muted-foreground">No chunks match your search.</p>
                )}
              </div>
            </div>

            <div className="bg-card border border-border rounded-lg min-h-[60vh]">
              {selectedChunk ? (
                <div className="p-5">
                  <div className="flex items-start justify-between gap-3 mb-4">
                    <div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                        <Hash className="w-3.5 h-3.5" />
                        Chunk #{selectedChunk.chunkIndex + 1}
                        {selectedChunk.pageNumber && <span>Page {selectedChunk.pageNumber}</span>}
                      </div>
                      <h3 className="text-base font-semibold">{selectedChunk.sectionTitle || 'Untitled section'}</h3>
                    </div>
                    <div className="text-right text-xs text-muted-foreground">
                      <div>{selectedChunk.tokenCount} tokens</div>
                      <div>span {selectedChunk.spanStart}-{selectedChunk.spanEnd}</div>
                    </div>
                  </div>
                  <div className="rounded-lg border border-border bg-background p-4">
                    <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
                      <Eye className="w-3.5 h-3.5" />
                      Source Text
                    </div>
                    <p className="text-sm leading-7 whitespace-pre-wrap">{selectedChunk.content}</p>
                  </div>
                </div>
              ) : (
                <EmptyState icon="database" title="No chunk selected" description="Select a chunk from the list to inspect its full text and span." />
              )}
            </div>
          </div>
        )}

        {tab === 'Claims' && (
          claimsLoading ? <LoadingSpinner /> :
          !claims || claims.length === 0 ? <EmptyState icon="alert" title="No claims extracted" description="Claims will appear here after extraction." /> :
          <div className="space-y-3">
            {claims.map(claim => (
              <div key={claim.id} className="bg-card border border-border rounded-lg p-4">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <StatusBadge status={claim.claimType} type="claim" />
                    <StatusBadge status={claim.canonicalStatus} type="page" />
                    {Boolean(claim.metadataJson?.isLowConfidence) && (
                      <span className="rounded-full bg-yellow-100 px-2 py-0.5 text-xs text-yellow-800">Low confidence</span>
                    )}
                    {claim.extractionMethod && (
                      <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">{claim.extractionMethod}</span>
                    )}
                  </div>
                  <ConfidenceBar score={claim.confidenceScore} className="w-24" />
                </div>
                <p className="text-sm leading-relaxed">{claim.text}</p>
                {claim.topic && <p className="text-xs text-muted-foreground mt-2">Topic: {claim.topic}</p>}
                {(typeof claim.evidenceSpanStart === 'number' || typeof claim.evidenceSpanEnd === 'number') && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Evidence span: {String(claim.evidenceSpanStart ?? '?')} - {String(claim.evidenceSpanEnd ?? '?')}
                  </p>
                )}
                {Array.isArray(claim.metadataJson?.vagueTerms) && (claim.metadataJson?.vagueTerms as unknown[]).length > 0 && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Vague terms: {(claim.metadataJson?.vagueTerms as string[]).join(', ')}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}

        {tab === 'Knowledge Units' && (
          knowledgeUnitsLoading ? <LoadingSpinner /> :
          !knowledgeUnits || knowledgeUnits.length === 0 ? <EmptyState icon="database" title="No knowledge units yet" description="Knowledge units appear after semantic extraction runs complete." /> :
          <div className="space-y-3">
            {knowledgeUnits.map(unit => (
              <div key={unit.id} className="bg-card border border-border rounded-lg p-4">
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <StatusBadge status={unit.unitType} type="claim" />
                    <StatusBadge status={unit.status} type="page" />
                    <StatusBadge status={unit.reviewStatus} type="page" />
                    <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">{unit.canonicalStatus}</span>
                  </div>
                  <ConfidenceBar score={unit.confidenceScore} className="w-24" />
                </div>
                <div className="mb-1 text-sm font-medium">{unit.title || unit.unitType}</div>
                <p className="text-sm leading-relaxed">{unit.text}</p>
                <div className="mt-2 space-y-1 text-xs text-muted-foreground">
                  {unit.topic && <p>Topic: {unit.topic}</p>}
                  {unit.claimId && <p>Claim link: {unit.claimId}</p>}
                  {unit.sourceChunkId && <p>Source chunk: {unit.sourceChunkId}</p>}
                  {(typeof unit.evidenceSpanStart === 'number' || typeof unit.evidenceSpanEnd === 'number') && (
                    <p>Evidence span: {String(unit.evidenceSpanStart ?? '?')} - {String(unit.evidenceSpanEnd ?? '?')}</p>
                  )}
                  {Array.isArray(unit.metadataJson?.vagueTerms) && (unit.metadataJson?.vagueTerms as unknown[]).length > 0 && (
                    <p>Vague terms: {(unit.metadataJson?.vagueTerms as string[]).join(', ')}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === 'Extraction Runs' && (
          extractionRunsLoading ? <LoadingSpinner /> :
          !extractionRuns || extractionRuns.length === 0 ? <EmptyState icon="database" title="No extraction runs yet" description="Extraction run history will appear after ingest or rebuild." /> :
          <div className="space-y-3">
            {extractionRuns.map(run => (
              <div key={run.id} className="bg-card border border-border rounded-lg p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold">{run.runType.replaceAll('_', ' ')}</span>
                      <StatusBadge status={run.status} type="page" />
                      <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">{run.method}</span>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Task profile: {run.taskProfile || 'n/a'} · Provider: {run.modelProvider || 'none'} · Model: {run.modelName || 'n/a'}
                    </p>
                  </div>
                  <div className="text-right text-xs text-muted-foreground">
                    <div>{run.inputChunkCount} chunks in</div>
                    <div>{run.outputCount} outputs</div>
                  </div>
                </div>
                <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs text-muted-foreground">
                  <div>
                    <p>Started: {formatDateTime(run.startedAt)}</p>
                    <p>Finished: {run.finishedAt ? formatDateTime(run.finishedAt) : 'n/a'}</p>
                  </div>
                  <div>
                    <p>Prompt version: {run.promptVersion || 'n/a'}</p>
                    {run.errorMessage && <p className="text-red-600">Error: {run.errorMessage}</p>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === 'Entities' && (
          entitiesLoading ? <LoadingSpinner /> :
          !entities || entities.length === 0 ? <EmptyState icon="database" title="No entities found" description="Entities extracted from this source will appear here." /> :
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {entities.map(entity => (
              <div key={entity.id} className="bg-card border border-border rounded-lg p-3">
                <div className="flex items-start justify-between mb-1">
                  <span className="font-medium text-sm">{entity.name}</span>
                  <StatusBadge status={entity.entityType} type="entity" />
                </div>
                <p className="text-xs text-muted-foreground line-clamp-2">{entity.description}</p>
                {entity.aliases.length > 0 && (
                  <div className="flex gap-1 flex-wrap mt-1">
                    {entity.aliases.slice(0, 3).map(a => (
                      <span key={a} className="text-xs bg-muted px-1.5 py-0.5 rounded">{a}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {tab === 'Related Pages' && (
          pagesLoading ? <LoadingSpinner /> :
          !affectedPages || affectedPages.length === 0 ? <EmptyState icon="file-text" title="No related pages" description="Pages derived from this source will appear here." /> :
          <div className="space-y-3">
            {affectedPages.map(page => (
              <Link key={page.id} href={`/pages/${page.slug}`} className="block bg-card border border-border rounded-lg p-4 hover:border-primary/50 transition-colors">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium">{page.title}</span>
                  <StatusBadge status={page.status} type="page" />
                  <StatusBadge status={page.pageType} type="pageType" />
                </div>
                <p className="text-xs text-muted-foreground line-clamp-1">{page.summary}</p>
              </Link>
            ))}
          </div>
        )}

        {tab === 'Jobs' && (
          jobsLoading ? <LoadingSpinner /> :
          !jobs || jobs.length === 0 ? <EmptyState icon="database" title="No jobs yet" description="Ingest and rebuild jobs for this source will appear here." /> :
          <div className="space-y-4">
            {jobs.map(job => (
              <div key={job.id} className="bg-card border border-border rounded-lg p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-semibold">{job.id}</span>
                      <span className={cn(
                        'rounded-full px-2 py-0.5 text-xs font-medium capitalize',
                        job.status === 'completed' ? 'bg-green-100 text-green-700' :
                        job.status === 'failed' ? 'bg-red-100 text-red-700' :
                        job.status === 'running' ? 'bg-blue-100 text-blue-700' :
                        job.status === 'canceled' ? 'bg-slate-100 text-slate-700' :
                        'bg-amber-100 text-amber-700'
                      )}>
                        {job.status}
                      </span>
                      <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium capitalize text-muted-foreground">{job.jobType}</span>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Started {formatDateTime(job.startedAt)}
                      {job.finishedAt ? ` · Finished ${formatDateTime(job.finishedAt)}` : ''}
                    </p>
                    {job.errorMessage && <p className="mt-2 text-sm text-red-600">{job.errorMessage}</p>}
                  </div>
                  <div className="flex gap-2">
                    {job.status === 'failed' && (
                      <button
                        onClick={() => retryJob.mutate(job.id)}
                        disabled={retryJob.isPending}
                        className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                      >
                        Retry
                      </button>
                    )}
                    {(job.status === 'pending' || job.status === 'running') && (
                      <button
                        onClick={() => cancelJob.mutate(job.id)}
                        disabled={cancelJob.isPending}
                        className="rounded-md border border-border px-3 py-1.5 text-xs font-medium hover:bg-accent disabled:opacity-50"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
                <div className="mt-4">
                  <div className="mb-1 flex items-center justify-between text-xs text-muted-foreground">
                    <span>Progress</span>
                    <span>{job.progressPercent ?? 0}%</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-muted">
                    <div
                      className={cn(
                        'h-full rounded-full transition-all',
                        job.status === 'failed' ? 'bg-red-500' :
                        job.status === 'canceled' ? 'bg-slate-400' :
                        job.status === 'completed' ? 'bg-green-500' :
                        'bg-blue-500'
                      )}
                      style={{ width: `${Math.max(0, Math.min(job.progressPercent ?? 0, 100))}%` }}
                    />
                  </div>
                  {job.actor && <p className="mt-1 text-xs text-muted-foreground">Actor: {job.actor}</p>}
                </div>
                {job.stepsJson && job.stepsJson.length > 0 && (
                  <div className="mt-4 rounded-lg border border-border bg-background p-3">
                    <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Structured Steps</p>
                    <div className="space-y-2">
                      {job.stepsJson.map((step, index) => (
                        <div key={`${job.id}-step-${index}`} className="flex items-start gap-3 rounded-md bg-muted/30 px-2 py-2">
                          <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-background text-[10px] font-semibold text-muted-foreground">{index + 1}</span>
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="text-xs font-semibold capitalize">{step.name.replace(/_/g, ' ')}</span>
                              <span className={cn(
                                'rounded-full px-1.5 py-0.5 text-[10px] capitalize',
                                step.status === 'completed' ? 'bg-green-100 text-green-700' :
                                step.status === 'failed' ? 'bg-red-100 text-red-700' :
                                step.status === 'running' ? 'bg-blue-100 text-blue-700' :
                                step.status === 'canceled' ? 'bg-slate-100 text-slate-700' :
                                'bg-amber-100 text-amber-700'
                              )}>
                                {step.status}
                              </span>
                              {typeof step.progress === 'number' && <span className="text-[10px] text-muted-foreground">{step.progress}%</span>}
                            </div>
                            {Object.keys(step.details ?? {}).length > 0 && (
                              <p className="mt-1 break-words font-mono text-[11px] leading-relaxed text-muted-foreground">
                                {JSON.stringify(step.details)}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <div className="mt-4 rounded-lg border border-border bg-background p-3">
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Job Logs</p>
                  {job.logsJson.length > 0 ? (
                    <ol className="space-y-1">
                      {job.logsJson.map((line, index) => (
                        <li key={`${job.id}-${index}`} className="flex gap-2 font-mono text-xs text-muted-foreground">
                          <span className="w-6 shrink-0 text-right text-muted-foreground/60">{index + 1}</span>
                          <span>{line}</span>
                        </li>
                      ))}
                    </ol>
                  ) : (
                    <p className="text-xs text-muted-foreground">No logs recorded for this job.</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
