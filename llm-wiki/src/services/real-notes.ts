import type { Note } from '@/lib/types'

import { apiRequest } from './api-client'
import type { INoteService } from './types'

function buildQuery(params?: Record<string, string | number | undefined>) {
  const searchParams = new URLSearchParams()
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== '') searchParams.set(key, String(value))
  })
  const query = searchParams.toString()
  return query ? `?${query}` : ''
}

export function createRealNoteService(): INoteService {
  return {
    async list(params) {
      return apiRequest<Note[]>(`/notes${buildQuery(params)}`)
    },
    async create(payload) {
      return apiRequest<Note>('/notes', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
    },
    async update(id, payload) {
      return apiRequest<Note>(`/notes/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      })
    },
    async archive(id) {
      return apiRequest<Note>(`/notes/${id}`, { method: 'DELETE' })
    },
    async createPageDraft(id) {
      return apiRequest<{ success: boolean; pageId: string; pageSlug: string }>(`/notes/${id}/page-draft`, { method: 'POST' })
    },
    async createReviewItem(id) {
      return apiRequest<{ success: boolean; reviewItemId: string }>(`/notes/${id}/review-item`, { method: 'POST' })
    },
  }
}
