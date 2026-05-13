'use client'

import { FlaskConical, Pencil, Plus, X } from 'lucide-react'
import { useMemo, useState } from 'react'

import { EmptyState } from '@/components/data-display/empty-state'
import { ErrorState } from '@/components/data-display/error-state'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { PageHeader } from '@/components/layout/page-header'
import { Input } from '@/components/ui/input'
import { useSkillActions, useSkills } from '@/hooks/use-skills'
import type { SkillPackage } from '@/lib/types'
import { useAuth } from '@/providers/auth-provider'

const TASK_PROFILE_OPTIONS = [
  'ask_answer',
  'review_assist',
  'ingest_summary',
  'claim_extraction',
  'entity_glossary_timeline',
  'bpm_generation',
]

type SkillFormState = {
  id: string
  name: string
  version: string
  scope: string
  status: string
  reviewStatus: string
  owner: string
  summary: string
  description: string
  instructions: string
  capabilities: string
  tags: string
  entryPoints: string
  taskProfile: string
  changeComment: string
}

function emptySkillForm(): SkillFormState {
  return {
    id: '',
    name: '',
    version: '0.1.0',
    scope: 'workspace',
    status: 'draft',
    reviewStatus: 'draft',
    owner: '',
    summary: '',
    description: '',
    instructions: '',
    capabilities: '',
    tags: '',
    entryPoints: '',
    taskProfile: 'ask_answer',
    changeComment: '',
  }
}

function skillToForm(skill: SkillPackage): SkillFormState {
  return {
    id: skill.id,
    name: skill.name,
    version: skill.version,
    scope: skill.scope,
    status: skill.status,
    reviewStatus: skill.reviewStatus,
    owner: skill.owner ?? '',
    summary: skill.summary,
    description: skill.description,
    instructions: skill.instructions ?? '',
    capabilities: (skill.capabilities ?? []).join(', '),
    tags: (skill.tags ?? []).join(', '),
    entryPoints: (skill.entryPoints ?? []).join(', '),
    taskProfile: skill.taskProfile ?? String(skill.metadataJson?.taskProfile ?? 'ask_answer'),
    changeComment: '',
  }
}

function splitCsv(value: string): string[] {
  return value.split(',').map(item => item.trim()).filter(Boolean)
}

export default function SkillsPage() {
  const { data, isLoading, isError, error, refetch } = useSkills()
  const { createSkill, updateSkill, testSkill, addComment, submitReview, approve, release } = useSkillActions()
  const { hasPermission } = useAuth()
  const [commentDrafts, setCommentDrafts] = useState<Record<string, string>>({})
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingSkill, setEditingSkill] = useState<SkillPackage | null>(null)
  const [testingSkill, setTestingSkill] = useState<SkillPackage | null>(null)
  const [createForm, setCreateForm] = useState<SkillFormState>(emptySkillForm)
  const [editForm, setEditForm] = useState<SkillFormState>(emptySkillForm)
  const [testInput, setTestInput] = useState('')
  const canWrite = hasPermission('skill:write')

  const sortedSkills = useMemo(() => (data ?? []).slice().sort((a, b) => a.name.localeCompare(b.name)), [data])

  if (isLoading) return <LoadingSpinner label="Loading skill registry..." />
  if (isError) return <ErrorState message={(error as Error)?.message ?? 'Failed to load skill registry'} onRetry={() => refetch()} />

  const busy = createSkill.isPending || updateSkill.isPending || testSkill.isPending || addComment.isPending || submitReview.isPending || approve.isPending || release.isPending

  return (
    <div>
      <PageHeader
        title="Skill Packages"
        description="Create reusable AI skills, tune their instructions, and run live tests before review and release."
        actions={
          canWrite ? (
            <button
              type="button"
              onClick={() => { setCreateForm(emptySkillForm()); setShowCreateModal(true) }}
              className="inline-flex h-10 items-center gap-2 rounded-full bg-primary px-4 text-sm font-semibold text-primary-foreground"
            >
              <Plus className="h-4 w-4" />
              New skill
            </button>
          ) : undefined
        }
      />

      <div className="p-6">
        {!sortedSkills.length ? (
          <EmptyState icon="database" title="No skill packages yet" description="Create your first skill so reusable AI workflows can be authored and tested here." />
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">
            {sortedSkills.map(skill => {
              const draft = commentDrafts[skill.id] ?? ''
              return (
                <div key={skill.id} className="rounded-2xl border border-border bg-card p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="text-base font-semibold">{skill.name}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{skill.id}</div>
                    </div>
                    <div className="text-right text-xs text-muted-foreground">
                      <div>v{skill.version}</div>
                      <div>{skill.reviewStatus}</div>
                    </div>
                  </div>

                  <p className="mt-3 text-sm text-muted-foreground">{skill.summary || 'No summary yet.'}</p>

                  <div className="mt-3 flex flex-wrap gap-2">
                    <span className="rounded-full bg-muted px-2 py-1 text-xs">{skill.scope}</span>
                    <span className="rounded-full bg-muted px-2 py-1 text-xs">{skill.status}</span>
                    <span className="rounded-full bg-muted px-2 py-1 text-xs">{skill.taskProfile ?? 'ask_answer'}</span>
                    {(skill.tags ?? []).map(tag => <span key={tag} className="rounded-full bg-muted px-2 py-1 text-xs">{tag}</span>)}
                  </div>

                  <div className="mt-4 grid gap-3 rounded-xl border border-border/70 bg-background/55 p-4">
                    <div>
                      <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Instructions</div>
                      <div className="mt-2 line-clamp-4 whitespace-pre-wrap text-sm text-muted-foreground">
                        {skill.instructions || 'No explicit instructions yet. The system falls back to summary, description, and capabilities.'}
                      </div>
                    </div>
                    {skill.capabilities.length > 0 ? (
                      <div>
                        <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Capabilities</div>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {skill.capabilities.map(capability => <span key={capability} className="rounded-full border border-border px-2 py-1 text-xs">{capability}</span>)}
                        </div>
                      </div>
                    ) : null}
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    {canWrite ? (
                      <>
                        <button
                          type="button"
                          onClick={() => { setEditForm(skillToForm(skill)); setEditingSkill(skill) }}
                          className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-2 text-xs font-medium"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => { setTestingSkill(skill); setTestInput(skill.latestTest?.input ?? '') }}
                          className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-2 text-xs font-medium"
                        >
                          <FlaskConical className="h-3.5 w-3.5" />
                          Test skill
                        </button>
                      </>
                    ) : null}
                  </div>

                  {skill.latestTest ? (
                    <div className="mt-4 rounded-xl border border-border/70 bg-muted/15 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Latest test</div>
                        <div className="text-xs text-muted-foreground">
                          {skill.latestTest.provider} / {skill.latestTest.model}
                        </div>
                      </div>
                      <div className="mt-2 text-xs text-muted-foreground">{new Date(skill.latestTest.createdAt).toLocaleString()}</div>
                      <div className="mt-3 text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Input</div>
                      <div className="mt-1 whitespace-pre-wrap text-sm text-muted-foreground">{skill.latestTest.input}</div>
                      <div className="mt-3 text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Output</div>
                      <div className="mt-1 whitespace-pre-wrap text-sm">{skill.latestTest.output || 'No output returned.'}</div>
                    </div>
                  ) : null}

                  <div className="mt-4 rounded-xl border border-border/70 bg-muted/20 p-4">
                    <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Review flow</div>
                    <div className="mt-2 space-y-2">
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
                            {event.comment ? <div className="mt-1 whitespace-pre-wrap text-foreground/90">{event.comment}</div> : null}
                          </div>
                        ))
                      )}
                    </div>

                    {canWrite ? (
                      <div className="mt-3 space-y-3">
                        <textarea
                          value={draft}
                          onChange={event => setCommentDrafts(current => ({ ...current, [skill.id]: event.target.value }))}
                          placeholder="Add reviewer note, release note, or scope decision..."
                          className="min-h-[88px] w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none"
                        />
                        <div className="flex flex-wrap gap-2">
                          <button type="button" onClick={() => addComment.mutate({ id: skill.id, comment: draft }, { onSuccess: () => setCommentDrafts(current => ({ ...current, [skill.id]: '' })) })} disabled={!draft.trim() || busy} className="rounded-md border border-border px-3 py-2 text-xs font-medium disabled:opacity-50">Add Comment</button>
                          <button type="button" onClick={() => submitReview.mutate({ id: skill.id, comment: draft || undefined }, { onSuccess: () => setCommentDrafts(current => ({ ...current, [skill.id]: '' })) })} disabled={busy} className="rounded-md border border-border px-3 py-2 text-xs font-medium disabled:opacity-50">Submit Review</button>
                          <button type="button" onClick={() => approve.mutate({ id: skill.id, comment: draft || undefined }, { onSuccess: () => setCommentDrafts(current => ({ ...current, [skill.id]: '' })) })} disabled={busy} className="rounded-md border border-border px-3 py-2 text-xs font-medium disabled:opacity-50">Approve</button>
                          <button type="button" onClick={() => release.mutate({ id: skill.id, comment: draft || undefined }, { onSuccess: () => setCommentDrafts(current => ({ ...current, [skill.id]: '' })) })} disabled={busy} className="rounded-md bg-primary px-3 py-2 text-xs font-medium text-primary-foreground disabled:opacity-50">Release</button>
                        </div>
                      </div>
                    ) : null}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {showCreateModal ? (
        <ModalShell title="Create skill package" icon={<Plus className="h-5 w-5" />} onClose={() => setShowCreateModal(false)}>
          <SkillForm
            form={createForm}
            onChange={setCreateForm}
            submitLabel={createSkill.isPending ? 'Creating...' : 'Create skill'}
            onCancel={() => setShowCreateModal(false)}
            onSubmit={() =>
              createSkill.mutate(
                {
                  id: createForm.id || undefined,
                  name: createForm.name,
                  version: createForm.version,
                  scope: createForm.scope,
                  status: createForm.status,
                  reviewStatus: createForm.reviewStatus,
                  owner: createForm.owner || null,
                  summary: createForm.summary,
                  description: createForm.description,
                  instructions: createForm.instructions,
                  capabilities: splitCsv(createForm.capabilities),
                  tags: splitCsv(createForm.tags),
                  entryPoints: splitCsv(createForm.entryPoints),
                  taskProfile: createForm.taskProfile,
                  changeComment: createForm.changeComment || 'Created skill package',
                },
                {
                  onSuccess: skill => {
                    setShowCreateModal(false)
                    setTestingSkill(skill)
                    setTestInput('')
                  },
                },
              )
            }
            isPending={createSkill.isPending}
          />
        </ModalShell>
      ) : null}

      {editingSkill ? (
        <ModalShell title={`Edit ${editingSkill.name}`} icon={<Pencil className="h-5 w-5" />} onClose={() => setEditingSkill(null)}>
          <SkillForm
            form={editForm}
            onChange={setEditForm}
            submitLabel={updateSkill.isPending ? 'Saving...' : 'Save changes'}
            onCancel={() => setEditingSkill(null)}
            onSubmit={() =>
              updateSkill.mutate(
                {
                  id: editingSkill.id,
                  payload: {
                    name: editForm.name,
                    version: editForm.version,
                    scope: editForm.scope,
                    status: editForm.status,
                    reviewStatus: editForm.reviewStatus,
                    owner: editForm.owner || null,
                    summary: editForm.summary,
                    description: editForm.description,
                    instructions: editForm.instructions,
                    capabilities: splitCsv(editForm.capabilities),
                    tags: splitCsv(editForm.tags),
                    entryPoints: splitCsv(editForm.entryPoints),
                    taskProfile: editForm.taskProfile,
                    changeComment: editForm.changeComment || 'Updated skill package',
                  },
                },
                { onSuccess: () => setEditingSkill(null) },
              )
            }
            isPending={updateSkill.isPending}
          />
        </ModalShell>
      ) : null}

      {testingSkill ? (
        <ModalShell title={`Test ${testingSkill.name}`} icon={<FlaskConical className="h-5 w-5" />} onClose={() => setTestingSkill(null)}>
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <Stat label="Task profile" value={testingSkill.taskProfile ?? 'ask_answer'} />
              <Stat label="Status" value={testingSkill.status} />
              <Stat label="Review" value={testingSkill.reviewStatus} />
            </div>
            <label className="block space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Test input</span>
              <textarea
                value={testInput}
                onChange={event => setTestInput(event.target.value)}
                placeholder="Paste a realistic task request here. The skill will run against the configured runtime model profile."
                rows={8}
                className="w-full rounded-2xl border border-input bg-background px-4 py-3 text-sm"
              />
            </label>
            <div className="flex justify-end gap-3">
              <button type="button" onClick={() => setTestingSkill(null)} className="inline-flex h-10 items-center justify-center rounded-full border border-border bg-background px-4 text-sm font-medium">Close</button>
              <button
                type="button"
                onClick={() => testSkill.mutate({ id: testingSkill.id, input: testInput })}
                disabled={!testInput.trim() || testSkill.isPending}
                className="inline-flex h-10 items-center justify-center rounded-full bg-primary px-5 text-sm font-semibold text-primary-foreground disabled:opacity-60"
              >
                {testSkill.isPending ? 'Running...' : 'Run test'}
              </button>
            </div>
            {testingSkill.latestTest ? (
              <div className="rounded-2xl border border-border/70 bg-background/60 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-sm font-semibold">Latest result</div>
                  <div className="text-xs text-muted-foreground">{testingSkill.latestTest.provider} / {testingSkill.latestTest.model}</div>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">{new Date(testingSkill.latestTest.createdAt).toLocaleString()}</div>
                <div className="mt-3 text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Output</div>
                <div className="mt-2 whitespace-pre-wrap text-sm">{testingSkill.latestTest.output || 'No output returned.'}</div>
              </div>
            ) : null}
          </div>
        </ModalShell>
      ) : null}
    </div>
  )
}

function SkillForm({
  form,
  onChange,
  onSubmit,
  onCancel,
  submitLabel,
  isPending,
}: {
  form: SkillFormState
  onChange: (next: SkillFormState) => void
  onSubmit: () => void
  onCancel: () => void
  submitLabel: string
  isPending: boolean
}) {
  const update = (patch: Partial<SkillFormState>) => onChange({ ...form, ...patch })

  return (
    <>
      <div className="grid gap-4 xl:grid-cols-2">
        <Field label="Name">
          <Input value={form.name} onChange={event => update({ name: event.target.value })} />
        </Field>
        <Field label="Id slug">
          <Input value={form.id} onChange={event => update({ id: event.target.value })} placeholder="Optional. Auto-generated if empty." />
        </Field>
        <Field label="Summary" className="xl:col-span-2">
          <Input value={form.summary} onChange={event => update({ summary: event.target.value })} />
        </Field>
        <Field label="Description" className="xl:col-span-2">
          <textarea value={form.description} onChange={event => update({ description: event.target.value })} rows={4} className="w-full rounded-2xl border border-input bg-background px-4 py-3 text-sm" />
        </Field>
        <Field label="Instructions" className="xl:col-span-2">
          <textarea value={form.instructions} onChange={event => update({ instructions: event.target.value })} rows={8} className="w-full rounded-2xl border border-input bg-background px-4 py-3 text-sm" />
        </Field>
        <Field label="Capabilities">
          <Input value={form.capabilities} onChange={event => update({ capabilities: event.target.value })} placeholder="Comma-separated" />
        </Field>
        <Field label="Tags">
          <Input value={form.tags} onChange={event => update({ tags: event.target.value })} placeholder="Comma-separated" />
        </Field>
        <Field label="Entry points">
          <Input value={form.entryPoints} onChange={event => update({ entryPoints: event.target.value })} placeholder="Comma-separated" />
        </Field>
        <Field label="Task profile">
          <select value={form.taskProfile} onChange={event => update({ taskProfile: event.target.value })} className="h-11 w-full rounded-2xl border border-input bg-background px-4 text-sm">
            {TASK_PROFILE_OPTIONS.map(option => <option key={option} value={option}>{option}</option>)}
          </select>
        </Field>
        <Field label="Owner">
          <Input value={form.owner} onChange={event => update({ owner: event.target.value })} />
        </Field>
        <Field label="Version">
          <Input value={form.version} onChange={event => update({ version: event.target.value })} />
        </Field>
        <Field label="Change note" className="xl:col-span-2">
          <Input value={form.changeComment} onChange={event => update({ changeComment: event.target.value })} placeholder="Why this version exists or changed" />
        </Field>
      </div>
      <div className="mt-6 flex justify-end gap-3">
        <button type="button" onClick={onCancel} className="inline-flex h-10 items-center justify-center rounded-full border border-border bg-background px-4 text-sm font-medium">Cancel</button>
        <button type="button" onClick={onSubmit} disabled={!form.name.trim() || isPending} className="inline-flex h-10 items-center justify-center rounded-full bg-primary px-5 text-sm font-semibold text-primary-foreground disabled:opacity-60">
          {submitLabel}
        </button>
      </div>
    </>
  )
}

function ModalShell({ title, icon, children, onClose }: { title: string; icon: React.ReactNode; children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/35 px-4 py-8 backdrop-blur-sm">
      <div className="surface-panel max-h-[calc(100vh-4rem)] w-full max-w-5xl overflow-y-auto rounded-[2rem] border border-border/80 p-6 shadow-[0_30px_90px_rgba(25,20,15,0.22)]">
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

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-border/70 bg-background/60 p-4">
      <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">{label}</div>
      <div className="mt-2 text-sm font-medium">{value}</div>
    </div>
  )
}
