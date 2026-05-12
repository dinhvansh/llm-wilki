'use client'

import { Building2, Pencil, Plus, X } from 'lucide-react'
import { useMemo, useState } from 'react'

import { EmptyState } from '@/components/data-display/empty-state'
import { ErrorState } from '@/components/data-display/error-state'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { PageHeader } from '@/components/layout/page-header'
import { useAdminDepartments, useAdminUserActions } from '@/hooks/use-admin-users'
import type { Department } from '@/lib/types'
import { useAuth } from '@/providers/auth-provider'

function emptyDepartmentForm() {
  return { name: '', description: '' }
}

export default function AdminDepartmentsPage() {
  const { hasRole } = useAuth()
  const { data: departments, isLoading, isError, error, refetch } = useAdminDepartments()
  const { createDepartment, updateDepartment } = useAdminUserActions()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingDepartment, setEditingDepartment] = useState<Department | null>(null)
  const [createForm, setCreateForm] = useState(emptyDepartmentForm)
  const [editForm, setEditForm] = useState(emptyDepartmentForm)

  const sortedDepartments = useMemo(() => (departments ?? []).slice().sort((a, b) => a.name.localeCompare(b.name)), [departments])

  if (!hasRole('admin')) return <ErrorState message="Only admins can manage departments." />
  if (isLoading) return <LoadingSpinner label="Loading departments..." />
  if (isError) return <ErrorState message={(error as Error)?.message ?? 'Failed to load departments'} onRetry={() => refetch()} />

  return (
    <div className="pb-8">
      <PageHeader
        title="Departments"
        description="Manage organization departments separately from employee creation so access structure stays clean."
        actions={
          <button
            type="button"
            onClick={() => setShowCreateModal(true)}
            className="inline-flex h-10 items-center gap-2 rounded-full bg-primary px-4 text-sm font-semibold text-primary-foreground"
          >
            <Plus className="h-4 w-4" />
            New department
          </button>
        }
      />

      <div className="p-6">
        <div className="surface-panel rounded-[2rem] border border-border/80 p-5">
          {!sortedDepartments.length ? (
            <EmptyState icon="inbox" title="No departments yet" description="Create your first department to structure ownership and permissions." />
          ) : (
            <div className="rounded-[1.5rem] border border-border/70 bg-background/45">
              <div className="grid grid-cols-[minmax(0,220px),minmax(0,1fr),120px] gap-4 border-b border-border/70 px-5 py-3 text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
                <div>Name</div>
                <div>Description</div>
                <div className="text-right">Action</div>
              </div>
              <div className="divide-y divide-border/60">
                {sortedDepartments.map(department => (
                  <div key={department.id} className="grid grid-cols-[minmax(0,220px),minmax(0,1fr),120px] gap-4 px-5 py-4">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold text-foreground">{department.name}</div>
                      <div className="mt-1 text-xs uppercase tracking-[0.16em] text-muted-foreground">{department.slug}</div>
                    </div>
                    <div className="self-center text-sm text-muted-foreground">{department.description || 'No description'}</div>
                    <div className="flex justify-end">
                      <button
                        type="button"
                        onClick={() => {
                          setEditingDepartment(department)
                          setEditForm({ name: department.name, description: department.description })
                        }}
                        className="inline-flex h-9 items-center gap-2 rounded-full border border-border bg-background px-4 text-sm font-medium transition-colors hover:border-primary/30 hover:text-foreground"
                      >
                        <Pencil className="h-4 w-4" />
                        Edit
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {showCreateModal && (
        <ModalShell title="Create department" icon={<Building2 className="h-5 w-5" />} onClose={() => setShowCreateModal(false)}>
          <div className="space-y-4">
            <Field label="Department name">
              <input value={createForm.name} onChange={event => setCreateForm(current => ({ ...current, name: event.target.value }))} className="h-11 w-full rounded-2xl border border-input bg-background px-4 text-sm" />
            </Field>
            <Field label="Description">
              <textarea value={createForm.description} onChange={event => setCreateForm(current => ({ ...current, description: event.target.value }))} rows={4} className="w-full rounded-2xl border border-input bg-background px-4 py-3 text-sm" />
            </Field>
          </div>
          <div className="mt-6 flex justify-end gap-3">
            <button type="button" onClick={() => setShowCreateModal(false)} className="inline-flex h-10 items-center justify-center rounded-full border border-border bg-background px-4 text-sm font-medium">Cancel</button>
            <button
              type="button"
              disabled={createDepartment.isPending || !createForm.name.trim()}
              onClick={() =>
                createDepartment.mutate(
                  { name: createForm.name.trim(), description: createForm.description.trim() },
                  { onSuccess: () => { setCreateForm(emptyDepartmentForm()); setShowCreateModal(false) } },
                )
              }
              className="inline-flex h-10 items-center justify-center rounded-full bg-primary px-5 text-sm font-semibold text-primary-foreground disabled:opacity-60"
            >
              {createDepartment.isPending ? 'Creating...' : 'Create department'}
            </button>
          </div>
        </ModalShell>
      )}

      {editingDepartment && (
        <ModalShell title="Edit department" icon={<Pencil className="h-5 w-5" />} onClose={() => setEditingDepartment(null)}>
          <div className="space-y-4">
            <Field label="Department name">
              <input value={editForm.name} onChange={event => setEditForm(current => ({ ...current, name: event.target.value }))} className="h-11 w-full rounded-2xl border border-input bg-background px-4 text-sm" />
            </Field>
            <Field label="Description">
              <textarea value={editForm.description} onChange={event => setEditForm(current => ({ ...current, description: event.target.value }))} rows={4} className="w-full rounded-2xl border border-input bg-background px-4 py-3 text-sm" />
            </Field>
          </div>
          <div className="mt-6 flex justify-end gap-3">
            <button type="button" onClick={() => setEditingDepartment(null)} className="inline-flex h-10 items-center justify-center rounded-full border border-border bg-background px-4 text-sm font-medium">Cancel</button>
            <button
              type="button"
              disabled={updateDepartment.isPending || !editForm.name.trim()}
              onClick={() =>
                updateDepartment.mutate(
                  { departmentId: editingDepartment.id, payload: { name: editForm.name.trim(), description: editForm.description.trim() } },
                  { onSuccess: () => setEditingDepartment(null) },
                )
              }
              className="inline-flex h-10 items-center justify-center rounded-full bg-primary px-5 text-sm font-semibold text-primary-foreground disabled:opacity-60"
            >
              {updateDepartment.isPending ? 'Saving...' : 'Save changes'}
            </button>
          </div>
        </ModalShell>
      )}
    </div>
  )
}

function ModalShell({ title, icon, children, onClose }: { title: string; icon: React.ReactNode; children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/35 px-4 py-10 backdrop-blur-sm">
      <div className="surface-panel w-full max-w-2xl rounded-[2rem] border border-border/80 p-6 shadow-[0_30px_90px_rgba(25,20,15,0.22)]">
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

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-2">
      <span className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">{label}</span>
      {children}
    </label>
  )
}
