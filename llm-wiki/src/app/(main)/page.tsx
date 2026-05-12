'use client'
import { useDashboard } from '@/hooks/use-dashboard'
import { PageHeader } from '@/components/layout/page-header'
import { StatusBadge } from '@/components/data-display/status-badge'
import { EmptyState } from '@/components/data-display/empty-state'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { ErrorState } from '@/components/data-display/error-state'
import { formatRelativeTime, formatDate } from '@/lib/utils'
import {
  Database, FileText, AlertTriangle, CheckCircle, Clock,
  TrendingUp, TrendingDown, Minus, Upload, AlertCircle, RefreshCw, Eye, MessageSquare, ArrowRight
} from 'lucide-react'
import { PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, CartesianGrid } from 'recharts'
import Link from 'next/link'

function StatCard({ icon: Icon, label, value, subValue, trend }: {
  icon: React.ElementType
  label: string
  value: number | string
  subValue?: string
  trend?: 'up' | 'down' | 'neutral'
}) {
  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus
  return (
    <div className="surface-panel rounded-3xl p-5">
      <div className="flex items-start justify-between mb-2">
        <div className="rounded-2xl bg-primary/10 p-2.5">
          <Icon className="w-4 h-4 text-primary" />
        </div>
        {trend && <TrendIcon className={`w-4 h-4 ${trend === 'up' ? 'text-green-500' : trend === 'down' ? 'text-red-500' : 'text-muted-foreground'}`} />}
      </div>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-sm text-muted-foreground">{label}</div>
      {subValue && <div className="text-xs text-muted-foreground mt-0.5">{subValue}</div>}
    </div>
  )
}

function QuickActionCard({
  href,
  icon: Icon,
  title,
  description,
  cta,
}: {
  href: string
  icon: React.ElementType
  title: string
  description: string
  cta: string
}) {
  return (
    <Link
      href={href}
      className="surface-panel group rounded-[1.75rem] p-5 transition-colors hover:border-primary/40 hover:bg-accent/30"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2">
          <div className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Icon className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold">{title}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{description}</p>
          </div>
        </div>
        <ArrowRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
      </div>
      <div className="mt-4 text-sm font-medium text-primary">{cta}</div>
    </Link>
  )
}

const ACTIVITY_ICONS: Record<string, React.ElementType> = {
  source_uploaded: Upload,
  page_published: FileText,
  page_draft_created: FileText,
  review_completed: CheckCircle,
  job_failed: AlertCircle,
  claim_conflict_detected: AlertTriangle,
  source_rebuilt: RefreshCw,
}

const ACTIVITY_COLORS: Record<string, string> = {
  source_uploaded: 'text-blue-500 bg-blue-100',
  page_published: 'text-green-500 bg-green-100',
  page_draft_created: 'text-yellow-500 bg-yellow-100',
  review_completed: 'text-green-500 bg-green-100',
  job_failed: 'text-red-500 bg-red-100',
  claim_conflict_detected: 'text-orange-500 bg-orange-100',
  source_rebuilt: 'text-purple-500 bg-purple-100',
}

export default function DashboardPage() {
  const { data: stats, isLoading, isError, error, refetch } = useDashboard()

  if (isLoading) return <LoadingSpinner label="Loading dashboard..." />

  if (isError) return (
    <div>
      <PageHeader title="Dashboard" />
      <ErrorState message={(error as Error)?.message ?? 'Failed to load dashboard'} onRetry={() => refetch()} />
    </div>
  )

  if (!stats) return (
    <div>
      <PageHeader title="Dashboard" />
      <EmptyState title="No data yet" description="Upload sources to get started with your knowledge base." />
    </div>
  )

  const pieData = [
    { name: 'Published', value: stats.publishedPages, color: '#22c55e' },
    { name: 'Draft', value: stats.draftPages, color: '#f59e0b' },
    { name: 'In Review', value: stats.inReviewPages, color: '#a855f7' },
    { name: 'Stale', value: stats.stalePages, color: '#ef4444' },
  ].filter(d => d.value > 0)

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Overview of your AI knowledge base"
        actions={
          <div className="flex items-center gap-2">
            <Link
              href="/sources"
              className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-sm hover:bg-accent"
            >
              <Upload className="h-4 w-4" />
              Upload Source
            </Link>
            <Link
              href="/ask"
              className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:bg-primary/90"
            >
              <MessageSquare className="h-4 w-4" />
              Ask AI
            </Link>
            <div className="ml-2 hidden items-center gap-1.5 text-xs text-muted-foreground lg:flex">
              <Clock className="w-3.5 h-3.5" />
              Last sync: {formatRelativeTime(stats.lastSyncTime)}
            </div>
          </div>
        }
      />

      <div className="space-y-6 py-4">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <QuickActionCard
            href="/sources"
            icon={Upload}
            title="Upload knowledge sources"
            description="Add Markdown, TXT, PDF, or DOCX files to ingest and index them into the wiki."
            cta="Open source uploader"
          />
          <QuickActionCard
            href="/ask"
            icon={MessageSquare}
            title="Ask the knowledge base"
            description="Chat against indexed content and get grounded answers with citations."
            cta="Open Ask AI"
          />
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon={Database} label="Total Sources" value={stats.totalSources} subValue={`${stats.totalChunks} chunks`} trend="up" />
          <StatCard icon={FileText} label="Total Pages" value={stats.totalPages} subValue={`${stats.publishedPages} published`} trend="up" />
          <StatCard icon={AlertTriangle} label="Unverified Claims" value={stats.unverifiedClaims} trend={stats.unverifiedClaims > 10 ? 'down' : 'neutral'} />
          <StatCard icon={CheckCircle} label="Review Queue" value={stats.reviewQueueCount} subValue="items pending" trend={stats.reviewQueueCount > 0 ? 'neutral' : 'up'} />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Pages published over time */}
          <div className="surface-panel lg:col-span-2 rounded-[1.75rem] p-5">
            <h3 className="text-sm font-semibold mb-4">Pages Published Over Time</h3>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={stats.pagesPublishedOverTime}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="label" tick={{ fontSize: 10 }} tickLine={false} interval={6} />
                <YAxis tick={{ fontSize: 10 }} tickLine={false} />
                <Tooltip contentStyle={{ borderRadius: '0.375rem', border: '1px solid var(--border)' }} />
                <Line type="monotone" dataKey="value" stroke="#6366f1" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Page status pie */}
          <div className="surface-panel rounded-[1.75rem] p-5">
            <h3 className="text-sm font-semibold mb-4">Page Status Distribution</h3>
            <ResponsiveContainer width="100%" height={160}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={45} outerRadius={70} paddingAngle={3} dataKey="value">
                  {pieData.map((entry, index) => <Cell key={index} fill={entry.color} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex flex-wrap gap-2 mt-2">
              {pieData.map(d => (
                <div key={d.name} className="flex items-center gap-1 text-xs">
                  <span className="w-2 h-2 rounded-full" style={{ background: d.color }} />
                  {d.name}: {d.value}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Recent Activity + Failed Jobs */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Recent Activity */}
          <div className="surface-panel rounded-[1.75rem] p-5">
            <h3 className="text-sm font-semibold mb-3">Recent Activity</h3>
            <div className="space-y-3">
              {stats.recentActivity.map(item => {
                const Icon = ACTIVITY_ICONS[item.type] ?? Eye
                const color = ACTIVITY_COLORS[item.type] ?? 'text-gray-500 bg-gray-100'
                return (
                  <div key={item.id} className="flex items-start gap-3">
                    <div className={`p-1.5 rounded-md flex-shrink-0 ${color.split(' ')[1]}`}>
                      <Icon className={`w-3.5 h-3.5 ${color.split(' ')[0]}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm">{item.description}</p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                        {item.user && <span>{item.user}</span>}
                        <span>{formatRelativeTime(item.timestamp)}</span>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Failed Jobs */}
          <div className="surface-panel rounded-[1.75rem] p-5">
            <h3 className="text-sm font-semibold mb-3">Failed Jobs ({stats.failedJobsCount})</h3>
            {stats.failedJobs.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">No failed jobs</p>
            ) : (
              <div className="space-y-3">
                {stats.failedJobs.map(job => (
                  <div key={job.id} className="p-3 rounded-md bg-destructive/5 border border-destructive/20">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium capitalize">{job.jobType} job</span>
                      <StatusBadge status="failed" type="source" />
                    </div>
                    <p className="text-xs text-destructive">{job.errorMessage}</p>
                    <p className="text-xs text-muted-foreground mt-1">{formatDate(job.startedAt)}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
