'use client'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { collectionService } from '@/services'

export function useCollections() {
  return useQuery({
    queryKey: ['collections'],
    queryFn: () => collectionService.list(),
  })
}

export function useCreateCollection() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: { name: string; description?: string; color?: string }) => collectionService.create(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['collections'] }),
  })
}

export function useAssignSourceCollection() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ sourceId, collectionId }: { sourceId: string; collectionId?: string | null }) => collectionService.assignSource(sourceId, collectionId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['collections'] })
      qc.invalidateQueries({ queryKey: ['sources'] })
      qc.invalidateQueries({ queryKey: ['source'] })
      qc.invalidateQueries({ queryKey: ['graph'] })
    },
  })
}

export function useAssignPageCollection() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ pageId, collectionId }: { pageId: string; collectionId?: string | null }) => collectionService.assignPage(pageId, collectionId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['collections'] })
      qc.invalidateQueries({ queryKey: ['pages'] })
      qc.invalidateQueries({ queryKey: ['page'] })
      qc.invalidateQueries({ queryKey: ['graph'] })
    },
  })
}

