'use client'

import { BadgeCheck, Shield, Sparkles } from 'lucide-react'

import { EmptyState } from '@/components/data-display/empty-state'
import { ErrorState } from '@/components/data-display/error-state'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { PageHeader } from '@/components/layout/page-header'
import { useAdminRoles } from '@/hooks/use-admin-users'
import { useAuth } from '@/providers/auth-provider'

export default function AdminRolesPage() {
  const { hasRole } = useAuth()
  const { data: roles, isLoading, isError, error, refetch } = useAdminRoles()

  if (!hasRole('admin')) return <ErrorState message="Only admins can view role definitions." />
  if (isLoading) return <LoadingSpinner label="Loading roles..." />
  if (isError) return <ErrorState message={(error as Error)?.message ?? 'Failed to load roles'} onRetry={() => refetch()} />

  return (
    <div className="pb-8">
      <PageHeader
        title="Roles"
        description="System role catalog and permission matrix used by the current permission engine."
      />

      <div className="grid gap-6 p-6 xl:grid-cols-[minmax(0,1fr),420px]">
        <div className="surface-panel rounded-[2rem] border border-border/80 p-5">
          {!roles?.length ? (
            <EmptyState icon="inbox" title="No roles available" description="The permission engine did not return any role definitions." />
          ) : (
            <div className="space-y-4">
              {roles.map(role => (
                <div key={role.id} className="rounded-[1.5rem] border border-border/70 bg-background/55 p-5">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-primary/12 text-primary">
                          <BadgeCheck className="h-4 w-4" />
                        </div>
                        <div className="text-lg font-semibold">{role.name}</div>
                      </div>
                      <div className="mt-2 text-sm text-muted-foreground">{role.description}</div>
                    </div>
                    <span className="rounded-full bg-muted px-3 py-1 text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
                      {role.isSystem ? 'system role' : 'custom role'}
                    </span>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    {role.permissions.map(permission => (
                      <span key={permission} className="rounded-full border border-border/80 bg-card px-3 py-1 text-xs text-muted-foreground">
                        {permission}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-6">
          <InfoCard
            icon={<Shield className="h-5 w-5" />}
            title="Why roles are separate"
            body="Users should only carry identity fields. Role definitions and permission lists belong in their own catalog so access policy can be reviewed without opening employee records."
          />
          <InfoCard
            icon={<Sparkles className="h-5 w-5" />}
            title="Current engine behavior"
            body="This build uses system roles from the backend permission matrix. The page shows the live permissions that the API enforces today."
          />
        </div>
      </div>
    </div>
  )
}

function InfoCard({ icon, title, body }: { icon: React.ReactNode; title: string; body: string }) {
  return (
    <div className="surface-panel rounded-[2rem] border border-border/80 p-5">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/12 text-primary">{icon}</div>
        <div className="text-lg font-semibold">{title}</div>
      </div>
      <div className="mt-3 text-sm leading-6 text-muted-foreground">{body}</div>
    </div>
  )
}
