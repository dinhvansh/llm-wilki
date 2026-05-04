'use client'
import { useQuery } from '@tanstack/react-query'
import { dashboardService } from '@/services'

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => dashboardService.getStats(),
  })
}
