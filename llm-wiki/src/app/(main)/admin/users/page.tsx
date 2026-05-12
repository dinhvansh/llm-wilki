'use client'

import { Building2, KeyRound, Plus, Search, Shield, Sparkles, UserPlus, Users, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

import { EmptyState } from '@/components/data-display/empty-state'
import { ErrorState } from '@/components/data-display/error-state'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { PageHeader } from '@/components/layout/page-header'
import { useAdminDepartments, useAdminUserActions, useAdminUsers } from '@/hooks/use-admin-users'
import { useCollections, useSetCollectionMemberships } from '@/hooks/use-collections'
import type { ManagedUser } from '@/lib/types'
import { useAuth } from '@/providers/auth-provider'

const GLOBAL_ROLES = [
  { value: 'reader', label: 'Reader', description: 'Browse and ask against allowed knowledge.' },
  { value: 'editor', label: 'Editor', description: 'Edit sources and structured pages.' },
  { value: 'reviewer', label: 'Reviewer', description: 'Approve review and publication flows.' },
  { value: 'admin', label: 'Admin', description: 'Manage people, settings, and access policies.' },
]

const COLLECTION_ROLES = [
  { value: '', label: 'No access' },
  { value: 'viewer', label: 'Viewer' },
  { value: 'contributor', label: 'Contributor' },
  { value: 'editor', label: 'Editor' },
  { value: 'admin', label: 'Admin' },
]

function roleForCollection(user: ManagedUser, collectionId: string) {
  return user.collectionMemberships.find(item => item.collectionId === collectionId)?.role ?? ''
}

function createUserForm() {
  return {
    email: '',
    name: '',
    role: 'reader',
    password: '',
    departmentId: '',
    isActive: true,
  }
}

function createDepartmentForm() {
  return {
    name: '',
    description: '',
  }
}

export default function AdminUsersPage() {
  const { hasRole } = useAuth()
  const { data: users, isLoading, isError, error, refetch } = useAdminUsers()
  const { data: departments } = useAdminDepartments()
  const { data: collections } = useCollections()
  const { createUser, updateUser, setPassword, createDepartment } = useAdminUserActions()
  const setMemberships = useSetCollectionMemberships()

  const [searchValue, setSearchValue] = useState('')
  const [roleFilter, setRoleFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [createForm, setCreateForm] = useState(createUserForm)
  const [departmentForm, setDepartmentForm] = useState(createDepartmentForm)
  const [profileDraft, setProfileDraft] = useState({ name: '', email: '', role: 'reader', departmentId: '', isActive: true })
  const [passwordDraft, setPasswordDraft] = useState('')
  const [membershipDrafts, setMembershipDrafts] = useState<Record<string, Record<string, string>>>({})

  const sortedUsers = useMemo(() => (users ?? []).slice().sort((a, b) => a.email.localeCompare(b.email)), [users])

  const filteredUsers = useMemo(() => {
    return sortedUsers.filter(user => {
      const term = searchValue.trim().toLowerCase()
      const matchesSearch =
        term.length === 0 ||
        user.name.toLowerCase().includes(term) ||
        user.email.toLowerCase().includes(term) ||
        (user.departmentName ?? '').toLowerCase().includes(term)

      const matchesRole = roleFilter === 'all' || user.role === roleFilter
      const matchesStatus =
        statusFilter === 'all' ||
        (statusFilter === 'active' && user.isActive) ||
        (statusFilter === 'inactive' && !user.isActive) ||
        (statusFilter === 'scoped' && user.scopeMode === 'restricted')

      return matchesSearch && matchesRole && matchesStatus
    })
  }, [roleFilter, searchValue, sortedUsers, statusFilter])

  const selectedUser = useMemo(
    () => filteredUsers.find(user => user.id === selectedUserId) ?? filteredUsers[0] ?? null,
    [filteredUsers, selectedUserId],
  )

  useEffect(() => {
    if (!selectedUser) {
      setSelectedUserId(null)
      return
    }
    if (selectedUser.id !== selectedUserId) {
      setSelectedUserId(selectedUser.id)
    }
  }, [selectedUser, selectedUserId])

  useEffect(() => {
    if (!selectedUser) return
    setProfileDraft({
      name: selectedUser.name,
      email: selectedUser.email,
      role: selectedUser.role,
      departmentId: selectedUser.departmentId ?? '',
      isActive: selectedUser.isActive,
    })
    setPasswordDraft('')
  }, [selectedUser])

  if (!hasRole('admin')) {
    return <ErrorState message="Only admins can manage users." />
  }

  if (isLoading) return <LoadingSpinner label="Loading users..." />
  if (isError) return <ErrorState message={(error as Error)?.message ?? 'Failed to load users'} onRetry={() => refetch()} />

  const stats = {
    total: sortedUsers.length,
    active: sortedUsers.filter(user => user.isActive).length,
    scoped: sortedUsers.filter(user => user.scopeMode === 'restricted').length,
    departments: (departments ?? []).length,
  }

  const onCreateUser = () => {
    createUser.mutate(
      {
        ...createForm,
        departmentId: createForm.departmentId || null,
      },
      {
        onSuccess: created => {
          setCreateForm(createUserForm())
          setShowCreateModal(false)
          setSelectedUserId(created.id)
        },
      },
    )
  }

  const onSaveProfile = () => {
    if (!selectedUser) return
    updateUser.mutate({
      userId: selectedUser.id,
      payload: {
        name: profileDraft.name.trim(),
        email: profileDraft.email.trim(),
        role: profileDraft.role,
        departmentId: profileDraft.departmentId || null,
        isActive: profileDraft.isActive,
      },
    })
  }

  const onResetPassword = () => {
    if (!selectedUser || !passwordDraft.trim()) return
    setPassword.mutate(
      {
        userId: selectedUser.id,
        password: passwordDraft.trim(),
      },
      {
        onSuccess: () => setPasswordDraft(''),
      },
    )
  }

  const onSaveMemberships = async (user: ManagedUser) => {
    if (!collections || collections.length === 0 || !users) return
    const draft = membershipDrafts[user.id] ?? {}
    for (const collection of collections) {
      const desiredRole = draft[collection.id] ?? roleForCollection(user, collection.id)
      const existing = users
        .filter(item => item.id !== user.id)
        .map(item => ({ userId: item.id, role: roleForCollection(item, collection.id) }))
        .filter(item => item.role)
      if (desiredRole) {
        existing.push({ userId: user.id, role: desiredRole })
      }
      const currentRole = roleForCollection(user, collection.id)
      if ((desiredRole || '') === (currentRole || '')) continue
      await setMemberships.mutateAsync({ collectionId: collection.id, memberships: existing })
    }
  }

  return (
    <div className="pb-8">
      <PageHeader
        title="Employees"
        description="Manage employee accounts, departments, global roles, and collection-scoped access without burying everything in one long form."
        actions={
          <button
            type="button"
            onClick={() => setShowCreateModal(true)}
            className="inline-flex h-10 items-center gap-2 rounded-full bg-primary px-4 text-sm font-semibold text-primary-foreground"
          >
            <Plus className="h-4 w-4" />
            New employee
          </button>
        }
      />

      <div className="grid gap-6 p-6">
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard icon={<Users className="h-8 w-8 text-primary" />} label="Employees" value={stats.total} />
          <StatCard icon={<Shield className="h-8 w-8 text-primary" />} label="Active Accounts" value={stats.active} />
          <StatCard icon={<Sparkles className="h-8 w-8 text-primary" />} label="Scoped Access" value={stats.scoped} />
          <StatCard icon={<Building2 className="h-8 w-8 text-primary" />} label="Departments" value={stats.departments} />
        </section>

        <section>
          <div className="surface-panel rounded-[2rem] border border-border/80 p-5">
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2 rounded-full border border-border/80 bg-background/70 px-4">
                <Search className="h-4 w-4 text-muted-foreground" />
                <input
                  value={searchValue}
                  onChange={event => setSearchValue(event.target.value)}
                  placeholder="Search by name, email, department..."
                  className="h-11 w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
                />
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <select value={roleFilter} onChange={event => setRoleFilter(event.target.value)} className="h-11 rounded-2xl border border-input bg-background px-4 text-sm">
                  <option value="all">All roles</option>
                  {GLOBAL_ROLES.map(role => (
                    <option key={role.value} value={role.value}>
                      {role.label}
                    </option>
                  ))}
                </select>
                <select value={statusFilter} onChange={event => setStatusFilter(event.target.value)} className="h-11 rounded-2xl border border-input bg-background px-4 text-sm">
                  <option value="all">All states</option>
                  <option value="active">Active only</option>
                  <option value="inactive">Inactive only</option>
                  <option value="scoped">Scoped access only</option>
                </select>
              </div>
            </div>

              <div className="mt-5 overflow-hidden rounded-[1.5rem] border border-border/70 bg-background/45">
                <div className="grid grid-cols-12 items-center gap-4 border-b border-border/70 px-5 py-3 text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
                  <div className="col-span-4">Employee</div>
                  <div className="col-span-3">Department</div>
                  <div className="col-span-2">Role</div>
                  <div className="col-span-2">Status</div>
                  <div className="col-span-1 text-right">Action</div>
                </div>

              {!filteredUsers.length ? (
                <div className="p-8">
                  <EmptyState icon="inbox" title="No employees match this view" description="Try a different search or filter, or create a new employee." />
                </div>
              ) : (
                <div className="divide-y divide-border/60">
                  {filteredUsers.map(user => {
                    const isSelected = user.id === selectedUser?.id
                    return (
                      <div
                        role="button"
                        tabIndex={0}
                        key={user.id}
                        onClick={() => {
                          setSelectedUserId(user.id)
                          setShowEditModal(true)
                        }}
                        onKeyDown={event => {
                          if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault()
                            setSelectedUserId(user.id)
                            setShowEditModal(true)
                          }
                        }}
                        className={`grid cursor-pointer grid-cols-12 items-center gap-4 px-5 py-4 text-left transition ${
                          isSelected ? 'bg-primary/8' : 'hover:bg-background/70'
                        }`}
                      >
                        <div className="col-span-4 min-w-0">
                          <div className="truncate text-sm font-semibold text-foreground">{user.name}</div>
                          <div className="truncate text-sm text-muted-foreground">{user.email}</div>
                        </div>
                        <div className="col-span-3 min-w-0 text-sm text-muted-foreground">
                          {user.departmentName ?? 'No department'}
                        </div>
                        <div className="col-span-2">
                          <span className="rounded-full bg-muted px-3 py-1 text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
                            {user.role}
                          </span>
                        </div>
                        <div className="col-span-2 flex flex-wrap items-center gap-2">
                          <span className="rounded-full bg-muted px-3 py-1 text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
                            {user.isActive ? 'active' : 'inactive'}
                          </span>
                          {user.scopeMode === 'restricted' && (
                            <span className="rounded-full bg-background px-3 py-1 text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
                              {user.accessibleCollectionIds.length} scoped
                            </span>
                          )}
                        </div>
                        <div className="col-span-1 flex items-center justify-end">
                          <button
                            type="button"
                            onClick={event => {
                              event.stopPropagation()
                              setSelectedUserId(user.id)
                              setShowEditModal(true)
                            }}
                            className="inline-flex h-9 items-center justify-center rounded-full border border-border bg-background px-4 text-sm font-medium transition-colors hover:border-primary/30 hover:text-foreground"
                          >
                            Edit
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        </section>
      </div>

      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/35 px-4 py-10 backdrop-blur-sm">
          <div className="surface-panel w-full max-w-3xl rounded-[2rem] border border-border/80 p-6 shadow-[0_30px_90px_rgba(25,20,15,0.22)]">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/12 text-primary">
                    <UserPlus className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="text-lg font-semibold">Create employee</div>
                    <div className="text-sm text-muted-foreground">Start with identity, global role, department, and a temporary password.</div>
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                className="rounded-full p-2 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="mt-6 grid gap-6 xl:grid-cols-[1.25fr,0.75fr]">
              <div className="grid gap-4 md:grid-cols-2">
                <label className="space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Full Name</span>
                  <input
                    value={createForm.name}
                    onChange={event => setCreateForm(current => ({ ...current, name: event.target.value }))}
                    placeholder="Nguyen Van A"
                    className="h-11 w-full rounded-2xl border border-input bg-background px-4 text-sm"
                  />
                </label>
                <label className="space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Email</span>
                  <input
                    value={createForm.email}
                    onChange={event => setCreateForm(current => ({ ...current, email: event.target.value }))}
                    placeholder="user@company.com"
                    className="h-11 w-full rounded-2xl border border-input bg-background px-4 text-sm"
                  />
                </label>
                <label className="space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Global Role</span>
                  <select
                    value={createForm.role}
                    onChange={event => setCreateForm(current => ({ ...current, role: event.target.value }))}
                    className="h-11 w-full rounded-2xl border border-input bg-background px-4 text-sm"
                  >
                    {GLOBAL_ROLES.map(role => (
                      <option key={role.value} value={role.value}>
                        {role.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Department</span>
                  <select
                    value={createForm.departmentId}
                    onChange={event => setCreateForm(current => ({ ...current, departmentId: event.target.value }))}
                    className="h-11 w-full rounded-2xl border border-input bg-background px-4 text-sm"
                  >
                    <option value="">No department</option>
                    {(departments ?? []).map(department => (
                      <option key={department.id} value={department.id}>
                        {department.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="space-y-2 md:col-span-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Temporary Password</span>
                  <input
                    type="password"
                    value={createForm.password}
                    onChange={event => setCreateForm(current => ({ ...current, password: event.target.value }))}
                    placeholder="Set a strong temporary password"
                    className="h-11 w-full rounded-2xl border border-input bg-background px-4 text-sm"
                  />
                </label>
                <label className="md:col-span-2 flex items-center gap-3 rounded-2xl border border-border/80 bg-background/60 px-4 py-3 text-sm text-muted-foreground">
                  <input
                    type="checkbox"
                    checked={createForm.isActive}
                    onChange={event => setCreateForm(current => ({ ...current, isActive: event.target.checked }))}
                  />
                  Active immediately after creation
                </label>
              </div>

              <div className="rounded-[1.75rem] border border-border/80 bg-background/60 p-4">
                <div className="text-sm font-semibold">Quick department add</div>
                <div className="mt-1 text-sm text-muted-foreground">If the department does not exist yet, create it here without leaving the modal.</div>
                <div className="mt-4 space-y-3">
                  <input
                    value={departmentForm.name}
                    onChange={event => setDepartmentForm(current => ({ ...current, name: event.target.value }))}
                    placeholder="Research Ops"
                    className="h-11 w-full rounded-2xl border border-input bg-background px-4 text-sm"
                  />
                  <textarea
                    value={departmentForm.description}
                    onChange={event => setDepartmentForm(current => ({ ...current, description: event.target.value }))}
                    rows={3}
                    placeholder="Optional note"
                    className="w-full rounded-2xl border border-input bg-background px-4 py-3 text-sm"
                  />
                  <button
                    type="button"
                    disabled={createDepartment.isPending || !departmentForm.name.trim()}
                    onClick={() =>
                      createDepartment.mutate(
                        {
                          name: departmentForm.name.trim(),
                          description: departmentForm.description.trim() || undefined,
                        },
                        {
                          onSuccess: created => {
                            setDepartmentForm(createDepartmentForm())
                            setCreateForm(current => ({ ...current, departmentId: created.id }))
                          },
                        },
                      )
                    }
                    className="inline-flex h-10 items-center justify-center rounded-full border border-border bg-card px-4 text-sm font-semibold disabled:opacity-60"
                  >
                    {createDepartment.isPending ? 'Creating...' : 'Create department'}
                  </button>
                </div>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                className="inline-flex h-10 items-center justify-center rounded-full border border-border bg-background px-4 text-sm font-medium"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={createUser.isPending}
                onClick={onCreateUser}
                className="inline-flex h-10 items-center justify-center rounded-full bg-primary px-5 text-sm font-semibold text-primary-foreground disabled:opacity-60"
              >
                {createUser.isPending ? 'Creating employee...' : 'Create employee'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showEditModal && selectedUser && (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/35 px-4 py-10 backdrop-blur-sm">
          <div className="surface-panel max-h-[90vh] w-full max-w-3xl overflow-auto rounded-[2rem] border border-border/80 p-6 shadow-[0_30px_90px_rgba(25,20,15,0.22)]">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Edit Employee</div>
                <h2 className="mt-2 text-2xl font-semibold">{selectedUser.name}</h2>
                <div className="mt-1 text-sm text-muted-foreground">{selectedUser.email}</div>
              </div>
              <button type="button" onClick={() => setShowEditModal(false)} className="rounded-full p-2 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground">
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="mt-5 space-y-5">
              <div className="grid gap-4 md:grid-cols-2">
                <label className="block space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Full Name</span>
                  <input value={profileDraft.name} onChange={event => setProfileDraft(current => ({ ...current, name: event.target.value }))} className="h-11 w-full rounded-2xl border border-input bg-background px-4 text-sm" />
                </label>
                <label className="block space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Email</span>
                  <input value={profileDraft.email} onChange={event => setProfileDraft(current => ({ ...current, email: event.target.value }))} className="h-11 w-full rounded-2xl border border-input bg-background px-4 text-sm" />
                </label>
                <label className="block space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Global Role</span>
                  <select value={profileDraft.role} onChange={event => setProfileDraft(current => ({ ...current, role: event.target.value }))} className="h-11 w-full rounded-2xl border border-input bg-background px-4 text-sm">
                    {GLOBAL_ROLES.map(role => (
                      <option key={role.value} value={role.value}>{role.label}</option>
                    ))}
                  </select>
                </label>
                <label className="block space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Department</span>
                  <select value={profileDraft.departmentId} onChange={event => setProfileDraft(current => ({ ...current, departmentId: event.target.value }))} className="h-11 w-full rounded-2xl border border-input bg-background px-4 text-sm">
                    <option value="">No department</option>
                    {(departments ?? []).map(department => (
                      <option key={department.id} value={department.id}>{department.name}</option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="rounded-[1.5rem] border border-border/80 bg-background/60 p-4">
                <label className="flex items-center gap-3 text-sm text-muted-foreground">
                  <input type="checkbox" checked={profileDraft.isActive} onChange={event => setProfileDraft(current => ({ ...current, isActive: event.target.checked }))} />
                  Active account
                </label>
              </div>

              <div className="rounded-[1.5rem] border border-border/80 bg-background/60 p-4">
                <div className="mb-3 flex items-center gap-3">
                  <KeyRound className="h-5 w-5 text-primary" />
                  <div className="text-sm font-semibold">Reset password</div>
                </div>
                <div className="flex gap-3">
                  <input type="password" value={passwordDraft} onChange={event => setPasswordDraft(event.target.value)} placeholder={`Set a new password for ${selectedUser.email}`} className="h-11 w-full rounded-2xl border border-input bg-background px-4 text-sm" />
                  <button type="button" disabled={setPassword.isPending || !passwordDraft.trim()} onClick={onResetPassword} className="inline-flex h-11 items-center justify-center rounded-full bg-primary px-5 text-sm font-semibold text-primary-foreground disabled:opacity-60">
                    {setPassword.isPending ? 'Updating...' : 'Apply'}
                  </button>
                </div>
              </div>

              <div className="rounded-[1.5rem] border border-border/80 bg-background/60 p-4">
                <div className="text-sm font-semibold">Collection Access</div>
                <div className="mt-3 space-y-3">
                  {(collections ?? []).map(collection => {
                    const currentRole = membershipDrafts[selectedUser.id]?.[collection.id] ?? roleForCollection(selectedUser, collection.id)
                    return (
                      <div key={collection.id} className="grid grid-cols-[minmax(0,1fr),220px] items-center gap-3">
                        <div>
                          <div className="text-sm font-semibold">{collection.name}</div>
                          <div className="text-xs text-muted-foreground">{collection.slug}</div>
                        </div>
                        <select
                          value={currentRole}
                          onChange={event =>
                            setMembershipDrafts(current => ({
                              ...current,
                              [selectedUser.id]: { ...(current[selectedUser.id] ?? {}), [collection.id]: event.target.value },
                            }))
                          }
                          className="h-11 w-full rounded-2xl border border-input bg-background px-4 text-sm"
                        >
                          {COLLECTION_ROLES.map(option => (
                            <option key={option.label} value={option.value}>{option.label}</option>
                          ))}
                        </select>
                      </div>
                    )
                  })}
                </div>
                <div className="mt-4 flex justify-end">
                  <button type="button" disabled={setMemberships.isPending} onClick={() => onSaveMemberships(selectedUser)} className="inline-flex h-10 items-center justify-center rounded-full bg-primary px-5 text-sm font-semibold text-primary-foreground disabled:opacity-60">
                    {setMemberships.isPending ? 'Saving...' : 'Save collection access'}
                  </button>
                </div>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button type="button" onClick={() => setShowEditModal(false)} className="inline-flex h-10 items-center justify-center rounded-full border border-border bg-background px-4 text-sm font-medium">Cancel</button>
              <button type="button" disabled={updateUser.isPending} onClick={onSaveProfile} className="inline-flex h-10 items-center justify-center rounded-full bg-primary px-5 text-sm font-semibold text-primary-foreground disabled:opacity-60">
                {updateUser.isPending ? 'Saving...' : 'Save profile'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="surface-panel rounded-[1.75rem] border border-border/80 p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{label}</div>
          <div className="mt-2 text-3xl font-semibold">{value}</div>
        </div>
        {icon}
      </div>
    </div>
  )
}
