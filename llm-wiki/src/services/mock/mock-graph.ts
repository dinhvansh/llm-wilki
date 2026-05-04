import type { GraphData } from '@/lib/types'
import type { IGraphService } from '../types'
import { MOCK_GRAPH_DATA } from './mock-data'

const delay = (ms = 350) => new Promise(resolve => setTimeout(resolve, ms))

export function createMockGraphService(): IGraphService {
  return {
    async getGraph(params) {
      await delay()
      if (params?.focusId) {
        const focusId = params.focusId
        const edges = MOCK_GRAPH_DATA.edges.filter(edge => edge.source === focusId || edge.target === focusId)
        const ids = new Set<string>([focusId])
        edges.forEach(edge => {
          ids.add(edge.source)
          ids.add(edge.target)
        })
        return {
          ...MOCK_GRAPH_DATA,
          nodes: MOCK_GRAPH_DATA.nodes.filter(node => ids.has(node.id)),
          edges,
          meta: {
            nodeCount: ids.size,
            edgeCount: edges.length,
            localMode: true,
            focusId,
            availableRelationTypes: [...new Set(edges.map(edge => edge.relationType))],
            availablePageTypes: [],
            availableEntityTypes: [],
          },
        }
      }
      if (params?.nodeType === 'page') {
        return {
          nodes: MOCK_GRAPH_DATA.nodes.filter(n => n.type === 'page'),
          edges: MOCK_GRAPH_DATA.edges,
          meta: { nodeCount: MOCK_GRAPH_DATA.nodes.filter(n => n.type === 'page').length, edgeCount: MOCK_GRAPH_DATA.edges.length, localMode: false, availableRelationTypes: [], availablePageTypes: [], availableEntityTypes: [] },
        }
      }
      if (params?.nodeType === 'entity') {
        return {
          nodes: MOCK_GRAPH_DATA.nodes.filter(n => n.type === 'entity'),
          edges: MOCK_GRAPH_DATA.edges,
          meta: { nodeCount: MOCK_GRAPH_DATA.nodes.filter(n => n.type === 'entity').length, edgeCount: MOCK_GRAPH_DATA.edges.length, localMode: false, availableRelationTypes: [], availablePageTypes: [], availableEntityTypes: [] },
        }
      }
      return {
        ...MOCK_GRAPH_DATA,
        meta: { nodeCount: MOCK_GRAPH_DATA.nodes.length, edgeCount: MOCK_GRAPH_DATA.edges.length, localMode: false, availableRelationTypes: [], availablePageTypes: [], availableEntityTypes: [] },
      }
    },
  }
}
