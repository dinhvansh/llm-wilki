import type { AuditLog, ExplorerEntity, GlossaryTerm, Page, PageVersion, TimelineEvent } from '@/lib/types'
import { markdownToPageBlocks, pageBlocksToMarkdown } from '@/lib/page-blocks'
import type { IPageService } from '../types'
import { MOCK_PAGES, MOCK_PAGE_VERSIONS } from './mock-data'
import type { PageStatus } from '@/lib/constants'

const delay = (ms = 250) => new Promise(resolve => setTimeout(resolve, ms))

export function createMockPageService(): IPageService {
  return {
    async list(params) {
      await delay()
      let filtered = [...MOCK_PAGES]
      if (params?.status) filtered = filtered.filter(p => p.status === params.status)
      if (params?.type) filtered = filtered.filter(p => p.pageType === params.type)
      if (params?.collectionId) {
        filtered = params.collectionId === 'standalone'
          ? filtered.filter(p => !p.collectionId)
          : filtered.filter(p => p.collectionId === params.collectionId)
      }
      if (params?.search) {
        const q = params.search.toLowerCase()
        filtered = filtered.filter(p => p.title.toLowerCase().includes(q) || p.slug.toLowerCase().includes(q))
      }
      // Sort
      if (params?.sort === 'updated') filtered.sort((a, b) => new Date(b.lastComposedAt).getTime() - new Date(a.lastComposedAt).getTime())
      else if (params?.sort === 'title') filtered.sort((a, b) => a.title.localeCompare(b.title))

      const page = params?.page ?? 1
      const pageSize = params?.pageSize ?? 20
      const start = (page - 1) * pageSize
      const data = filtered.slice(start, start + pageSize)
      return { data, total: filtered.length, page, pageSize, hasMore: start + pageSize < filtered.length }
    },

    async getBySlug(slug) {
      await delay(300)
      const page = MOCK_PAGES.find(p => p.slug === slug)
      if (!page) throw new Error(`Page ${slug} not found`)
      return page
    },

    async getEntityExplorer() {
      await delay()
      return { data: [] as ExplorerEntity[], total: 0, page: 1, pageSize: 50, hasMore: false }
    },

    async getTimelineExplorer() {
      await delay()
      return { data: [] as TimelineEvent[], total: 0, page: 1, pageSize: 50, hasMore: false }
    },

    async getGlossary() {
      await delay()
      return { data: [] as GlossaryTerm[], total: 0, page: 1, pageSize: 50, hasMore: false }
    },

    async getVersions(pageId) {
      await delay(200)
      return MOCK_PAGE_VERSIONS.filter(v => v.pageId === pageId).sort((a, b) => b.versionNo - a.versionNo)
    },

    async getAudit(pageId) {
      await delay(150)
      return [
        {
          id: `audit-${pageId}-1`,
          action: 'update_content',
          objectType: 'page',
          objectId: pageId,
          actor: 'Current User',
          summary: 'Edited from frontend',
          metadataJson: {},
          createdAt: new Date().toISOString(),
        },
      ] satisfies AuditLog[]
    },

    async getDiff(pageId, versionNo) {
      await delay(300)
      const current = MOCK_PAGES.find(p => p.id === pageId)
      const version = MOCK_PAGE_VERSIONS.find(v => v.pageId === pageId && v.versionNo === versionNo)
      if (!current) throw new Error(`Page ${pageId} not found`)
      return {
        old: version?.contentMd ?? '',
        new: current.contentMd,
      }
    },

    async compose(payload) {
      await delay(1000)
      const topic = payload.topic
      const newPage: Page = {
        id: `page-${Date.now()}`,
        slug: topic.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, ''),
        title: topic,
        pageType: payload.pageType === 'deep_dive' || payload.pageType === 'overview' || payload.pageType === 'faq' ? payload.pageType : 'summary',
        status: 'draft',
        summary: `Draft page generated for topic: ${topic}`,
        contentMd: payload.contentMd || `# ${topic}\n\nDraft content for this topic...`,
        contentJson: payload.contentJson || markdownToPageBlocks(payload.contentMd || `# ${topic}\n\nDraft content for this topic...`),
        currentVersion: 1,
        lastComposedAt: new Date().toISOString(),
        owner: 'PageComposer Agent',
        tags: [],
        keyFacts: [],
        relatedSourceIds: [],
        relatedPageIds: [],
        relatedEntityIds: [],
      }
      return newPage
    },

    async publish(pageId) {
      await delay(400)
      const page = MOCK_PAGES.find(p => p.id === pageId)
      if (!page) throw new Error(`Page ${pageId} not found`)
      return { ...page, status: 'published' as PageStatus, publishedAt: new Date().toISOString() }
    },

    async unpublish(pageId) {
      await delay(400)
      const page = MOCK_PAGES.find(p => p.id === pageId)
      if (!page) throw new Error(`Page ${pageId} not found`)
      return { ...page, status: 'draft' as PageStatus }
    },

    async update(pageId, payload) {
      await delay(500)
      const page = MOCK_PAGES.find(p => p.id === pageId)
      if (!page) throw new Error(`Page ${pageId} not found`)
      return {
        ...page,
        contentMd: payload.contentMd || pageBlocksToMarkdown(payload.contentJson || page.contentJson || markdownToPageBlocks(page.contentMd)),
        contentJson: payload.contentJson || markdownToPageBlocks(payload.contentMd),
        currentVersion: page.currentVersion + 1,
        lastComposedAt: new Date().toISOString(),
      }
    },
  }
}
