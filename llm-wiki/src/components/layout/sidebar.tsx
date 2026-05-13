'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard, Database, FileText, CheckCircle,
  Network, Settings, ChevronLeft, ChevronRight, Boxes, Milestone, BookMarked, ShieldCheck, Activity, GitBranch, Sparkles, Building2, BadgeCheck, Trash2
} from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/providers/auth-provider'

const NAV_GROUPS = [
  {
    label: 'Workspace',
    items: [
      { label: 'Operations Home', href: '/', icon: LayoutDashboard, permission: 'dashboard:read' },
      { label: 'Collections', href: '/collections', icon: Boxes, permission: 'collection:read' },
      { label: 'Sources', href: '/sources', icon: Database, permission: 'source:read' },
      { label: 'Pages', href: '/pages', icon: FileText, permission: 'page:read' },
      { label: 'Ask AI', href: '/ask', icon: Sparkles, permission: 'ask:read' },
    ],
  },
  {
    label: 'Knowledge',
    items: [
      { label: 'Knowledge Graph', href: '/graph', icon: Network, permission: 'graph:read' },
      { label: 'Process Diagrams', href: '/diagrams', icon: GitBranch, permission: 'diagram:read' },
      { label: 'Skill Packages', href: '/skills', icon: Sparkles, permission: 'skill:read' },
      { label: 'Entity Explorer', href: '/entities', icon: Boxes, permission: 'page:read' },
      { label: 'Timeline Explorer', href: '/timeline', icon: Milestone, permission: 'timeline:read' },
      { label: 'Glossary', href: '/glossary', icon: BookMarked, permission: 'glossary:read' },
    ],
  },
  {
    label: 'Governance',
    items: [
      { label: 'Review Queue', href: '/review', icon: CheckCircle, permission: 'review:read' },
      { label: 'Lint Center', href: '/lint', icon: ShieldCheck, permission: 'lint:read' },
      { label: 'Trash', href: '/trash', icon: Trash2, permission: 'page:read' },
      { label: 'Operations', href: '/admin', icon: Activity, permission: 'admin:read', role: 'admin' },
      { label: 'Users', href: '/admin/users', icon: ShieldCheck, permission: 'admin:read', role: 'admin' },
      { label: 'Departments', href: '/admin/departments', icon: Building2, permission: 'admin:read', role: 'admin' },
      { label: 'Roles', href: '/admin/roles', icon: BadgeCheck, permission: 'admin:read', role: 'admin' },
      { label: 'Settings', href: '/settings', icon: Settings, permission: 'settings:read' },
    ],
  },
]

export function Sidebar() {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)
  const { user, hasPermission, hasRole } = useAuth()

  return (
    <aside className={cn(
      'surface-panel flex h-screen flex-col border-r border-border/80 transition-all duration-200',
      collapsed ? 'w-20' : 'w-72'
    )}>
      <div className="border-b border-border/80 px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-2xl bg-primary text-sm font-bold text-primary-foreground shadow-sm">
            WK
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold tracking-tight text-foreground">AI Knowledge Workspace</div>
              <div className="truncate text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                {user?.scopeMode === 'restricted' ? 'Collection scoped' : 'Shared workspace'}
              </div>
            </div>
          )}
        </div>
        {!collapsed && (
          <div className="surface-subtle mt-4 rounded-2xl px-3 py-3">
            <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Current access</div>
            <div className="mt-1 text-sm font-medium text-foreground">
              {user ? user.name : 'Guest session'}
            </div>
            <div className="mt-1 text-xs text-muted-foreground">
              {user?.scopeMode === 'restricted'
                ? `${user.accessibleCollectionIds.length} collections visible`
                : 'Workspace-wide visibility'}
            </div>
          </div>
        )}
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <div className="space-y-5">
          {NAV_GROUPS.map((group) => {
            const items = group.items.filter((item) => hasPermission(item.permission) && (!('role' in item) || !item.role || hasRole(item.role)))
            if (items.length === 0) return null
            return (
              <div key={group.label} className="space-y-2">
                {!collapsed && (
                  <div className="px-3 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                    {group.label}
                  </div>
                )}
                <div className="space-y-1">
                  {items.map((item) => {
                    const isActive = item.href === '/' || item.href === '/admin'
                      ? pathname === item.href
                      : pathname === item.href || pathname.startsWith(`${item.href}/`)
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        className={cn(
                          'group flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm transition-all',
                          isActive
                            ? 'bg-primary text-primary-foreground shadow-sm'
                            : 'text-muted-foreground hover:bg-accent/80 hover:text-foreground'
                        )}
                        title={collapsed ? item.label : undefined}
                      >
                        <item.icon className={cn('h-4 w-4 flex-shrink-0', isActive ? 'text-primary-foreground' : 'text-muted-foreground group-hover:text-foreground')} />
                        {!collapsed && (
                          <div className="min-w-0 flex-1">
                            <div className="truncate font-medium">{item.label}</div>
                          </div>
                        )}
                      </Link>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>
      </nav>
      <div className="border-t border-border/80 p-3">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex w-full items-center gap-2 rounded-2xl px-3 py-2 text-xs uppercase tracking-[0.16em] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          {!collapsed && <span>Collapse rail</span>}
        </button>
      </div>
    </aside>
  )
}
