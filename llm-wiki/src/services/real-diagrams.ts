import type { AuditLog, Diagram, DiagramVersion, PaginatedResponse } from '@/lib/types'

import { apiRequest } from './api-client'
import type { IDiagramService } from './types'

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

export function createRealDiagramService(): IDiagramService {
  return {
    async list(params) {
      return apiRequest<PaginatedResponse<Diagram>>(
        `/diagrams${buildQuery({ page: params?.page, pageSize: params?.pageSize, status: params?.status, search: params?.search, collectionId: params?.collectionId, pageId: params?.pageId, sourceId: params?.sourceId })}`,
      )
    },
    async getBySlug(slug) {
      return apiRequest<Diagram>(`/diagrams/${slug}`)
    },
    async assessPage(pageId) {
      return apiRequest(`/diagrams/assess-page/${pageId}`)
    },
    async assessSource(sourceId) {
      return apiRequest(`/diagrams/assess-source/${sourceId}`)
    },
    async getVersions(diagramId) {
      return apiRequest<DiagramVersion[]>(`/diagrams/${diagramId}/versions`)
    },
    async getAudit(diagramId) {
      return apiRequest<AuditLog[]>(`/diagrams/${diagramId}/audit`)
    },
    async generateFromPage(pageId, payload) {
      return apiRequest<Diagram>(`/diagrams/from-page/${pageId}`, {
        method: 'POST',
        body: JSON.stringify(payload ?? {}),
      })
    },
    async generateFromSource(sourceId, payload) {
      return apiRequest<Diagram>(`/diagrams/from-source/${sourceId}`, {
        method: 'POST',
        body: JSON.stringify(payload ?? {}),
      })
    },
    async create(payload) {
      return apiRequest<Diagram>('/diagrams', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
    },
    async importFlow(payload) {
      return apiRequest<Diagram>('/diagrams/import', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
    },
    async update(diagramId, payload) {
      return apiRequest<Diagram>(`/diagrams/${diagramId}/update`, {
        method: 'POST',
        body: JSON.stringify(payload),
      })
    },
    async validate(diagramId) {
      return apiRequest<{ isValid: boolean; warnings: string[] }>(`/diagrams/${diagramId}/validate`, { method: 'POST' })
    },
    async exportFlow(diagramId, format) {
      return apiRequest<{ format: string; content: Diagram['flowDocument'] | string }>(`/diagrams/${diagramId}/export/${format}`)
    },
    async submitReview(diagramId) {
      return apiRequest<Diagram>(`/diagrams/${diagramId}/submit-review`, { method: 'POST' })
    },
    async approveReview(diagramId, payload) {
      return apiRequest<Diagram>(`/diagrams/${diagramId}/approve-review`, {
        method: 'POST',
        body: JSON.stringify(payload ?? {}),
      })
    },
    async requestChanges(diagramId, payload) {
      return apiRequest<Diagram>(`/diagrams/${diagramId}/request-changes`, {
        method: 'POST',
        body: JSON.stringify(payload ?? {}),
      })
    },
    async publish(diagramId) {
      return apiRequest<Diagram>(`/diagrams/${diagramId}/publish`, { method: 'POST' })
    },
    async unpublish(diagramId) {
      return apiRequest<Diagram>(`/diagrams/${diagramId}/unpublish`, { method: 'POST' })
    },
  }
}
