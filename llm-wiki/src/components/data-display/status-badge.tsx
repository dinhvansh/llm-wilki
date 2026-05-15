import { cn } from '@/lib/utils'
import {
  SOURCE_STATUS_CONFIG, SOURCE_TYPE_CONFIG, PAGE_STATUS_CONFIG, PAGE_TYPE_CONFIG,
  REVIEW_ISSUE_CONFIG, SEVERITY_CONFIG, TRUST_LEVEL_CONFIG,
  ENTITY_TYPE_CONFIG, CLAIM_TYPE_CONFIG
} from '@/lib/constants'
import type { SourceStatus, PageStatus, PageType, ReviewIssueType, SeverityLevel, TrustLevel, EntityType, ClaimType } from '@/lib/constants'

interface StatusBadgeProps {
  status: string
  type?: 'source' | 'page' | 'pageType' | 'reviewIssue' | 'severity' | 'trust' | 'entity' | 'claim'
  className?: string
}

const CONFIG_MAP: Record<string, Record<string, { label: string; color: string }>> = {
  source: {
    ...SOURCE_STATUS_CONFIG,
    ...Object.fromEntries(
      Object.entries(SOURCE_TYPE_CONFIG).map(([key, value]) => [
        key,
        { label: value.label, color: 'bg-slate-100 text-slate-700' },
      ]),
    ),
  },
  page: PAGE_STATUS_CONFIG,
  pageType: PAGE_TYPE_CONFIG,
  reviewIssue: REVIEW_ISSUE_CONFIG,
  severity: SEVERITY_CONFIG,
  trust: TRUST_LEVEL_CONFIG,
  entity: ENTITY_TYPE_CONFIG,
  claim: CLAIM_TYPE_CONFIG,
}

export function StatusBadge({ status, type = 'page', className }: StatusBadgeProps) {
  const config = CONFIG_MAP[type]
  const item = config?.[status]
  if (!item) return null
  return (
    <span className={cn('inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium', item.color, className)}>
      {item.label}
    </span>
  )
}
