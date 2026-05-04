'use client'
import { Search, Bell, LogOut, User } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useAuth } from '@/providers/auth-provider'

export function TopBar() {
  const [searchValue, setSearchValue] = useState('')
  const [email, setEmail] = useState('admin@local.test')
  const [password, setPassword] = useState('admin123')
  const [error, setError] = useState('')
  const { user, isLoading, login, logout } = useAuth()

  const onLogin = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    try {
      await login(email, password)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    }
  }

  return (
    <header className="h-14 border-b border-border bg-card flex items-center px-5 gap-4">
      <div className="flex-1 max-w-md">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search pages, sources, entities..."
            value={searchValue}
            onChange={e => setSearchValue(e.target.value)}
            className="w-full h-8 pl-8 pr-3 text-sm bg-background border border-input rounded-md placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </div>
      </div>
      <div className="flex items-center gap-3 ml-auto">
        <button className="relative p-1.5 rounded-md text-muted-foreground hover:bg-accent">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1 right-1 w-1.5 h-1.5 bg-destructive rounded-full" />
        </button>
        {user ? <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-secondary flex items-center justify-center">
            <User className="w-3.5 h-3.5 text-secondary-foreground" />
          </div>
          <div className="hidden md:block leading-tight">
            <div className="text-sm text-foreground">{user.name}</div>
            <div className="text-[11px] uppercase text-muted-foreground">{user.role}</div>
          </div>
          <button onClick={() => logout()} className="p-1.5 rounded-md text-muted-foreground hover:bg-accent" title="Log out">
            <LogOut className="w-4 h-4" />
          </button>
        </div> : (
          <form onSubmit={onLogin} className="flex items-center gap-2">
            <input
              value={email}
              onChange={event => setEmail(event.target.value)}
              className="h-8 w-36 rounded-md border border-input bg-background px-2 text-xs"
              aria-label="Email"
            />
            <input
              type="password"
              value={password}
              onChange={event => setPassword(event.target.value)}
              className="h-8 w-28 rounded-md border border-input bg-background px-2 text-xs"
              aria-label="Password"
            />
            <button disabled={isLoading} className="h-8 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground disabled:opacity-60">
              Login
            </button>
            {error && <span className="max-w-56 truncate text-xs text-destructive">{error}</span>}
          </form>
        )}
      </div>
    </header>
  )
}
