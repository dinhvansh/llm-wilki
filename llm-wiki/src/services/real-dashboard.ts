import type { DashboardStats } from '@/lib/types'

import { apiRequest } from './api-client'
import type { IDashboardService } from './types'

export function createRealDashboardService(): IDashboardService {
  return {
    async getStats(): Promise<DashboardStats> {
      return apiRequest<DashboardStats>('/dashboard/stats')
    },
  }
}
