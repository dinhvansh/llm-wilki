import type { DashboardStats } from '@/lib/types'
import { MOCK_DASHBOARD_STATS } from './mock-data'

// Simulate async delay
const delay = (ms = 300) => new Promise(resolve => setTimeout(resolve, ms))

export function createMockDashboardService() {
  return {
    async getStats(): Promise<DashboardStats> {
      await delay(400)
      return { ...MOCK_DASHBOARD_STATS }
    },
  }
}