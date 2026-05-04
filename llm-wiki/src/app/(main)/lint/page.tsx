'use client'
import Link from 'next/link'
import { useState } from 'react'
import { AlertTriangle, Search, ShieldCheck } from 'lucide-react'

import { EmptyState } from '@/components/data-display/empty-state'
import { ErrorState } from '@/components/data-display/error-state'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { StatusBadge } from '@/components/data-display/status-badge'
import { PageHeader } from '@/components/layout/page-header'
import { useCollections } from '@/hooks/use-collections'
import { useLint } from '@/hooks/use-lint'
import type { SeverityLevel } from '@/lib/constants'
import { cn } from '@/lib/utils'

export default function LintCenterPage() {
  const [severity, setSeverity] = useState<SeverityLevel | ''>('')
  const [ruleId, setRuleId] = useState<string>('')
  const [pageType, setPageType] = useState('')
  const [collectionId, setCollectionId] = useState('')
  const [search, setSearch] = useState('')
  const { data: collections } = useCollections()
  const { data, isLoading, isError, error, refetch } = useLint({
    severity: severity || undefined,
    ruleId: ruleId || undefined,
    pageType: pageType || undefined,
    collectionId: collectionId || undefined,
    search: search || undefined,
    page: 1,
    pageSize: 100,
  })

  const issues = data?.data ?? []
  const summary = data?.summary
  const severityOptions: Array<SeverityLevel | ''> = ['', 'critical', 'high', 'medium', 'low']
  const pageTypeOptions = ['', 'overview', 'summary', 'concept', 'sop', 'entity', 'timeline', 'issue', 'glossary']

  if (isLoading) return <LoadingSpinner label="Running lint checks..." />

  if (isError) {
    return (
      <div>
        <PageHeader title="Lint Center" />
        <ErrorState message={(error as Error)?.message ?? 'Failed to load lint results'} onRetry={() => refetch()} />
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        title="Lint Center"
        description="Static content QA for pages, links, summaries, and discoverability"
        actions={
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <ShieldCheck className="h-4 w-4" />
            {summary?.issueCount ?? 0} issues across {summary?.affectedPages ?? 0} pages
          </div>
        }
      />

      <div className="space-y-6 p-6">
        <div className="grid gap-4 lg:grid-cols-4">
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Total issues</p>
            <p className="mt-2 text-2xl font-semibold">{summary?.issueCount ?? 0}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Affected pages</p>
            <p className="mt-2 text-2xl font-semibold">{summary?.affectedPages ?? 0}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">High severity</p>
            <p className="mt-2 text-2xl font-semibold">{summary?.bySeverity.high ?? 0}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Medium severity</p>
            <p className="mt-2 text-2xl font-semibold">{summary?.bySeverity.medium ?? 0}</p>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-[1.3fr_1fr]">
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2">
              <Search className="h-4 w-4 text-muted-foreground" />
              <input
                value={search}
                onChange={event => setSearch(event.target.value)}
                placeholder="Search page, rule, or message..."
                className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              />
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {severityOptions.map(value => (
                <button key={value || 'all'} onClick={() => setSeverity(value)} className={cn('rounded-md border px-2 py-1 text-xs', severity === value ? 'border-primary bg-primary text-primary-foreground' : 'border-input hover:bg-accent')}>
                  {value || 'all severities'}
                </button>
              ))}
            </div>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <select
                value={pageType}
                onChange={event => setPageType(event.target.value)}
                className="h-9 rounded-md border border-input bg-background px-2 text-sm"
              >
                {pageTypeOptions.map(value => (
                  <option key={value || 'all'} value={value}>{value || 'all page types'}</option>
                ))}
              </select>
              <select
                value={collectionId}
                onChange={event => setCollectionId(event.target.value)}
                className="h-9 rounded-md border border-input bg-background px-2 text-sm"
              >
                <option value="">all collections</option>
                <option value="standalone">standalone</option>
                {collections?.map(collection => (
                  <option key={collection.id} value={collection.id}>{collection.name}</option>
                ))}
              </select>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <button onClick={() => setRuleId('')} className={cn('rounded-md border px-2 py-1 text-xs', ruleId === '' ? 'border-primary bg-primary text-primary-foreground' : 'border-input hover:bg-accent')}>
                all rules
              </button>
              {summary?.rules.map(rule => (
                <button key={rule.id} onClick={() => setRuleId(rule.id)} className={cn('rounded-md border px-2 py-1 text-xs', ruleId === rule.id ? 'border-primary bg-primary text-primary-foreground' : 'border-input hover:bg-accent')}>
                  {rule.label}
                </button>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-sm font-semibold">Rule Breakdown</p>
            <div className="mt-3 space-y-2">
              {summary?.rules.map(rule => (
                <div key={rule.id} className="flex items-center justify-between rounded-lg border border-border bg-background px-3 py-2 text-sm">
                  <span>{rule.label}</span>
                  <span className="text-muted-foreground">{summary.byRule[rule.id] ?? 0}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {issues.length === 0 ? (
          <EmptyState icon="database" title="No lint issues" description="Current pages pass the active lint filters." />
        ) : (
          <div className="space-y-3">
            {issues.map(issue => (
              <div key={issue.id} className="rounded-xl border border-border bg-card p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-amber-600" />
                      <h3 className="text-sm font-semibold">{issue.title}</h3>
                    </div>
                    <Link href={`/pages/${issue.pageSlug}`} className="mt-1 inline-block text-sm text-primary hover:underline">
                      {issue.pageTitle}
                    </Link>
                    <p className="mt-2 text-sm text-muted-foreground">{issue.message}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <StatusBadge status={issue.severity} type="severity" />
                    <StatusBadge status={issue.pageType} type="pageType" />
                    <StatusBadge status={issue.pageStatus} type="page" />
                  </div>
                </div>
                <div className="mt-3 rounded-lg bg-muted/50 p-3">
                  <p className="text-xs font-medium text-muted-foreground">Suggested fix</p>
                  <p className="mt-1 text-sm">{issue.suggestion}</p>
                  {'quickFix' in issue.metadata && typeof issue.metadata.quickFix === 'object' && issue.metadata.quickFix !== null && (
                    <p className="mt-2 text-xs text-primary">{(issue.metadata.quickFix as { label?: string }).label}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
