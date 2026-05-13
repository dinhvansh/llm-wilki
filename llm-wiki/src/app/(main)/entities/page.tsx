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
  const [showEditModal, setShowEditModal] = useState(false)
  const [showMergeModal, setShowMergeModal] = useState(false)

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
    setShowEditModal(false)
    setShowMergeModal(false)
  }, [selectedEntity?.id, selectedEntity])

  const linkedPages = selectedEntity?.linkedPages ?? []
  const linkedSources = selectedEntity?.linkedSources ?? []
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
  }

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

          {isLoading ? <LoadingSpinner label="Loading entities..." /> : null}
          {isError ? <ErrorState message={(error as Error)?.message ?? 'Failed to load entities'} onRetry={() => refetch()} /> : null}

          {!isLoading && !isError ? (
            <div className="space-y-3">
              {entities.map(entity => (
                <button
                  key={entity.id}
                  type="button"
                  onClick={() => setSelectedEntityId(entity.id)}
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

        <section className="rounded-2xl border border-border bg-card p-5">
          {!selectedEntityId ? (
            <div className="rounded-xl border border-dashed border-border bg-background p-10 text-center text-sm text-muted-foreground">
              Pick an entity to review and manage it.
            </div>
          ) : entityQuery.isLoading ? (
            <LoadingSpinner label="Loading entity detail..." />
          ) : entityQuery.isError ? (
            <ErrorState message={(entityQuery.error as Error)?.message ?? 'Failed to load entity detail'} onRetry={() => entityQuery.refetch()} />
          ) : selectedEntity ? (
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
                  <button
                    type="button"
                    onClick={() => verifyEntity.mutate({ entityId: selectedEntity.id, verificationStatus: 'verified' })}
                    disabled={verifyEntity.isPending}
                    className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1.5 text-sm hover:bg-accent disabled:opacity-50"
                  >
                    <BadgeCheck className="h-4 w-4" />
                    Verify
                  </button>
                  <button
                    type="button"
                    onClick={() => verifyEntity.mutate({ entityId: selectedEntity.id, verificationStatus: 'disputed' })}
                    disabled={verifyEntity.isPending}
                    className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1.5 text-sm hover:bg-accent disabled:opacity-50"
                  >
                    <ShieldAlert className="h-4 w-4" />
                    Dispute
                  </button>
                  {selectedEntity.status === 'archived' ? (
                    <button
                      type="button"
                      onClick={() => restoreEntity.mutate(selectedEntity.id)}
                      disabled={restoreEntity.isPending}
                      className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1.5 text-sm hover:bg-accent disabled:opacity-50"
                    >
                      <RefreshCw className="h-4 w-4" />
                      Restore
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={() => archiveEntity.mutate(selectedEntity.id)}
                      disabled={archiveEntity.isPending}
                      className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1.5 text-sm hover:bg-accent disabled:opacity-50"
                    >
                      <Archive className="h-4 w-4" />
                      Archive
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => setShowEditModal(true)}
                    className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1.5 text-sm hover:bg-accent"
                  >
                    <Pencil className="h-4 w-4" />
                    Edit profile
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowMergeModal(true)}
                    className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1.5 text-sm hover:bg-accent"
                  >
                    <ArrowRightLeft className="h-4 w-4" />
                    Merge
                  </button>
                </div>
              </div>

              <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_320px]">
                <div className="space-y-5">
                  <div className="rounded-xl border border-border bg-background p-4">
                    <div className="mb-4 flex items-center justify-between gap-3">
                      <div className="text-sm font-semibold">Canonical profile</div>
                      <button
                        type="button"
                        onClick={() => setShowEditModal(true)}
                        className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-1.5 text-xs font-medium hover:bg-accent"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                        Edit
                      </button>
                    </div>
                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="rounded-xl border border-border/70 bg-card/55 p-3">
                        <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Name</div>
                        <div className="mt-2 text-sm font-medium">{selectedEntity.name}</div>
                      </div>
                      <div className="rounded-xl border border-border/70 bg-card/55 p-3">
                        <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Type</div>
                        <div className="mt-2 text-sm font-medium capitalize">{selectedEntity.entityType}</div>
                      </div>
                      <div className="rounded-xl border border-border/70 bg-card/55 p-3 md:col-span-2">
                        <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Description</div>
                        <div className="mt-2 text-sm text-muted-foreground">{selectedEntity.description || 'No canonical description yet.'}</div>
                      </div>
                      <div className="rounded-xl border border-border/70 bg-card/55 p-3 md:col-span-2">
                        <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Aliases</div>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {selectedEntity.aliases.length ? selectedEntity.aliases.map(alias => (
                            <span key={alias} className="rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground">{alias}</span>
                          )) : <span className="text-sm text-muted-foreground">No aliases yet.</span>}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-xl border border-border bg-background p-4">
                    <div className="mb-4 flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2 text-sm font-semibold">
                        <ArrowRightLeft className="h-4 w-4" />
                        Merge duplicate into another entity
                      </div>
                      <button
                        type="button"
                        onClick={() => setShowMergeModal(true)}
                        className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-1.5 text-xs font-medium hover:bg-accent"
                      >
                        <ArrowRightLeft className="h-3.5 w-3.5" />
                        Open merge
                      </button>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Merge moves source links, page links, and entity references into the target, then marks this record as merged.
                    </p>
                    <div className="mt-3 text-sm text-muted-foreground">
                      {mergeCandidates.length ? `${mergeCandidates.length} possible merge targets available.` : 'No merge targets available for this entity.'}
                    </div>
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

              {showEditModal ? (
                <ModalShell title={`Edit ${selectedEntity.name}`} icon={<Pencil className="h-5 w-5" />} onClose={() => setShowEditModal(false)}>
                  <div className="grid gap-4 xl:grid-cols-2">
                    <Field label="Name">
                      <Input value={draftName} onChange={e => setDraftName(e.target.value)} />
                    </Field>
                    <Field label="Type">
                      <select value={draftType} onChange={e => setDraftType(e.target.value)} className="h-11 w-full rounded-2xl border border-input bg-background px-4 text-sm">
                        {ENTITY_TYPES.filter(option => option !== 'all').map(option => <option key={option} value={option}>{option}</option>)}
                      </select>
                    </Field>
                    <Field label="Description" className="xl:col-span-2">
                      <textarea value={draftDescription} onChange={e => setDraftDescription(e.target.value)} rows={6} className="w-full rounded-2xl border border-input bg-background px-4 py-3 text-sm" />
                    </Field>
                    <Field label="Aliases" className="xl:col-span-2">
                      <Input value={draftAliases} onChange={e => setDraftAliases(e.target.value)} placeholder="Comma-separated aliases" />
                    </Field>
                  </div>
                  <div className="mt-6 flex justify-end gap-3">
                    <button type="button" onClick={() => setShowEditModal(false)} className="inline-flex h-10 items-center justify-center rounded-full border border-border bg-background px-4 text-sm font-medium">Cancel</button>
                    <button
                      type="button"
                      onClick={() => saveChanges().then(() => setShowEditModal(false))}
                      disabled={updateEntity.isPending}
                      className="inline-flex h-10 items-center justify-center gap-2 rounded-full bg-primary px-5 text-sm font-semibold text-primary-foreground disabled:opacity-60"
                    >
                      <Save className="h-4 w-4" />
                      {updateEntity.isPending ? 'Saving...' : 'Save canonical profile'}
                    </button>
                  </div>
                </ModalShell>
              ) : null}

              {showMergeModal ? (
                <ModalShell title={`Merge ${selectedEntity.name}`} icon={<ArrowRightLeft className="h-5 w-5" />} onClose={() => setShowMergeModal(false)}>
                  <div className="space-y-4">
                    <Field label="Merge target">
                      <select value={mergeTargetId} onChange={e => setMergeTargetId(e.target.value)} className="h-11 w-full rounded-2xl border border-input bg-background px-4 text-sm">
                        <option value="">Select merge target</option>
                        {mergeCandidates.map(candidate => (
                          <option key={candidate.id} value={candidate.id}>
                            {candidate.name} · {candidate.entityType} · {candidate.verificationStatus}
                          </option>
                        ))}
                      </select>
                    </Field>
                    <div className="rounded-2xl border border-border/70 bg-background/60 p-4 text-sm text-muted-foreground">
                      Merge moves source links, page links, and entity references into the target entity, then marks this entity as merged.
                    </div>
                  </div>
                  <div className="mt-6 flex justify-end gap-3">
                    <button type="button" onClick={() => setShowMergeModal(false)} className="inline-flex h-10 items-center justify-center rounded-full border border-border bg-background px-4 text-sm font-medium">Cancel</button>
                    <button
                      type="button"
                      onClick={() => mergeEntity.mutate({ entityId: selectedEntity.id, targetEntityId: mergeTargetId }, { onSuccess: () => setShowMergeModal(false) })}
                      disabled={!mergeTargetId || mergeEntity.isPending}
                      className="inline-flex h-10 items-center justify-center rounded-full bg-primary px-5 text-sm font-semibold text-primary-foreground disabled:opacity-60"
                    >
                      {mergeEntity.isPending ? 'Merging...' : 'Merge now'}
                    </button>
                  </div>
                </ModalShell>
              ) : null}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-border bg-background p-10 text-center text-sm text-muted-foreground">
              Pick an entity to review and manage it.
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

function ModalShell({ title, icon, children, onClose }: { title: string; icon: React.ReactNode; children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/35 px-4 py-8 backdrop-blur-sm">
      <div className="surface-panel max-h-[calc(100vh-4rem)] w-full max-w-3xl overflow-y-auto rounded-[2rem] border border-border/80 p-6 shadow-[0_30px_90px_rgba(25,20,15,0.22)]">
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
