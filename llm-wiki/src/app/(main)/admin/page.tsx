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

type QualityReport = {
  success: boolean
  qualityGates?: Record<string, boolean>
  behaviorMetrics?: Record<string, number>
  behaviorCases?: Array<Record<string, unknown>>
  averages?: Record<string, number>
}

type QualityPayload = {
  generatedAt: string
  evalReportAvailable: boolean
  benchmarkReportAvailable: boolean
  evalReport: QualityReport | null
  benchmarkReport: QualityReport | null
  summary: {
    evalSuccess: boolean
    benchmarkSuccess: boolean
    failedBehaviorCases: number
    failedEvalGates: number
    failedBenchmarkGates: number
  }
  failedBehaviorCases: Array<Record<string, unknown>>
  failedEvalGates: Array<{ name: string; passed: boolean }>
  failedBenchmarkGates: Array<{ name: string; passed: boolean }>
  recentRuns: Array<{
    id: string
    runType: string
    runName: string
    version: string
    status: string
    success: boolean
    caseCount: number
    tags: string[]
    createdAt: string | null
    qualityGates: Record<string, boolean>
  }>
  commands: {
    eval: string
    benchmark: string
    regression: string
  }
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
  const [quality, setQuality] = useState<QualityPayload | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [loading, setLoading] = useState(true)
  const [retrying, setRetrying] = useState(false)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const [operations, qualityReport] = await Promise.all([
        apiRequest<OperationsPayload>('/admin/operations'),
        apiRequest<QualityPayload>('/admin/quality'),
      ])
      setData(operations)
      setQuality(qualityReport)
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
          <div className="border-b border-border px-4 py-3">
            <h2 className="text-sm font-semibold">Quality</h2>
            <p className="mt-1 text-sm text-muted-foreground">Latest Ask AI eval, retrieval benchmark, and quality gates.</p>
          </div>
          <div className="space-y-6 p-4">
            <div className="grid gap-4 md:grid-cols-5">
              <Metric label="Eval" value={quality?.summary.evalSuccess ? 'PASS' : 'FAIL'} />
              <Metric label="Benchmark" value={quality?.summary.benchmarkSuccess ? 'PASS' : 'FAIL'} />
              <Metric label="Failed behavior cases" value={quality?.summary.failedBehaviorCases} />
              <Metric label="Failed eval gates" value={quality?.summary.failedEvalGates} />
              <Metric label="Failed benchmark gates" value={quality?.summary.failedBenchmarkGates} />
            </div>
            <div className="grid gap-6 lg:grid-cols-2">
              <div className="rounded-lg border border-border p-4">
                <h3 className="text-sm font-semibold">Eval Gates</h3>
                <div className="mt-3 space-y-2 text-sm">
                  {quality?.evalReport?.qualityGates ? Object.entries(quality.evalReport.qualityGates).map(([name, passed]) => (
                    <div key={name} className="flex items-center justify-between rounded-md bg-accent/40 px-3 py-2">
                      <span className="font-mono text-xs">{name}</span>
                      <span className={passed ? 'text-emerald-600' : 'text-red-600'}>{passed ? 'PASS' : 'FAIL'}</span>
                    </div>
                  )) : <div className="text-muted-foreground">No eval report available.</div>}
                </div>
              </div>
              <div className="rounded-lg border border-border p-4">
                <h3 className="text-sm font-semibold">Benchmark Gates</h3>
                <div className="mt-3 space-y-2 text-sm">
                  {quality?.benchmarkReport?.qualityGates ? Object.entries(quality.benchmarkReport.qualityGates).map(([name, passed]) => (
                    <div key={name} className="flex items-center justify-between rounded-md bg-accent/40 px-3 py-2">
                      <span className="font-mono text-xs">{name}</span>
                      <span className={passed ? 'text-emerald-600' : 'text-red-600'}>{passed ? 'PASS' : 'FAIL'}</span>
                    </div>
                  )) : <div className="text-muted-foreground">No benchmark report available.</div>}
                </div>
              </div>
            </div>
            <div className="grid gap-6 lg:grid-cols-2">
              <div className="rounded-lg border border-border p-4">
                <h3 className="text-sm font-semibold">Eval Averages</h3>
                <div className="mt-3 space-y-2 text-sm">
                  {quality?.evalReport?.averages ? Object.entries(quality.evalReport.averages).map(([name, value]) => (
                    <div key={name} className="flex items-center justify-between rounded-md bg-accent/40 px-3 py-2">
                      <span className="font-mono text-xs">{name}</span>
                      <span>{String(value)}</span>
                    </div>
                  )) : <div className="text-muted-foreground">No eval averages available.</div>}
                </div>
              </div>
              <div className="rounded-lg border border-border p-4">
                <h3 className="text-sm font-semibold">Behavior Metrics</h3>
                <div className="mt-3 space-y-2 text-sm">
                  {quality?.evalReport?.behaviorMetrics ? Object.entries(quality.evalReport.behaviorMetrics).map(([name, value]) => (
                    <div key={name} className="flex items-center justify-between rounded-md bg-accent/40 px-3 py-2">
                      <span className="font-mono text-xs">{name}</span>
                      <span>{value}</span>
                    </div>
                  )) : <div className="text-muted-foreground">No behavior metrics available.</div>}
                </div>
              </div>
              <div className="rounded-lg border border-border p-4">
                <h3 className="text-sm font-semibold">Rerun Commands</h3>
                <div className="mt-3 space-y-2 text-sm">
                  {quality?.commands ? Object.entries(quality.commands).map(([name, command]) => (
                    <div key={name} className="rounded-md bg-accent/40 px-3 py-2">
                      <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{name}</div>
                      <div className="mt-1 font-mono text-xs">{command}</div>
                    </div>
                  )) : <div className="text-muted-foreground">No commands available.</div>}
                </div>
              </div>
            </div>
            <div className="rounded-lg border border-border p-4">
              <h3 className="text-sm font-semibold">Failed Behavior Cases</h3>
              <div className="mt-3 divide-y divide-border">
                {quality?.failedBehaviorCases?.length ? quality.failedBehaviorCases.map((item, index) => (
                  <div key={`${item.id ?? index}`} className="grid gap-1 py-3 text-sm md:grid-cols-[180px_140px_1fr]">
                    <div className="font-medium">{String(item.id ?? 'unknown')}</div>
                    <div className="text-muted-foreground">{String(item.type ?? 'case')}</div>
                    <div className="text-muted-foreground">
                      answerType={String(item.answerType ?? 'n/a')}
                      {item.preferredSourceTitle ? `, preferred=${String(item.preferredSourceTitle)}` : ''}
                      {Array.isArray(item.tags) && item.tags.length ? `, tags=${item.tags.join(',')}` : ''}
                    </div>
                    <div className="md:col-span-3">
                      {Array.isArray(item.citations) && item.citations.length ? (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {item.citations.map((citation: Record<string, unknown>, citationIndex: number) => (
                            <span key={`${item.id ?? index}-citation-${citationIndex}`} className="rounded-full border border-border px-2 py-1 text-xs text-muted-foreground">
                              source:{String(citation.sourceTitle ?? citation.sourceId ?? 'unknown')}
                            </span>
                          ))}
                        </div>
                      ) : null}
                      {Array.isArray(item.relatedPages) && item.relatedPages.length ? (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {item.relatedPages.map((page: Record<string, unknown>, pageIndex: number) => (
                            <a
                              key={`${item.id ?? index}-page-${pageIndex}`}
                              href={`/pages/${String(page.slug ?? '')}`}
                              className="rounded-full border border-border px-2 py-1 text-xs text-muted-foreground hover:bg-accent"
                            >
                              page:{String(page.title ?? page.slug ?? 'unknown')}
                            </a>
                          ))}
                        </div>
                      ) : null}
                      {Array.isArray(item.relatedSources) && item.relatedSources.length ? (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {item.relatedSources.map((source: Record<string, unknown>, sourceIndex: number) => (
                            <a
                              key={`${item.id ?? index}-source-${sourceIndex}`}
                              href={`/sources/${String(source.id ?? '')}`}
                              className="rounded-full border border-border px-2 py-1 text-xs text-muted-foreground hover:bg-accent"
                            >
                              source:{String(source.title ?? source.id ?? 'unknown')}
                            </a>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  </div>
                )) : <div className="py-6 text-sm text-muted-foreground">No failed behavior cases.</div>}
              </div>
            </div>
            <div className="rounded-lg border border-border p-4">
              <h3 className="text-sm font-semibold">Recent Runs</h3>
              <div className="mt-3 divide-y divide-border">
                {quality?.recentRuns?.length ? quality.recentRuns.map((run) => (
                  <div key={run.id} className="grid gap-1 py-3 text-sm md:grid-cols-[120px_1fr_120px_160px]">
                    <div className="font-medium">{run.runType}</div>
                    <div className="text-muted-foreground">
                      {run.runName} {run.version ? `(${run.version})` : ''}
                      {run.tags?.length ? ` [${run.tags.join(', ')}]` : ''}
                    </div>
                    <div className={run.success ? 'text-emerald-600' : 'text-red-600'}>{run.success ? 'PASS' : 'FAIL'}</div>
                    <div className="text-muted-foreground">{run.createdAt ? new Date(run.createdAt).toLocaleString() : 'n/a'}</div>
                  </div>
                )) : <div className="py-6 text-sm text-muted-foreground">No persisted runs yet.</div>}
              </div>
            </div>
          </div>
        </section>
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
