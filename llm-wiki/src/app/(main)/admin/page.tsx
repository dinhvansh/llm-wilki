'use client'

import { useEffect, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { PageHeader } from '@/components/layout/page-header'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { ErrorState } from '@/components/data-display/error-state'
import { apiRequest } from '@/services/api-client'

type OperationsPayload = {
  generatedAt: string
  jobMetrics: {
    total: number
    byStatus: Record<string, number>
    byType: Record<string, number>
    pending: number
    running: number
    failed: number
    durationMs: { p50?: number | null; p95?: number | null; max?: number | null }
  }
  sourceThroughput: { byIngestStatus: Record<string, number>; processedSources: number }
  failedJobDrilldown: Array<{ id: string; jobType: string; status: string; inputRef: string; errorMessage?: string | null; attempt: number; maxAttempts: number }>
}

function Metric({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-2 text-2xl font-semibold">{value ?? 'n/a'}</div>
    </div>
  )
}

export default function AdminOperationsPage() {
  const [data, setData] = useState<OperationsPayload | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [loading, setLoading] = useState(true)
  const [retrying, setRetrying] = useState(false)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await apiRequest<OperationsPayload>('/admin/operations'))
    } catch (err) {
      setError(err as Error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const bulkRetry = async () => {
    setRetrying(true)
    try {
      await apiRequest('/admin/jobs/bulk-retry', { method: 'POST', body: JSON.stringify({ limit: 20 }) })
      await load()
    } finally {
      setRetrying(false)
    }
  }

  if (loading) return <LoadingSpinner label="Loading operations..." />
  if (error) return <ErrorState message={error.message} onRetry={load} />

  return (
    <div>
      <PageHeader
        title="Operations"
        description="System health, job backlog, failures, and runtime export."
        actions={
          <button onClick={load} className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-sm hover:bg-accent">
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        }
      />
      <div className="space-y-6 p-6">
        <div className="grid gap-4 md:grid-cols-4">
          <Metric label="Jobs" value={data?.jobMetrics.total} />
          <Metric label="Pending" value={data?.jobMetrics.pending} />
          <Metric label="Running" value={data?.jobMetrics.running} />
          <Metric label="Failed" value={data?.jobMetrics.failed} />
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <Metric label="Duration p50 ms" value={data?.jobMetrics.durationMs.p50} />
          <Metric label="Duration p95 ms" value={data?.jobMetrics.durationMs.p95} />
          <Metric label="Processed sources" value={data?.sourceThroughput.processedSources} />
        </div>
        <section className="rounded-lg border border-border bg-card">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <h2 className="text-sm font-semibold">Failed Jobs</h2>
            <button onClick={bulkRetry} disabled={retrying} className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground disabled:opacity-50">
              {retrying ? 'Retrying...' : 'Bulk Retry'}
            </button>
          </div>
          <div className="divide-y divide-border">
            {data?.failedJobDrilldown.length ? data.failedJobDrilldown.map(job => (
              <div key={job.id} className="grid gap-2 px-4 py-3 text-sm md:grid-cols-[1fr_1fr_2fr]">
                <div className="font-medium">{job.id}</div>
                <div className="text-muted-foreground">{job.jobType} attempt {job.attempt}/{job.maxAttempts}</div>
                <div className="text-muted-foreground">{job.errorMessage || job.inputRef}</div>
              </div>
            )) : <div className="px-4 py-8 text-sm text-muted-foreground">No failed jobs.</div>}
          </div>
        </section>
      </div>
    </div>
  )
}
