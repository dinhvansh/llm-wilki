import type { Claim, Entity, ExtractionRun, Job, KnowledgeUnit, Page, PaginatedResponse, Source, SourceArtifact, SourceChunk, SourceSuggestion } from '@/lib/types'

import { apiRequest } from './api-client'
import type { ISourceService } from './types'

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

export function createRealSourceService(): ISourceService {
  return {
    async list(params) {
      return apiRequest<PaginatedResponse<Source>>(
        `/sources${buildQuery({ page: params?.page, pageSize: params?.pageSize, status: params?.status, type: params?.type, search: params?.search, collectionId: params?.collectionId })}`,
      )
    },
    async getById(id) {
      return apiRequest<Source>(`/sources/${id}`)
    },
    async getChunks(sourceId, params) {
      return apiRequest<PaginatedResponse<SourceChunk>>(`/sources/${sourceId}/chunks${buildQuery({ page: params?.page, pageSize: params?.pageSize })}`)
    },
    async getArtifacts(sourceId) {
      return apiRequest<SourceArtifact[]>(`/sources/${sourceId}/artifacts`)
    },
    async getClaims(sourceId) {
      return apiRequest<Claim[]>(`/sources/${sourceId}/claims`)
    },
    async getKnowledgeUnits(sourceId) {
      return apiRequest<KnowledgeUnit[]>(`/sources/${sourceId}/knowledge-units`)
    },
    async getExtractionRuns(sourceId) {
      return apiRequest<ExtractionRun[]>(`/sources/${sourceId}/extraction-runs`)
    },
    async getEntities(sourceId) {
      return apiRequest<Entity[]>(`/sources/${sourceId}/entities`)
    },
    async getAffectedPages(sourceId) {
      return apiRequest<Page[]>(`/sources/${sourceId}/affected-pages`)
    },
    async getSuggestions(sourceId) {
      return apiRequest<SourceSuggestion[]>(`/sources/${sourceId}/suggestions`)
    },
    async getJobs(sourceId) {
      return apiRequest<Job[]>(`/sources/${sourceId}/jobs`)
    },
    async acceptSuggestion(suggestionId) {
      return apiRequest<SourceSuggestion>(`/sources/suggestions/${suggestionId}/accept`, { method: 'POST' })
    },
    async rejectSuggestion(suggestionId) {
      return apiRequest<SourceSuggestion>(`/sources/suggestions/${suggestionId}/reject`, { method: 'POST' })
    },
    async acceptAllSuggestions(sourceId) {
      return apiRequest<{ sourceId: string; acceptedCount: number; suggestions: SourceSuggestion[] }>(`/sources/${sourceId}/suggestions/accept-all`, { method: 'POST' })
    },
    async rejectAllSuggestions(sourceId) {
      return apiRequest<{ sourceId: string; rejectedCount: number; suggestions: SourceSuggestion[] }>(`/sources/${sourceId}/suggestions/reject-all`, { method: 'POST' })
    },
    async changeSuggestionTarget(suggestionId, targetId) {
      return apiRequest<SourceSuggestion>(`/sources/suggestions/${suggestionId}/target`, {
        method: 'POST',
        body: JSON.stringify({ targetId: targetId ?? null }),
      })
    },
    async markStandalone(sourceId) {
      return apiRequest<{ sourceId: string; collectionId?: string | null }>(`/sources/${sourceId}/standalone`, { method: 'POST' })
    },
    async rebuild(sourceId) {
      return apiRequest<{ jobId: string }>(`/sources/${sourceId}/rebuild`, { method: 'POST' })
    },
    async retryJob(jobId) {
      return apiRequest<Job>(`/jobs/${jobId}/retry`, { method: 'POST' })
    },
    async cancelJob(jobId) {
      return apiRequest<Job>(`/jobs/${jobId}/cancel`, { method: 'POST' })
    },
    async archive(sourceId) {
      return apiRequest<Source>(`/sources/${sourceId}/archive`, { method: 'POST' })
    },
    async restore(sourceId) {
      return apiRequest<Source>(`/sources/${sourceId}/restore`, { method: 'POST' })
    },
    async updateMetadata(sourceId, payload) {
      return apiRequest<Source>(`/sources/${sourceId}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      })
    },
    async upload(file, collectionId) {
      const body = new FormData()
      body.append('file', file)
      if (collectionId) body.append('collectionId', collectionId)
      return apiRequest<Source>('/sources/upload', { method: 'POST', body })
    },
    async ingestUrl(payload) {
      return apiRequest<Source>('/sources/url', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
    },
    async ingestText(payload) {
      return apiRequest<Source>('/sources/text', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
    },
  }
}
