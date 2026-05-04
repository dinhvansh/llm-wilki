import type { Collection } from '@/lib/types'

import { apiRequest } from './api-client'
import type { ICollectionService } from './types'

export function createRealCollectionService(): ICollectionService {
  return {
    async list() {
      return apiRequest<Collection[]>('/collections')
    },
    async create(payload) {
      return apiRequest<Collection>('/collections', {
        method: 'POST',
        body: JSON.stringify({ name: payload.name, description: payload.description ?? '', color: payload.color ?? 'slate' }),
      })
    },
    async update(id, payload) {
      return apiRequest<Collection>(`/collections/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ name: payload.name, description: payload.description ?? '', color: payload.color ?? 'slate' }),
      })
    },
    async delete(id) {
      return apiRequest<{ success: boolean }>(`/collections/${id}`, { method: 'DELETE' })
    },
    async assignSource(sourceId, collectionId) {
      return apiRequest<{ sourceId: string; collectionId?: string | null }>(`/collections/sources/${sourceId}/assign`, {
        method: 'POST',
        body: JSON.stringify({ collectionId: collectionId ?? null }),
      })
    },
    async assignPage(pageId, collectionId) {
      return apiRequest<{ pageId: string; collectionId?: string | null }>(`/collections/pages/${pageId}/assign`, {
        method: 'POST',
        body: JSON.stringify({ collectionId: collectionId ?? null }),
      })
    },
  }
}

