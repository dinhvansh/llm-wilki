'use client'

import { Suspense, useEffect, useState, type FormEvent } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { Lock, LogIn } from 'lucide-react'

import { useAuth } from '@/providers/auth-provider'

function LoginScreen() {
  const [email, setEmail] = useState('admin@local.test')
  const [password, setPassword] = useState('admin123')
  const [error, setError] = useState('')
  const { user, isLoading, login } = useAuth()
  const router = useRouter()
  const searchParams = useSearchParams()

  useEffect(() => {
    if (!isLoading && user) {
      router.replace(searchParams.get('next') || '/')
    }
  }, [isLoading, router, searchParams, user])

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    try {
      await login(email, password)
      router.replace(searchParams.get('next') || '/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-6 py-10">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(182,102,58,0.16),transparent_28%),radial-gradient(circle_at_bottom_right,rgba(86,106,94,0.16),transparent_30%)]" />
      <div className="relative w-full max-w-md rounded-[28px] border border-border/80 bg-card/95 p-8 shadow-2xl">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
            <Lock className="h-5 w-5" />
          </div>
          <div>
            <div className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Identity Gate</div>
            <h1 className="text-2xl font-semibold tracking-tight">Sign In To Knowledge Workspace</h1>
          </div>
        </div>

        <p className="mt-4 text-sm text-muted-foreground">
          Use your workspace account to access scoped collections, review operations, and governed Ask AI flows.
        </p>

        <form onSubmit={onSubmit} className="mt-8 space-y-4">
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Email</label>
            <input
              value={email}
              onChange={event => setEmail(event.target.value)}
              className="h-11 w-full rounded-xl border border-input bg-background px-4 text-sm outline-none focus:ring-2 focus:ring-ring/30"
              autoComplete="email"
            />
          </div>
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Password</label>
            <input
              type="password"
              value={password}
              onChange={event => setPassword(event.target.value)}
              className="h-11 w-full rounded-xl border border-input bg-background px-4 text-sm outline-none focus:ring-2 focus:ring-ring/30"
              autoComplete="current-password"
            />
          </div>
          {error && <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</div>}
          <button
            type="submit"
            disabled={isLoading}
            className="flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-primary text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-60"
          >
            <LogIn className="h-4 w-4" />
            {isLoading ? 'Checking session...' : 'Sign In'}
          </button>
        </form>

        <div className="mt-6 rounded-2xl border border-border/70 bg-muted/30 p-4 text-xs text-muted-foreground">
          <div className="font-semibold uppercase tracking-[0.18em]">Local Dev Account</div>
          <div className="mt-2"><code>admin@local.test</code> / <code>admin123</code></div>
          <div className="mt-2">
            After login, admin users can manage accounts from <Link href="/admin/users" className="text-primary hover:underline">Users</Link>.
          </div>
        </div>
      </div>
    </main>
  )
}

export default function LoginPage() {
  return (
    <Suspense fallback={<main className="flex min-h-screen items-center justify-center bg-background"><div className="text-sm text-muted-foreground">Loading sign-in...</div></main>}>
      <LoginScreen />
    </Suspense>
  )
}
