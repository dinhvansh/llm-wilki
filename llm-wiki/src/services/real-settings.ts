import type { RuntimeConnectionTestResult, RuntimeModelListResult, RuntimeSettings } from '@/lib/types'

import { apiRequest } from './api-client'
import type { ISettingsService } from './types'

export function createRealSettingsService(): ISettingsService {
  return {
    async get(): Promise<RuntimeSettings> {
      return apiRequest<RuntimeSettings>('/settings')
    },
    async update(payload: Omit<RuntimeSettings, 'updatedAt'>): Promise<RuntimeSettings> {
      return apiRequest<RuntimeSettings>('/settings', {
        method: 'PUT',
        body: JSON.stringify(payload),
      })
    },
    async testConnection(payload): Promise<RuntimeConnectionTestResult> {
      return apiRequest<RuntimeConnectionTestResult>('/settings/test', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
    },
    async loadModels(payload): Promise<RuntimeModelListResult> {
      return apiRequest<RuntimeModelListResult>('/settings/models', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
    },
  }
}
