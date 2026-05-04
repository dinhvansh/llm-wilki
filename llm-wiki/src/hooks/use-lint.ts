'use client'
import { useQuery } from '@tanstack/react-query'
import { lintService } from '@/services'
import type { SeverityLevel } from '@/lib/constants'

export function useLint(params?: { severity?: SeverityLevel; ruleId?: string; search?: string; pageType?: string; collectionId?: string; page?: number; pageSize?: number }) {
  return useQuery({
    queryKey: ['lint', params],
    queryFn: () => lintService.getLint(params),
  })
}
