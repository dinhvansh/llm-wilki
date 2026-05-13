import type { AuditLog, EntityDetail, Page, PageVersion, PaginatedResponse } from '@/lib/types'

import { apiRequest } from './api-client'
import type { IPageService } from './types'

function buildQuery(params?: Record<string, string | number | undefined>) {
  const searchParams = new URLSearchParams()
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== '') {
      searchParams.set(key, String(value))
    }
  })
  const query = searchParams.toString()
  return query ? `?${query}` : ''
}

export function createRealPageService(): IPageService {
  return {
    async list(params) {
      return apiRequest<PaginatedResponse<Page>>(
        `/pages${buildQuery({ page: params?.page, pageSize: params?.pageSize, status: params?.status, type: params?.type, search: params?.search, sort: params?.sort, collectionId: params?.collectionId })}`,
      )
    },
    async getBySlug(slug) {
      return apiRequest<Page>(`/pages/${slug}`)
    },
    async getEntityExplorer(params) {
      return apiRequest(`/pages/entity-explorer${buildQuery({ page: params?.page, pageSize: params?.pageSize, search: params?.search, entityType: params?.entityType })}`)
    },
    async getEntityById(entityId) {
      return apiRequest<EntityDetail>(`/pages/entity-explorer/${entityId}`)
    },
    async updateEntity(entityId, payload) {
      return apiRequest<EntityDetail>(`/pages/entity-explorer/${entityId}/update`, {
        method: 'POST',
        body: JSON.stringify(payload),
      })
    },
    async verifyEntity(entityId, payload) {
      return apiRequest<EntityDetail>(`/pages/entity-explorer/${entityId}/verify`, {
        method: 'POST',
        body: JSON.stringify(payload),
      })
    },
    async archiveEntity(entityId) {
      return apiRequest<EntityDetail>(`/pages/entity-explorer/${entityId}/archive`, { method: 'POST' })
    },
    async restoreEntity(entityId) {
      return apiRequest<EntityDetail>(`/pages/entity-explorer/${entityId}/restore`, { method: 'POST' })
    },
    async mergeEntity(entityId, payload) {
      return apiRequest<EntityDetail>(`/pages/entity-explorer/${entityId}/merge`, {
        method: 'POST',
        body: JSON.stringify(payload),
      })
    },
    async getTimelineExplorer(params) {
      return apiRequest(`/pages/timeline-explorer${buildQuery({ page: params?.page, pageSize: params?.pageSize, search: params?.search })}`)
    },
    async getGlossary(params) {
      return apiRequest(`/pages/glossary${buildQuery({ page: params?.page, pageSize: params?.pageSize, search: params?.search })}`)
    },
    async getVersions(pageId) {
      return apiRequest<PageVersion[]>(`/pages/${pageId}/versions`)
    },
    async getAudit(pageId) {
      return apiRequest<AuditLog[]>(`/pages/${pageId}/audit`)
    },
    async getDiff(pageId, versionNo) {
      return apiRequest<{ old: string; new: string }>(`/pages/${pageId}/diff?versionNo=${versionNo}`)
    },
    async compose(payload) {
      return apiRequest<Page>('/pages/compose', {
        method: 'POST',
        body: JSON.stringify({
          topic: payload.topic,
          sourceIds: payload.sourceIds ?? [],
          contentMd: payload.contentMd,
          contentJson: payload.contentJson,
          collectionId: payload.collectionId,
          pageType: payload.pageType,
        }),
      })
    },
    async publish(pageId) {
      return apiRequest<Page>(`/pages/${pageId}/publish`, { method: 'POST' })
    },
    async unpublish(pageId) {
      return apiRequest<Page>(`/pages/${pageId}/unpublish`, { method: 'POST' })
    },
    async archive(pageId) {
      return apiRequest<Page>(`/pages/${pageId}/archive`, { method: 'POST' })
    },
    async restore(pageId) {
      return apiRequest<Page>(`/pages/${pageId}/restore`, { method: 'POST' })
    },
    async update(pageId, payload) {
      return apiRequest<Page>(`/pages/${pageId}/update`, {
        method: 'POST',
        body: JSON.stringify({ contentMd: payload.contentMd, contentJson: payload.contentJson, changeSummary: 'Edited from frontend' }),
      })
    },
  }
}
