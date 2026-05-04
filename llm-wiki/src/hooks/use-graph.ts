'use client'
import { useQuery } from '@tanstack/react-query'
import { graphService } from '@/services'
import type { PageStatus } from '@/lib/constants'

export function useGraph(params?: { nodeType?: string; status?: PageStatus; relationTypes?: string[]; entityTypes?: string[]; pageTypes?: string[]; collectionId?: string; focusId?: string; localMode?: boolean; showOrphans?: boolean; showStale?: boolean; showConflicts?: boolean; showHubs?: boolean }) {
  return useQuery({
    queryKey: ['graph', params],
    queryFn: () => graphService.getGraph(params),
  })
}
