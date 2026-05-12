import type { SkillPackage } from '@/lib/types'

import { apiRequest } from './api-client'
import type { ISkillService } from './types'

export function createRealSkillService(): ISkillService {
  return {
    async list() {
      return apiRequest<SkillPackage[]>('/skills')
    },
    async get(id) {
      return apiRequest<SkillPackage>(`/skills/${id}`)
    },
    async addComment(id, comment) {
      return apiRequest<SkillPackage>(`/skills/${id}/comments`, {
        method: 'POST',
        body: JSON.stringify({ comment }),
      })
    },
    async submitReview(id, comment) {
      return apiRequest<SkillPackage>(`/skills/${id}/submit-review`, {
        method: 'POST',
        body: JSON.stringify({ comment }),
      })
    },
    async approve(id, comment) {
      return apiRequest<SkillPackage>(`/skills/${id}/approve`, {
        method: 'POST',
        body: JSON.stringify({ comment }),
      })
    },
    async release(id, comment) {
      return apiRequest<SkillPackage>(`/skills/${id}/release`, {
        method: 'POST',
        body: JSON.stringify({ comment }),
      })
    },
  }
}
