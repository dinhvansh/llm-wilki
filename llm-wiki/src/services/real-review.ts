import type { Page, PaginatedResponse, ReviewItem } from '@/lib/types'

import { apiRequest } from './api-client'
import type { IReviewService } from './types'

function buildQuery(params?: Record<string, string | number | undefined>) {
  const searchParams = new URLSearchParams()
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== '') searchParams.set(key, String(value))
  })
  const query = searchParams.toString()
  return query ? `?${query}` : ''
}

export function createRealReviewService(): IReviewService {
  return {
    async getQueue(params) {
      return apiRequest<PaginatedResponse<ReviewItem>>(
        `/review-items${buildQuery({ severity: params?.severity, issueType: params?.issueType, page: params?.page, pageSize: params?.pageSize })}`,
      )
    },
    async getItem(id) {
      return apiRequest<ReviewItem>(`/review-items/${id}`)
    },
    async addComment(id, comment) {
      return apiRequest<{ id: string; reviewItemId: string; actor: string; comment: string; createdAt: string }>(`/review-items/${id}/comments`, {
        method: 'POST',
        body: JSON.stringify({ comment }),
      })
    },
    async approve(id, comment) {
      const query = comment ? `?comment=${encodeURIComponent(comment)}` : ''
      return apiRequest<{ success: boolean; page?: Page }>(`/review-items/${id}/approve${query}`, { method: 'POST' })
    },
    async reject(id, reason) {
      return apiRequest<{ success: boolean }>(`/review-items/${id}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
      })
    },
    async merge(id, payload) {
      return apiRequest<{ success: boolean; mergedPage?: Page; archivedPage?: Page; targetPageId?: string }>(`/review-items/${id}/merge`, {
        method: 'POST',
        body: JSON.stringify(payload ?? {}),
      })
    },
    async createIssuePage(id) {
      return apiRequest<{ success: boolean; issuePage?: Page; sourceReviewItemId: string }>(`/review-items/${id}/create-issue-page`, { method: 'POST' })
    },
    async requestRebuild(id) {
      return apiRequest<{ jobId: string }>(`/sources/${id}/rebuild`, { method: 'POST' })
    },
  }
}
