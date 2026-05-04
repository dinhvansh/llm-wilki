import type { ReviewItem, Page, PaginatedResponse } from '@/lib/types'
import type { IReviewService } from '../types'
import { MOCK_REVIEW_ITEMS, MOCK_PAGES } from './mock-data'

const delay = (ms = 300) => new Promise(resolve => setTimeout(resolve, ms))

export function createMockReviewService(): IReviewService {
  return {
    async getQueue(params) {
      await delay()
      let filtered = [...MOCK_REVIEW_ITEMS]
      if (params?.severity) filtered = filtered.filter(r => r.severity === params.severity)
      if (params?.issueType) filtered = filtered.filter(r => r.issueType === params.issueType)
      const page = params?.page ?? 1
      const pageSize = params?.pageSize ?? 20
      const start = (page - 1) * pageSize
      const data = filtered.slice(start, start + pageSize)
      return { data, total: filtered.length, page, pageSize, hasMore: start + pageSize < filtered.length }
    },

    async getItem(id) {
      await delay(200)
      const item = MOCK_REVIEW_ITEMS.find(r => r.id === id)
      if (!item) throw new Error(`Review item ${id} not found`)
      return item
    },

    async approve(id, _comment) {
      await delay(400)
      const item = MOCK_REVIEW_ITEMS.find(r => r.id === id)
      if (!item) throw new Error(`Review item ${id} not found`)
      const page = MOCK_PAGES.find(p => p.id === item.pageId)
      return { success: true, page }
    },

    async reject(id, reason) {
      await delay(400)
      const item = MOCK_REVIEW_ITEMS.find(r => r.id === id)
      if (!item) throw new Error(`Review item ${id} not found`)
      return { success: true }
    },

    async merge(id, payload) {
      await delay(450)
      const item = MOCK_REVIEW_ITEMS.find(r => r.id === id)
      if (!item) throw new Error(`Review item ${id} not found`)
      const mergedPage = MOCK_PAGES.find(p => p.id === (payload?.targetPageId ?? item.suggestions?.[0]?.targetId))
      const archivedPage = MOCK_PAGES.find(p => p.id === item.pageId)
      return { success: true, mergedPage, archivedPage, targetPageId: mergedPage?.id }
    },

    async createIssuePage(id) {
      await delay(350)
      const item = MOCK_REVIEW_ITEMS.find(r => r.id === id)
      if (!item) throw new Error(`Review item ${id} not found`)
      const issuePage = MOCK_PAGES.find(p => p.id === item.pageId)
      return { success: true, issuePage, sourceReviewItemId: id }
    },

    async requestRebuild(id) {
      await delay(500)
      return { jobId: `job-rebuild-${Date.now()}` }
    },
  }
}
