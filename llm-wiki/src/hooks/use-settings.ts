'use client'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import type { RuntimeSettings } from '@/lib/types'
import { settingsService } from '@/services'

export function useSettings() {
  return useQuery({
    queryKey: ['runtime-settings'],
    queryFn: () => settingsService.get(),
  })
}

export function useUpdateSettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: Omit<RuntimeSettings, 'updatedAt'>) => settingsService.update(payload),
    onSuccess: (data) => {
      queryClient.setQueryData(['runtime-settings'], data)
    },
  })
}

export function useTestSettingsConnection() {
  return useMutation({
    mutationFn: (payload: {
      provider: string
      model: string
      apiKey: string
      baseUrl: string
      timeoutSeconds: number
      purpose: string
    }) => settingsService.testConnection(payload),
  })
}
