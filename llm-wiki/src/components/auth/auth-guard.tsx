'use client'

import { useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'

import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { useAuth } from '@/providers/auth-provider'

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    if (!isLoading && !user) {
      const next = pathname && pathname !== '/' ? `?next=${encodeURIComponent(pathname)}` : ''
      router.replace(`/login${next}`)
    }
  }, [isLoading, pathname, router, user])

  if (isLoading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <LoadingSpinner label="Checking session..." />
      </div>
    )
  }

  return <>{children}</>
}
