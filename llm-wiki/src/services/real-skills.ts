import type { SkillPackage, SkillTestResult } from '@/lib/types'

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
    async create(payload) {
      return apiRequest<SkillPackage>('/skills', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
    },
    async update(id, payload) {
      return apiRequest<SkillPackage>(`/skills/${id}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      })
    },
    async test(id, input) {
      return apiRequest<{ skill: SkillPackage; result: SkillTestResult }>(`/skills/${id}/test`, {
        method: 'POST',
        body: JSON.stringify({ input }),
      })
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
