import type { AskResponse, ChatSession, ChatSessionDetail, SearchResult } from '@/lib/types'

import { apiRequest } from './api-client'
import type { IQueryService } from './types'

export function createRealQueryService(): IQueryService {
  return {
    async ask(question, sessionId, scope) {
      return apiRequest<AskResponse>('/ask', {
        method: 'POST',
        body: JSON.stringify({
          question,
          sessionId,
          sourceId: scope?.sourceId ?? null,
          collectionId: scope?.collectionId ?? null,
          pageId: scope?.pageId ?? null,
        }),
      })
    },
    async listChatSessions(limit = 30) {
      return apiRequest<ChatSession[]>(`/ask/sessions?limit=${limit}`)
    },
    async getChatSession(sessionId) {
      return apiRequest<ChatSessionDetail>(`/ask/sessions/${sessionId}`)
    },
    async deleteChatSession(sessionId) {
      return apiRequest<{ success: boolean }>(`/ask/sessions/${sessionId}`, { method: 'DELETE' })
    },
    async search(query, params) {
      const searchParams = new URLSearchParams({ query })
      if (params?.type) searchParams.set('type', params.type)
      if (params?.limit) searchParams.set('limit', String(params.limit))
      return apiRequest<SearchResult[]>(`/search?${searchParams.toString()}`)
    },
  }
}
