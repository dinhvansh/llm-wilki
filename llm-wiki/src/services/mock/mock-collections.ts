import type { Collection } from '@/lib/types'
import type { ICollectionService } from '../types'

import { MOCK_PAGES, MOCK_SOURCES } from './mock-data'

const delay = (ms = 200) => new Promise(resolve => setTimeout(resolve, ms))

export const MOCK_COLLECTIONS: Collection[] = [
  {
    id: 'col-001',
    name: 'Governance & Compliance',
    slug: 'governance-compliance',
    description: 'Policies, compliance processes, safety controls, and audit evidence.',
    color: 'emerald',
    sourceCount: 1,
    pageCount: 2,
    createdAt: '2025-01-01T00:00:00Z',
    updatedAt: '2025-03-01T00:00:00Z',
  },
  {
    id: 'col-002',
    name: 'Engineering Standards',
    slug: 'engineering-standards',
    description: 'LLM architecture, API standards, RAG, and technical implementation references.',
    color: 'blue',
    sourceCount: 3,
    pageCount: 4,
    createdAt: '2025-01-05T00:00:00Z',
    updatedAt: '2025-03-02T00:00:00Z',
  },
  {
    id: 'col-003',
    name: 'Operations Playbooks',
    slug: 'operations-playbooks',
    description: 'SOPs and internal workflow documentation for knowledge operations.',
    color: 'amber',
    sourceCount: 1,
    pageCount: 1,
    createdAt: '2025-01-10T00:00:00Z',
    updatedAt: '2025-03-03T00:00:00Z',
  },
]

export function createMockCollectionService(): ICollectionService {
  return {
    async list() {
      await delay()
      return MOCK_COLLECTIONS
    },
    async create(payload) {
      await delay()
      return {
        id: `col-${Date.now()}`,
        name: payload.name,
        slug: payload.name.toLowerCase().replace(/\W+/g, '-').replace(/^-|-$/g, ''),
        description: payload.description ?? '',
        color: payload.color ?? 'slate',
        sourceCount: 0,
        pageCount: 0,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      }
    },
    async update(id, payload) {
      await delay()
      const existing = MOCK_COLLECTIONS.find(collection => collection.id === id)
      if (!existing) throw new Error(`Collection ${id} not found`)
      return { ...existing, ...payload, updatedAt: new Date().toISOString() }
    },
    async delete() {
      await delay()
      return { success: true }
    },
    async assignSource(sourceId, collectionId) {
      await delay()
      if (!MOCK_SOURCES.some(source => source.id === sourceId)) throw new Error(`Source ${sourceId} not found`)
      return { sourceId, collectionId }
    },
    async assignPage(pageId, collectionId) {
      await delay()
      if (!MOCK_PAGES.some(page => page.id === pageId)) throw new Error(`Page ${pageId} not found`)
      return { pageId, collectionId }
    },
  }
}

