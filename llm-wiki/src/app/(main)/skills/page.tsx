'use client'

import { useState } from 'react'

import { EmptyState } from '@/components/data-display/empty-state'
import { ErrorState } from '@/components/data-display/error-state'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { PageHeader } from '@/components/layout/page-header'
import { useSkillActions, useSkills } from '@/hooks/use-skills'
import { useAuth } from '@/providers/auth-provider'

export default function SkillsPage() {
  const { data, isLoading, isError, error, refetch } = useSkills()
  const { addComment, submitReview, approve, release } = useSkillActions()
  const { hasPermission } = useAuth()
  const [commentDrafts, setCommentDrafts] = useState<Record<string, string>>({})
  const canWrite = hasPermission('skill:write')

  if (isLoading) return <LoadingSpinner label="Loading skill registry..." />
  if (isError) return <ErrorState message={(error as Error)?.message ?? 'Failed to load skill registry'} onRetry={() => refetch()} />

  return (
    <div>
      <PageHeader
        title="Skill Packages"
        description="Internal registry for reusable workflow, prompt, and tool packages."
      />

      <div className="p-6">
        {!data || data.length === 0 ? (
          <EmptyState icon="database" title="No skill packages yet" description="Reusable internal AI capability packages will appear here." />
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {data.map(skill => {
              const draft = commentDrafts[skill.id] ?? ''
              const busy = addComment.isPending || submitReview.isPending || approve.isPending || release.isPending
              return (
                <div key={skill.id} className="rounded-lg border border-border bg-card p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-sm font-semibold">{skill.name}</div>
                      <div className="text-xs text-muted-foreground">{skill.id}</div>
                    </div>
                    <div className="text-right text-xs text-muted-foreground">
                      <div>v{skill.version}</div>
                      <div>{skill.reviewStatus}</div>
                    </div>
                  </div>
                  <p className="mt-3 text-sm text-muted-foreground">{skill.summary}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <span className="rounded-full bg-muted px-2 py-1 text-xs">{skill.scope}</span>
                    <span className="rounded-full bg-muted px-2 py-1 text-xs">{skill.status}</span>
                    <span className="rounded-full bg-muted px-2 py-1 text-xs">{String(skill.metadataJson?.packageType ?? 'package')}</span>
                    {(skill.tags ?? []).map(tag => <span key={tag} className="rounded-full bg-muted px-2 py-1 text-xs">{tag}</span>)}
                  </div>
                  {skill.capabilities.length > 0 && (
                    <div className="mt-4">
                      <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Capabilities</div>
                      <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                        {skill.capabilities.map(capability => <li key={capability}>- {capability}</li>)}
                      </ul>
                    </div>
                  )}
                  {skill.entryPoints.length > 0 && (
                    <div className="mt-4">
                      <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Entry Points</div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {skill.entryPoints.map(entryPoint => <span key={entryPoint} className="rounded-full border border-border px-2 py-1 text-xs">{entryPoint}</span>)}
                      </div>
                    </div>
                  )}

                  <div className="mt-4 rounded-lg border border-border/70 bg-muted/20 p-3">
                    <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Review Flow</div>
                    <div className="mt-2 text-sm text-muted-foreground">
                      Workflow pack for review-oriented capability distribution. Scope and release state are tracked per package.
                    </div>
                    <div className="mt-3 space-y-2">
                      {(skill.reviewHistory ?? []).length === 0 ? (
                        <div className="text-xs text-muted-foreground">No review activity yet.</div>
                      ) : (
                        (skill.reviewHistory ?? []).slice().reverse().map(event => (
                          <div key={event.id} className="rounded-md border border-border/60 bg-background/60 p-2 text-xs">
                            <div className="flex items-center justify-between gap-3">
                              <span className="font-medium">{event.type}</span>
                              <span className="text-muted-foreground">{new Date(event.createdAt).toLocaleString()}</span>
                            </div>
                            <div className="mt-1 text-muted-foreground">{event.actor}</div>
                            {event.comment && <div className="mt-1 whitespace-pre-wrap text-foreground/90">{event.comment}</div>}
                          </div>
                        ))
                      )}
                    </div>
                    {canWrite && (
                      <div className="mt-3 space-y-3">
                        <textarea
                          value={draft}
                          onChange={event => setCommentDrafts(current => ({ ...current, [skill.id]: event.target.value }))}
                          placeholder="Add reviewer note, release note, or scope decision..."
                          className="min-h-[88px] w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none"
                        />
                        <div className="flex flex-wrap gap-2">
                          <button
                            type="button"
                            onClick={() => addComment.mutate({ id: skill.id, comment: draft }, { onSuccess: () => setCommentDrafts(current => ({ ...current, [skill.id]: '' })) })}
                            disabled={!draft.trim() || busy}
                            className="rounded-md border border-border px-3 py-2 text-xs font-medium disabled:opacity-50"
                          >
                            Add Comment
                          </button>
                          <button
                            type="button"
                            onClick={() => submitReview.mutate({ id: skill.id, comment: draft || undefined }, { onSuccess: () => setCommentDrafts(current => ({ ...current, [skill.id]: '' })) })}
                            disabled={busy}
                            className="rounded-md border border-border px-3 py-2 text-xs font-medium disabled:opacity-50"
                          >
                            Submit Review
                          </button>
                          <button
                            type="button"
                            onClick={() => approve.mutate({ id: skill.id, comment: draft || undefined }, { onSuccess: () => setCommentDrafts(current => ({ ...current, [skill.id]: '' })) })}
                            disabled={busy}
                            className="rounded-md border border-border px-3 py-2 text-xs font-medium disabled:opacity-50"
                          >
                            Approve
                          </button>
                          <button
                            type="button"
                            onClick={() => release.mutate({ id: skill.id, comment: draft || undefined }, { onSuccess: () => setCommentDrafts(current => ({ ...current, [skill.id]: '' })) })}
                            disabled={busy}
                            className="rounded-md bg-primary px-3 py-2 text-xs font-medium text-primary-foreground disabled:opacity-50"
                          >
                            Release
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
