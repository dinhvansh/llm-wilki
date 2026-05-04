import type { LintResponse } from '@/lib/types'

import { apiRequest } from './api-client'
import type { ILintService } from './types'

export function createRealLintService(): ILintService {
  return {
    async getLint(params) {
      const searchParams = new URLSearchParams()
      if (params?.severity) searchParams.set('severity', params.severity)
      if (params?.ruleId) searchParams.set('ruleId', params.ruleId)
      if (params?.search) searchParams.set('search', params.search)
      if (params?.pageType) searchParams.set('pageType', params.pageType)
      if (params?.collectionId) searchParams.set('collectionId', params.collectionId)
      if (params?.page) searchParams.set('page', String(params.page))
      if (params?.pageSize) searchParams.set('pageSize', String(params.pageSize))
      const suffix = searchParams.toString() ? `?${searchParams.toString()}` : ''
      return apiRequest<LintResponse>(`/lint${suffix}`)
    },
  }
}
