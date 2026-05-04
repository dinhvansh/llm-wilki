'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard, Database, FileText, CheckCircle,
  MessageSquare, Network, Settings, ChevronLeft, ChevronRight, Boxes, Milestone, BookMarked, ShieldCheck, Activity, GitBranch
} from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/providers/auth-provider'

const NAV_ITEMS = [
  { label: 'Dashboard', href: '/', icon: LayoutDashboard },
  { label: 'Collections', href: '/collections', icon: Boxes },
  { label: 'Sources', href: '/sources', icon: Database },
  { label: 'Pages', href: '/pages', icon: FileText },
  { label: 'Process Diagrams', href: '/diagrams', icon: GitBranch },
  { label: 'Entity Explorer', href: '/entities', icon: Boxes },
  { label: 'Timeline Explorer', href: '/timeline', icon: Milestone },
  { label: 'Glossary', href: '/glossary', icon: BookMarked },
  { label: 'Review Queue', href: '/review', icon: CheckCircle },
  { label: 'Lint Center', href: '/lint', icon: ShieldCheck },
  { label: 'Ask AI', href: '/ask', icon: MessageSquare },
  { label: 'Knowledge Graph', href: '/graph', icon: Network },
  { label: 'Operations', href: '/admin', icon: Activity },
  { label: 'Settings', href: '/settings', icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)
  const { hasRole } = useAuth()

  return (
    <aside className={cn(
      'flex flex-col border-r border-border bg-card h-screen sticky top-0 transition-all duration-200',
      collapsed ? 'w-16' : 'w-56'
    )}>
      {/* Logo */}
      <div className="flex items-center gap-2 px-3 h-14 border-b border-border">
        <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center flex-shrink-0">
          <span className="text-primary-foreground text-xs font-bold">W</span>
        </div>
        {!collapsed && <span className="font-semibold text-sm">LLM Wiki</span>}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3 px-2 space-y-0.5">
        {NAV_ITEMS.filter(item => !['/settings', '/admin'].includes(item.href) || hasRole('admin')).map((item) => {
          const isActive = item.href === '/'
            ? pathname === '/'
            : pathname.startsWith(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-2.5 px-2 py-2 rounded-md text-sm transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground font-medium'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              )}
              title={collapsed ? item.label : undefined}
            >
              <item.icon className="w-4 h-4 flex-shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          )
        })}
      </nav>

      {/* Bottom */}
      <div className="p-2 border-t border-border">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center gap-2 w-full px-2 py-1.5 rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground text-xs transition-colors"
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </aside>
  )
}
