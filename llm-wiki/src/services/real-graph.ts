import type { GraphData } from '@/lib/types'

import { apiRequest } from './api-client'
import type { IGraphService } from './types'

export function createRealGraphService(): IGraphService {
  return {
    async getGraph(params) {
      const searchParams = new URLSearchParams()
      if (params?.nodeType) searchParams.set('nodeType', params.nodeType)
      if (params?.status) searchParams.set('status', params.status)
      if (params?.relationTypes?.length) searchParams.set('relationTypes', params.relationTypes.join(','))
      if (params?.entityTypes?.length) searchParams.set('entityTypes', params.entityTypes.join(','))
      if (params?.pageTypes?.length) searchParams.set('pageTypes', params.pageTypes.join(','))
      if (params?.collectionId) searchParams.set('collectionId', params.collectionId)
      if (params?.focusId) searchParams.set('focusId', params.focusId)
      if (params?.localMode) searchParams.set('localMode', 'true')
      if (params?.showOrphans) searchParams.set('showOrphans', 'true')
      if (params?.showStale) searchParams.set('showStale', 'true')
      if (params?.showConflicts) searchParams.set('showConflicts', 'true')
      if (params?.showHubs) searchParams.set('showHubs', 'true')
      const suffix = searchParams.toString() ? `?${searchParams.toString()}` : ''
      return apiRequest<GraphData>(`/graph${suffix}`)
    },
  }
}
