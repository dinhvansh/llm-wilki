'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import {
  Archive,
  ArrowRightLeft,
  BadgeCheck,
  Boxes,
  FileText,
  Pencil,
  RefreshCw,
  Save,
  Search,
  ShieldAlert,
  ShieldCheck,
  X,
} from 'lucide-react'

import { ErrorState } from '@/components/data-display/error-state'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { StatusBadge } from '@/components/data-display/status-badge'
import { PageHeader } from '@/components/layout/page-header'
import { Input } from '@/components/ui/input'
import type { EntityDetail } from '@/lib/types'
import {
  useArchiveEntity,
  useEntity,
  useEntityExplorer,
  useMergeEntity,
  useRestoreEntity,
  useUpdateEntity,
  useVerifyEntity,
} from '@/hooks/use-pages'

const ENTITY_TYPES = ['all', 'concept', 'technology', 'process', 'organization', 'person', 'location', 'event', 'product'] as const
const VERIFICATION_FILTERS = ['all', 'verified', 'unverified', 'disputed'] as const
const STATUS_FILTERS = ['all', 'active', 'archived'] as const
const DESKTOP_MEDIA_QUERY = '(min-width: 1536px)'
type DetailMode = 'view' | 'edit' | 'merge'

export default function EntityExplorerPage() {
  const [search, setSearch] = useState('')
  const [entityType, setEntityType] = useState<(typeof ENTITY_TYPES)[number]>('all')
  const [verificationFilter, setVerificationFilter] = useState<(typeof VERIFICATION_FILTERS)[number]>('all')
  const [statusFilter, setStatusFilter] = useState<(typeof STATUS_FILTERS)[number]>('active')
  const [selectedEntityId, setSelectedEntityId] = useState('')
  const [draftName, setDraftName] = useState('')
  const [draftType, setDraftType] = useState('concept')
  const [draftDescription, setDraftDescription] = useState('')
  const [draftAliases, setDraftAliases] = useState('')
  const [mergeTargetId, setMergeTargetId] = useState('')
  const [showDetailModal, setShowDetailModal] = useState(false)
  const [detailMode, setDetailMode] = useState<DetailMode>('view')
  const [isDesktopLayout, setIsDesktopLayout] = useState(false)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const mediaQuery = window.matchMedia(DESKTOP_MEDIA_QUERY)
    const syncLayoutMode = (event?: MediaQueryListEvent) => {
      const matches = event?.matches ?? mediaQuery.matches
      setIsDesktopLayout(matches)
      if (matches) {
        setShowDetailModal(false)
        setDetailMode('view')
      }
    }
    syncLayoutMode()
    mediaQuery.addEventListener('change', syncLayoutMode)
    return () => mediaQuery.removeEventListener('change', syncLayoutMode)
  }, [])

  const { data, isLoading, isError, error, refetch } = useEntityExplorer({
    search: search || undefined,
    entityType: entityType === 'all' ? undefined : entityType,
    pageSize: 200,
  })

  const entities = useMemo(() => {
    const items = data?.data ?? []
    return items.filter(entity => {
      const matchesVerification = verificationFilter === 'all' || entity.verificationStatus === verificationFilter
      const matchesStatus = statusFilter === 'all' || entity.status === statusFilter
      return matchesVerification && matchesStatus
    })
  }, [data?.data, statusFilter, verificationFilter])

  useEffect(() => {
    if (!entities.length) {
      setSelectedEntityId('')
      setShowDetailModal(false)
      setDetailMode('view')
      return
    }
    if (!selectedEntityId || !entities.some(entity => entity.id === selectedEntityId)) {
      setSelectedEntityId(entities[0].id)
    }
  }, [entities, selectedEntityId])

  const entityQuery = useEntity(selectedEntityId, { enabled: !!selectedEntityId })
  const updateEntity = useUpdateEntity()
  const verifyEntity = useVerifyEntity()
  const archiveEntity = useArchiveEntity()
  const restoreEntity = useRestoreEntity()
  const mergeEntity = useMergeEntity()
  const selectedEntity = entityQuery.data

  useEffect(() => {
    if (!selectedEntity) return
    setDraftName(selectedEntity.name)
    setDraftType(selectedEntity.entityType)
    setDraftDescription(selectedEntity.description)
    setDraftAliases(selectedEntity.aliases.join(', '))
    setMergeTargetId('')
    setDetailMode('view')
  }, [selectedEntity?.id, selectedEntity])

  const mergeCandidates = (selectedEntity?.mergeCandidates ?? []).filter(candidate => candidate.id !== selectedEntity?.id)

  const saveChanges = async () => {
    if (!selectedEntity) return
    await updateEntity.mutateAsync({
      entityId: selectedEntity.id,
      payload: {
        name: draftName,
        entityType: draftType,
        description: draftDescription,
        aliases: draftAliases.split(',').map(alias => alias.trim()).filter(Boolean),
      },
    })
    setDetailMode('view')
  }

  const confirmMerge = async () => {
    if (!selectedEntity || !mergeTargetId) return
    await mergeEntity.mutateAsync({ entityId: selectedEntity.id, targetEntityId: mergeTargetId })
    setDetailMode('view')
  }

  const selectEntity = (entityId: string) => {
    setSelectedEntityId(entityId)
    setDetailMode('view')
    if (!isDesktopLayout) {
      setShowDetailModal(true)
    }
  }

  const detailPanel = selectedEntity ? (
    <EntityDetailContent
      selectedEntity={selectedEntity}
      mergeCandidates={mergeCandidates}
      detailMode={detailMode}
      draftName={draftName}
      draftType={draftType}
      draftDescription={draftDescription}
      draftAliases={draftAliases}
      mergeTargetId={mergeTargetId}
      onDraftNameChange={setDraftName}
      onDraftTypeChange={setDraftType}
      onDraftDescriptionChange={setDraftDescription}
      onDraftAliasesChange={setDraftAliases}
      onMergeTargetChange={setMergeTargetId}
      onOpenEdit={() => setDetailMode('edit')}
      onOpenMerge={() => setDetailMode('merge')}
      onBackToView={() => setDetailMode('view')}
      onSaveChanges={saveChanges}
      onConfirmMerge={confirmMerge}
      onVerify={() => verifyEntity.mutate({ entityId: selectedEntity.id, verificationStatus: 'verified' })}
      onDispute={() => verifyEntity.mutate({ entityId: selectedEntity.id, verificationStatus: 'disputed' })}
      onArchive={() => archiveEntity.mutate(selectedEntity.id)}
      onRestore={() => restoreEntity.mutate(selectedEntity.id)}
      verifyPending={verifyEntity.isPending}
      archivePending={archiveEntity.isPending}
      restorePending={restoreEntity.isPending}
      savePending={updateEntity.isPending}
      mergePending={mergeEntity.isPending}
    />
  ) : null

  return (
    <div>
      <PageHeader
        title="Entity Explorer"
        description="Govern extracted entities like managed knowledge objects: review them, verify them, merge duplicates, and archive noisy ones."
      />
      <div className="grid gap-6 p-4 lg:p-6 2xl:grid-cols-[320px_minmax(0,1fr)]">
        <section className="space-y-4 rounded-2xl border border-border bg-card p-4">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search entities..." className="h-10 pl-8" />
          </div>
          <div className="grid gap-2 md:grid-cols-2">
            <select value={entityType} onChange={e => setEntityType(e.target.value as (typeof ENTITY_TYPES)[number])} className="h-10 rounded-md border border-input bg-background px-3 text-sm">
              {ENTITY_TYPES.map(option => <option key={option} value={option}>{option === 'all' ? 'All types' : option}</option>)}
            </select>
            <select value={verificationFilter} onChange={e => setVerificationFilter(e.target.value as (typeof VERIFICATION_FILTERS)[number])} className="h-10 rounded-md border border-input bg-background px-3 text-sm">
              {VERIFICATION_FILTERS.map(option => <option key={option} value={option}>{option === 'all' ? 'All verification' : option}</option>)}
            </select>
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value as (typeof STATUS_FILTERS)[number])} className="h-10 rounded-md border border-input bg-background px-3 text-sm md:col-span-2">
              {STATUS_FILTERS.map(option => <option key={option} value={option}>{option === 'all' ? 'All statuses' : option}</option>)}
            </select>
          </div>

          {!isDesktopLayout ? (
            <div className="rounded-xl border border-dashed border-border bg-background/70 px-4 py-3 text-sm text-muted-foreground">
              Chon entity de mo workspace quan tri ngay tai popup, khong mo popup con nua.
            </div>
          ) : null}

          {isLoading ? <LoadingSpinner label="Loading entities..." /> : null}
          {isError ? <ErrorState message={(error as Error)?.message ?? 'Failed to load entities'} onRetry={() => refetch()} /> : null}

          {!isLoading && !isError ? (
            <div className="space-y-3">
              {entities.map(entity => (
                <button
                  key={entity.id}
                  type="button"
                  onClick={() => selectEntity(entity.id)}
                  className={`w-full rounded-xl border p-4 text-left transition-colors ${selectedEntityId === entity.id ? 'border-primary bg-primary/5' : 'border-border bg-background hover:bg-accent/40'}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="font-medium">{entity.name}</div>
                      <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">{entity.description || 'No description available.'}</div>
                    </div>
                    <StatusBadge status={entity.entityType} type="entity" />
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <span className="rounded-full bg-muted px-2 py-1">{entity.sourceCount} sources</span>
                    <span className="rounded-full bg-muted px-2 py-1">{entity.pageCount} pages</span>
                    <span className="rounded-full bg-muted px-2 py-1">{entity.verificationStatus}</span>
                    <span className="rounded-full bg-muted px-2 py-1">{entity.status}</span>
                  </div>
                </button>
              ))}
              {entities.length === 0 ? (
                <div className="rounded-xl border border-dashed border-border bg-background p-8 text-center text-sm text-muted-foreground">
                  <Boxes className="mx-auto mb-3 h-8 w-8" />
                  No entities match the current filters.
                </div>
              ) : null}
            </div>
          ) : null}
        </section>

        <section className="hidden rounded-2xl border border-border bg-card p-5 2xl:block">
          {!selectedEntityId ? (
            <div className="rounded-xl border border-dashed border-border bg-background p-10 text-center text-sm text-muted-foreground">
              Pick an entity to review and manage it.
            </div>
          ) : entityQuery.isLoading ? (
            <LoadingSpinner label="Loading entity detail..." />
          ) : entityQuery.isError ? (
            <ErrorState message={(entityQuery.error as Error)?.message ?? 'Failed to load entity detail'} onRetry={() => entityQuery.refetch()} />
          ) : detailPanel}
        </section>
      </div>

      {showDetailModal && !isDesktopLayout ? (
        <ModalShell title={selectedEntity ? selectedEntity.name : 'Entity workspace'} icon={<Boxes className="h-5 w-5" />} onClose={() => { setShowDetailModal(false); setDetailMode('view') }} size="wide">
          {!selectedEntityId ? (
            <div className="rounded-xl border border-dashed border-border bg-background p-10 text-center text-sm text-muted-foreground">
              Pick an entity to review and manage it.
            </div>
          ) : entityQuery.isLoading ? (
            <LoadingSpinner label="Loading entity detail..." />
          ) : entityQuery.isError ? (
            <ErrorState message={(entityQuery.error as Error)?.message ?? 'Failed to load entity detail'} onRetry={() => entityQuery.refetch()} />
          ) : detailPanel}
        </ModalShell>
      ) : null}
    </div>
  )
}

function EntityDetailContent({
  selectedEntity,
  mergeCandidates,
  detailMode,
  draftName,
  draftType,
  draftDescription,
  draftAliases,
  mergeTargetId,
  onDraftNameChange,
  onDraftTypeChange,
  onDraftDescriptionChange,
  onDraftAliasesChange,
  onMergeTargetChange,
  onOpenEdit,
  onOpenMerge,
  onBackToView,
  onSaveChanges,
  onConfirmMerge,
  onVerify,
  onDispute,
  onArchive,
  onRestore,
  verifyPending,
  archivePending,
  restorePending,
  savePending,
  mergePending,
}: {
  selectedEntity: EntityDetail
  mergeCandidates: EntityDetail['mergeCandidates']
  detailMode: DetailMode
  draftName: string
  draftType: string
  draftDescription: string
  draftAliases: string
  mergeTargetId: string
  onDraftNameChange: (value: string) => void
  onDraftTypeChange: (value: string) => void
  onDraftDescriptionChange: (value: string) => void
  onDraftAliasesChange: (value: string) => void
  onMergeTargetChange: (value: string) => void
  onOpenEdit: () => void
  onOpenMerge: () => void
  onBackToView: () => void
  onSaveChanges: () => Promise<void>
  onConfirmMerge: () => Promise<void>
  onVerify: () => void
  onDispute: () => void
  onArchive: () => void
  onRestore: () => void
  verifyPending: boolean
  archivePending: boolean
  restorePending: boolean
  savePending: boolean
  mergePending: boolean
}) {
  const linkedSources = selectedEntity.linkedSources ?? []
  const linkedPages = selectedEntity.linkedPages ?? []
  const isEditing = detailMode === 'edit'
  const isMerging = detailMode === 'merge'

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border pb-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-2xl font-semibold">{selectedEntity.name}</h2>
            <StatusBadge status={selectedEntity.entityType} type="entity" />
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span className="rounded-full bg-muted px-2 py-1">status: {selectedEntity.status}</span>
            <span className="rounded-full bg-muted px-2 py-1">verification: {selectedEntity.verificationStatus}</span>
            <span className="rounded-full bg-muted px-2 py-1">{selectedEntity.sourceCount} sources</span>
            <span className="rounded-full bg-muted px-2 py-1">{selectedEntity.pageCount} pages</span>
            {selectedEntity.reviewedBy ? <span className="rounded-full bg-muted px-2 py-1">reviewed by {selectedEntity.reviewedBy}</span> : null}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" onClick={onVerify} disabled={verifyPending} className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1.5 text-sm hover:bg-accent disabled:opacity-50">
            <BadgeCheck className="h-4 w-4" />
            Verify
          </button>
          <button type="button" onClick={onDispute} disabled={verifyPending} className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1.5 text-sm hover:bg-accent disabled:opacity-50">
            <ShieldAlert className="h-4 w-4" />
            Dispute
          </button>
          {selectedEntity.status === 'archived' ? (
            <button type="button" onClick={onRestore} disabled={restorePending} className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1.5 text-sm hover:bg-accent disabled:opacity-50">
              <RefreshCw className="h-4 w-4" />
              Restore
            </button>
          ) : (
            <button type="button" onClick={onArchive} disabled={archivePending} className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1.5 text-sm hover:bg-accent disabled:opacity-50">
              <Archive className="h-4 w-4" />
              Archive
            </button>
          )}
        </div>
      </div>

      <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-5">
          <div className="rounded-xl border border-border bg-background p-4">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div className="text-sm font-semibold">Canonical profile</div>
              <div className="flex items-center gap-2">
                {isEditing ? (
                  <>
                    <button type="button" onClick={onBackToView} className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-1.5 text-xs font-medium hover:bg-accent">
                      Cancel
                    </button>
                    <button type="button" onClick={onSaveChanges} disabled={savePending} className="inline-flex items-center gap-2 rounded-full bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground disabled:opacity-60">
                      <Save className="h-3.5 w-3.5" />
                      {savePending ? 'Saving...' : 'Save'}
                    </button>
                  </>
                ) : (
                  <button type="button" onClick={onOpenEdit} className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-1.5 text-xs font-medium hover:bg-accent">
                    <Pencil className="h-3.5 w-3.5" />
                    Edit
                  </button>
                )}
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-xl border border-border/70 bg-card/55 p-3">
                <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Name</div>
                {isEditing ? <Input value={draftName} onChange={e => onDraftNameChange(e.target.value)} className="mt-2" /> : <div className="mt-2 text-sm font-medium">{selectedEntity.name}</div>}
              </div>
              <div className="rounded-xl border border-border/70 bg-card/55 p-3">
                <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Type</div>
                {isEditing ? (
                  <select value={draftType} onChange={e => onDraftTypeChange(e.target.value)} className="mt-2 h-11 w-full rounded-2xl border border-input bg-background px-4 text-sm">
                    {ENTITY_TYPES.filter(option => option !== 'all').map(option => <option key={option} value={option}>{option}</option>)}
                  </select>
                ) : (
                  <div className="mt-2 text-sm font-medium capitalize">{selectedEntity.entityType}</div>
                )}
              </div>
              <div className="rounded-xl border border-border/70 bg-card/55 p-3 md:col-span-2">
                <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Description</div>
                {isEditing ? <textarea value={draftDescription} onChange={e => onDraftDescriptionChange(e.target.value)} rows={5} className="mt-2 w-full rounded-2xl border border-input bg-background px-4 py-3 text-sm" /> : <div className="mt-2 text-sm text-muted-foreground">{selectedEntity.description || 'No canonical description yet.'}</div>}
              </div>
              <div className="rounded-xl border border-border/70 bg-card/55 p-3 md:col-span-2">
                <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Aliases</div>
                {isEditing ? (
                  <Input value={draftAliases} onChange={e => onDraftAliasesChange(e.target.value)} placeholder="Comma-separated aliases" className="mt-2" />
                ) : (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {selectedEntity.aliases.length ? selectedEntity.aliases.map(alias => (
                      <span key={alias} className="rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground">{alias}</span>
                    )) : <span className="text-sm text-muted-foreground">No aliases yet.</span>}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-border bg-background p-4">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <ArrowRightLeft className="h-4 w-4" />
                Merge duplicate into another entity
              </div>
              {isMerging ? (
                <div className="flex items-center gap-2">
                  <button type="button" onClick={onBackToView} className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-1.5 text-xs font-medium hover:bg-accent">
                    Cancel
                  </button>
                  <button type="button" onClick={onConfirmMerge} disabled={!mergeTargetId || mergePending} className="inline-flex items-center gap-2 rounded-full bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground disabled:opacity-60">
                    {mergePending ? 'Merging...' : 'Merge now'}
                  </button>
                </div>
              ) : (
                <button type="button" onClick={onOpenMerge} className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-1.5 text-xs font-medium hover:bg-accent">
                  <ArrowRightLeft className="h-3.5 w-3.5" />
                  Open merge
                </button>
              )}
            </div>
            {isMerging ? (
              <div className="space-y-4">
                <Field label="Merge target">
                  <select value={mergeTargetId} onChange={e => onMergeTargetChange(e.target.value)} className="h-11 w-full rounded-2xl border border-input bg-background px-4 text-sm">
                    <option value="">Select merge target</option>
                    {mergeCandidates.map(candidate => (
                      <option key={candidate.id} value={candidate.id}>
                        {candidate.name} - {candidate.entityType} - {candidate.verificationStatus}
                      </option>
                    ))}
                  </select>
                </Field>
                <div className="rounded-2xl border border-border/70 bg-background/60 p-4 text-sm text-muted-foreground">
                  Merge moves source links, page links, and entity references into the target entity, then marks this entity as merged.
                </div>
              </div>
            ) : (
              <>
                <p className="text-xs text-muted-foreground">
                  Merge moves source links, page links, and entity references into the target, then marks this record as merged.
                </p>
                <div className="mt-3 text-sm text-muted-foreground">
                  {mergeCandidates.length ? `${mergeCandidates.length} possible merge targets available.` : 'No merge targets available for this entity.'}
                </div>
              </>
            )}
          </div>
        </div>

        <div className="space-y-5">
          <div className="rounded-xl border border-border bg-background p-4">
            <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
              <ShieldCheck className="h-4 w-4" />
              Linked sources
            </div>
            <div className="space-y-2">
              {linkedSources.map(source => (
                <Link key={source.id} href={`/sources/${source.id}`} className="block rounded-lg border border-border px-3 py-2 text-sm transition-colors hover:bg-accent">
                  <div className="font-medium">{source.title}</div>
                  <div className="mt-1 text-xs text-muted-foreground">{source.sourceType}</div>
                </Link>
              ))}
              {linkedSources.length === 0 ? <div className="text-sm text-muted-foreground">No linked sources.</div> : null}
            </div>
          </div>

          <div className="rounded-xl border border-border bg-background p-4">
            <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
              <FileText className="h-4 w-4" />
              Linked pages
            </div>
            <div className="space-y-2">
              {linkedPages.map(page => (
                <Link key={page.id} href={`/pages/${page.slug}`} className="block rounded-lg border border-border px-3 py-2 text-sm transition-colors hover:bg-accent">
                  <div className="font-medium">{page.title}</div>
                  <div className="mt-1 text-xs text-muted-foreground">{page.status}</div>
                </Link>
              ))}
              {linkedPages.length === 0 ? <div className="text-sm text-muted-foreground">No linked pages.</div> : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function ModalShell({
  title,
  icon,
  children,
  onClose,
  size = 'default',
}: {
  title: string
  icon: React.ReactNode
  children: React.ReactNode
  onClose: () => void
  size?: 'default' | 'wide'
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/35 px-4 py-8 backdrop-blur-sm">
      <div className={`surface-panel max-h-[calc(100vh-4rem)] w-full overflow-y-auto rounded-[2rem] border border-border/80 p-6 shadow-[0_30px_90px_rgba(25,20,15,0.22)] ${size === 'wide' ? 'max-w-6xl' : 'max-w-3xl'}`}>
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/12 text-primary">{icon}</div>
            <div className="text-lg font-semibold">{title}</div>
          </div>
          <button type="button" onClick={onClose} className="rounded-full p-2 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-6">{children}</div>
      </div>
    </div>
  )
}

function Field({ label, children, className = '' }: { label: string; children: React.ReactNode; className?: string }) {
  return (
    <label className={`block space-y-2 ${className}`}>
      <span className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">{label}</span>
      {children}
    </label>
  )
}
