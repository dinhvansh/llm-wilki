import type { LintResponse } from '@/lib/types'

import type { ILintService } from '../types'

const delay = (ms = 300) => new Promise(resolve => setTimeout(resolve, ms))

const MOCK_LINT: LintResponse = {
  data: [
    {
      id: 'lint-thin-summary-page-004',
      pageId: 'page-004',
      pageSlug: 'document-processing-pipeline',
      pageTitle: 'Document Processing Pipeline',
      pageStatus: 'draft',
      pageType: 'overview',
      ruleId: 'thin_summary',
      severity: 'medium',
      title: 'Summary is too thin',
      message: 'Page summary is too short for a navigational overview page.',
      suggestion: 'Expand the summary to explain scope and operational outcome.',
      metadata: { wordCount: 6 },
    },
  ],
  total: 1,
  page: 1,
  pageSize: 50,
  hasMore: false,
  summary: {
    issueCount: 1,
    affectedPages: 1,
    byRule: { thin_summary: 1 },
    bySeverity: { medium: 1 },
    rules: [{ id: 'thin_summary', label: 'Thin summary' }],
  },
}

export function createMockLintService(): ILintService {
  return {
    async getLint() {
      await delay()
      return MOCK_LINT
    },
  }
}
