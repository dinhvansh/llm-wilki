import { AuthGuard } from '@/components/auth/auth-guard'
import { Sidebar } from '@/components/layout/sidebar'
import { TopBar } from '@/components/layout/top-bar'

export default function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <div className="flex h-screen overflow-hidden bg-background">
        <Sidebar />
        <div className="relative flex h-screen flex-1 flex-col overflow-hidden">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(182,102,58,0.14),transparent_32%),radial-gradient(circle_at_bottom_left,rgba(86,106,94,0.14),transparent_28%)]" />
          <TopBar />
          <main className="relative flex-1 overflow-y-auto overflow-x-hidden">
            <div className="mx-auto flex w-full max-w-[1680px] flex-1 flex-col px-4 pb-8 pt-4 md:px-6 xl:px-8">
              {children}
            </div>
          </main>
        </div>
      </div>
    </AuthGuard>
  )
}
