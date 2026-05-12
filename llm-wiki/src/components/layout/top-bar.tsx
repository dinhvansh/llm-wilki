'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Bell, BookOpen, LogOut, Search, User } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useAuth } from '@/providers/auth-provider'

function ScopePill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-full border border-border/80 bg-background/80 px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
      {label}: <span className="font-semibold text-foreground">{value}</span>
    </div>
  )
}

export function TopBar() {
  const pathname = usePathname()
  const [searchValue, setSearchValue] = useState('')
  const { user, logout } = useAuth()
  const hideTopBar = pathname.startsWith('/admin/users')

  const scopeLabel = useMemo(() => {
    if (!user) return 'guest'
    if (user.scopeMode !== 'restricted') return 'all knowledge'
    return `${user.accessibleCollectionIds.length} collections`
  }, [user])

  if (hideTopBar) {
    return null
  }

  return (
    <header className="surface-panel border-b border-border/80 px-5 py-3">
      <div className="flex flex-wrap items-center gap-3">
        <div className="min-w-[18rem] flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search pages, sources, entities, claims..."
              value={searchValue}
              onChange={e => setSearchValue(e.target.value)}
              className="h-10 w-full rounded-full border border-input bg-background/80 pl-10 pr-4 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring/30"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <ScopePill label="Scope" value={scopeLabel} />
          {user && <ScopePill label="Role" value={user.role} />}
          <Link
            href="/collections"
            className="inline-flex items-center gap-2 rounded-full border border-border/80 bg-background/70 px-3 py-2 text-sm text-muted-foreground transition-colors hover:border-primary/30 hover:text-foreground"
          >
            <BookOpen className="h-4 w-4" />
            Collections
          </Link>
          <button className="relative rounded-full border border-border/80 bg-background/70 p-2 text-muted-foreground transition-colors hover:border-primary/30 hover:text-foreground">
            <Bell className="h-4 w-4" />
            <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-primary" />
          </button>
        </div>

        <div className="ml-auto flex items-center gap-3 rounded-full border border-border/80 bg-background/80 px-3 py-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/12 text-primary">
            <User className="h-4 w-4" />
          </div>
          <div className="hidden leading-tight md:block">
            <div className="text-sm font-medium text-foreground">{user?.name}</div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              {user?.scopeMode === 'restricted' ? 'Scoped access' : 'Workspace-wide access'}
            </div>
          </div>
          <button onClick={() => logout()} className="rounded-full p-2 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground" title="Log out">
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </header>
  )
}
