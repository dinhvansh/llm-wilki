'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { Archive, ArrowRightLeft, BadgeCheck, Boxes, FileText, RefreshCw, Save, Search, ShieldAlert, ShieldCheck } from 'lucide-react'

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
      <div className="grid gap-6 p-6 xl:grid-cols-[360px_minmax(0,1fr)]">
        <section className="space-y-4 rounded-2xl border border-border bg-card p-4">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search entities..." className="pl-8 h-10" />
          </div>
          <div className="grid gap-2 sm:grid-cols-3 xl:grid-cols-1">
            <select value={entityType} onChange={e => setEntityType(e.target.value as (typeof ENTITY_TYPES)[number])} className="h-10 rounded-md border border-input bg-background px-3 text-sm">
              {ENTITY_TYPES.map(option => <option key={option} value={option}>{option === 'all' ? 'All types' : option}</option>)}
            </select>
            <select value={verificationFilter} onChange={e => setVerificationFilter(e.target.value as (typeof VERIFICATION_FILTERS)[number])} className="h-10 rounded-md border border-input bg-background px-3 text-sm">
              {VERIFICATION_FILTERS.map(option => <option key={option} value={option}>{option === 'all' ? 'All verification' : option}</option>)}
            </select>
            <select value={statusFilter} onChange={e => setStatusFilter(e.target.value as (typeof STATUS_FILTERS)[number])} className="h-10 rounded-md border border-input bg-background px-3 text-sm">
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
                </div>
              </div>

              <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
                <div className="space-y-5">
                  <div className="rounded-xl border border-border bg-background p-4">
                    <div className="mb-4 text-sm font-semibold">Canonical profile</div>
                    <div className="grid gap-4 md:grid-cols-2">
                      <label className="block">
                        <div className="mb-1 text-sm font-medium">Name</div>
                        <Input value={draftName} onChange={e => setDraftName(e.target.value)} />
                      </label>
                      <label className="block">
                        <div className="mb-1 text-sm font-medium">Type</div>
                        <select value={draftType} onChange={e => setDraftType(e.target.value)} className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm">
                          {ENTITY_TYPES.filter(option => option !== 'all').map(option => <option key={option} value={option}>{option}</option>)}
                        </select>
                      </label>
                      <label className="block md:col-span-2">
                        <div className="mb-1 text-sm font-medium">Description</div>
                        <textarea value={draftDescription} onChange={e => setDraftDescription(e.target.value)} className="min-h-28 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" />
                      </label>
                      <label className="block md:col-span-2">
                        <div className="mb-1 text-sm font-medium">Aliases</div>
                        <Input value={draftAliases} onChange={e => setDraftAliases(e.target.value)} placeholder="Comma-separated aliases" />
                      </label>
                    </div>
                    <div className="mt-4 flex justify-end">
                      <button
                        type="button"
                        onClick={saveChanges}
                        disabled={updateEntity.isPending}
                        className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                      >
                        <Save className="h-4 w-4" />
                        {updateEntity.isPending ? 'Saving...' : 'Save canonical profile'}
                      </button>
                    </div>
                  </div>

                  <div className="rounded-xl border border-border bg-background p-4">
                    <div className="mb-4 flex items-center gap-2 text-sm font-semibold">
                      <ArrowRightLeft className="h-4 w-4" />
                      Merge duplicate into another entity
                    </div>
                    <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]">
                      <select value={mergeTargetId} onChange={e => setMergeTargetId(e.target.value)} className="h-10 rounded-md border border-input bg-background px-3 text-sm">
                        <option value="">Select merge target</option>
                        {mergeCandidates.map(candidate => (
                          <option key={candidate.id} value={candidate.id}>
                            {candidate.name} · {candidate.entityType} · {candidate.verificationStatus}
                          </option>
                        ))}
                      </select>
                      <button
                        type="button"
                        onClick={() => mergeEntity.mutate({ entityId: selectedEntity.id, targetEntityId: mergeTargetId })}
                        disabled={!mergeTargetId || mergeEntity.isPending}
                        className="rounded-md border border-border px-3 py-2 text-sm hover:bg-accent disabled:opacity-50"
                      >
                        {mergeEntity.isPending ? 'Merging...' : 'Merge now'}
                      </button>
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground">
                      Merge moves source/page links and entity references into the target, then marks this record as merged.
                    </p>
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
