import type { Source, SourceChunk, Entity, Claim, Page, PaginatedResponse, Job } from '@/lib/types'
import type { ISourceService } from '../types'
import { MOCK_SOURCES, MOCK_CHUNKS, MOCK_ENTITIES, MOCK_CLAIMS, MOCK_PAGES } from './mock-data'
import type { SourceStatus } from '@/lib/constants'

const delay = (ms = 250) => new Promise(resolve => setTimeout(resolve, ms))

export function createMockSourceService(): ISourceService {
  const getClaimsForSource = (sourceId: string) => {
    const sourceChunkIds = MOCK_CHUNKS.filter(c => c.sourceId === sourceId).map(c => c.id)
    return MOCK_CLAIMS.filter(cl => cl.sourceChunkIds.some(id => sourceChunkIds.includes(id)))
  }

  return {
    async list(params) {
      await delay()
      let filtered = [...MOCK_SOURCES]
      if (params?.status) filtered = filtered.filter(s => s.parseStatus === params.status)
      if (params?.type) filtered = filtered.filter(s => s.sourceType === params.type)
      if (params?.collectionId) {
        filtered = params.collectionId === 'standalone'
          ? filtered.filter(s => !s.collectionId)
          : filtered.filter(s => s.collectionId === params.collectionId)
      }
      if (params?.search) {
        const q = params.search.toLowerCase()
        filtered = filtered.filter(s => s.title.toLowerCase().includes(q))
      }
      const page = params?.page ?? 1
      const pageSize = params?.pageSize ?? 20
      const start = (page - 1) * pageSize
      const data = filtered.slice(start, start + pageSize)
      return { data, total: filtered.length, page, pageSize, hasMore: start + pageSize < filtered.length }
    },

    async getById(id) {
      await delay()
      const source = MOCK_SOURCES.find(s => s.id === id)
      if (!source) throw new Error(`Source ${id} not found`)
      return source
    },

    async getChunks(sourceId, params) {
      await delay()
      const chunks = MOCK_CHUNKS.filter(c => c.sourceId === sourceId)
      const page = params?.page ?? 1
      const pageSize = params?.pageSize ?? 20
      const start = (page - 1) * pageSize
      const data = chunks.slice(start, start + pageSize)
      return { data, total: chunks.length, page, pageSize, hasMore: start + pageSize < chunks.length }
    },

    async getArtifacts(sourceId) {
      await delay(120)
      const source = MOCK_SOURCES.find(item => item.id === sourceId)
      if (!source) throw new Error(`Source ${sourceId} not found`)
      return [
        {
          id: `artifact-${sourceId}-ocr`,
          sourceId,
          artifactType: 'ocr',
          title: 'OCR And Document Parsing',
          status: 'available',
          contentType: source.mimeType,
          summary: 'Document parser metadata and OCR configuration are available.',
          previewText: 'OCR languages: eng, vie',
          metadataJson: { parser: 'mock', ocrLanguages: ['eng', 'vie'] },
        },
        {
          id: `artifact-${sourceId}-structure`,
          sourceId,
          artifactType: 'structure',
          title: 'Document Structure Map',
          status: 'available',
          contentType: 'application/json',
          summary: 'Section-level structure and source walkthrough are available.',
          previewText: 'Overview, Key Facts, Procedure',
          metadataJson: { sectionCount: 3 },
        },
      ]
    },

    async getClaims(sourceId) {
      await delay(200)
      return getClaimsForSource(sourceId)
    },

    async getKnowledgeUnits(sourceId) {
      await delay(200)
      const claims = getClaimsForSource(sourceId)
      return claims.map((claim, index) => ({
        id: `ku-${sourceId}-${index + 1}`,
        sourceId,
        sourceChunkId: claim.sourceChunkIds[0],
        claimId: claim.id,
        unitType: claim.claimType,
        title: claim.topic || claim.claimType,
        text: claim.text,
        status: 'draft',
        reviewStatus: claim.reviewStatus,
        canonicalStatus: claim.canonicalStatus,
        confidenceScore: claim.confidenceScore,
        topic: claim.topic,
        entityIds: [],
        evidenceSpanStart: claim.evidenceSpanStart ?? null,
        evidenceSpanEnd: claim.evidenceSpanEnd ?? null,
        metadataJson: claim.metadataJson || {},
        createdAt: claim.extractedAt,
        updatedAt: claim.extractedAt,
      }))
    },

    async getExtractionRuns(sourceId) {
      await delay(150)
      const chunks = MOCK_CHUNKS.filter(c => c.sourceId === sourceId)
      const claims = getClaimsForSource(sourceId)
      return [
        {
          id: `er-${sourceId}-claims`,
          sourceId,
          runType: 'claim_extraction',
          status: 'completed',
          method: 'heuristic',
          taskProfile: 'claim_extraction',
          modelProvider: 'none',
          modelName: '',
          promptVersion: 'mock',
          inputChunkCount: chunks.length,
          outputCount: claims.length,
          errorMessage: null,
          metadataJson: { claimCount: claims.length },
          startedAt: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
          finishedAt: new Date(Date.now() - 1000 * 60 * 14).toISOString(),
        },
      ]
    },

    async getEntities(sourceId) {
      await delay(200)
      // Entities are linked via pages, not directly to sources
      // For now, return all entities as a simplification
      return MOCK_ENTITIES
    },

    async getAffectedPages(sourceId) {
      await delay()
      return MOCK_PAGES.filter(p => p.relatedSourceIds.includes(sourceId))
    },

    async getSuggestions(sourceId) {
      await delay(150)
      return [
        {
          id: `sug-${sourceId}-collection`,
          sourceId,
          suggestionType: 'collection_match',
          targetType: 'collection',
          targetId: 'col-002',
          targetLabel: 'Engineering Standards',
          status: 'pending',
          confidenceScore: 0.78,
          reason: 'Collection matched by source title and tags.',
          evidence: [{ tags: ['rag', 'llm'] }],
          createdAt: new Date().toISOString(),
          decidedAt: null,
        },
      ]
    },

    async getJobs(sourceId) {
      await delay(150)
      return [
        {
          id: `job-${sourceId}-latest`,
          jobType: 'rebuild',
          status: 'completed',
          startedAt: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
          finishedAt: new Date(Date.now() - 1000 * 60 * 10).toISOString(),
          inputRef: sourceId,
          outputRef: sourceId,
        logsJson: ['Rebuild requested', 'Parsing source', 'Source indexed'],
          stepsJson: [{ name: 'parse', status: 'completed', progress: 100, details: {}, updatedAt: new Date().toISOString() }],
          progressPercent: 100,
          actor: 'Current User',
        } satisfies Job,
      ]
    },

    async acceptSuggestion(suggestionId) {
      await delay(150)
      return {
        id: suggestionId,
        sourceId: 'src-001',
        suggestionType: 'collection_match',
        targetType: 'collection',
        targetId: 'col-002',
        targetLabel: 'Engineering Standards',
        status: 'accepted',
        confidenceScore: 0.78,
        reason: 'Accepted mock suggestion.',
        evidence: [],
        createdAt: new Date().toISOString(),
        decidedAt: new Date().toISOString(),
      }
    },

    async rejectSuggestion(suggestionId) {
      await delay(150)
      return {
        id: suggestionId,
        sourceId: 'src-001',
        suggestionType: 'collection_match',
        targetType: 'collection',
        targetId: 'col-002',
        targetLabel: 'Engineering Standards',
        status: 'rejected',
        confidenceScore: 0.78,
        reason: 'Rejected mock suggestion.',
        evidence: [],
        createdAt: new Date().toISOString(),
        decidedAt: new Date().toISOString(),
      }
    },

    async acceptAllSuggestions(sourceId) {
      await delay(200)
      return { sourceId, acceptedCount: 1, suggestions: [] }
    },

    async rejectAllSuggestions(sourceId) {
      await delay(200)
      return { sourceId, rejectedCount: 1, suggestions: [] }
    },

    async changeSuggestionTarget(suggestionId, targetId) {
      await delay(150)
      return {
        id: suggestionId,
        sourceId: 'src-001',
        suggestionType: 'collection_match',
        targetType: 'collection',
        targetId,
        targetLabel: targetId ?? 'Standalone',
        status: 'pending',
        confidenceScore: 0.78,
        reason: 'Changed mock target.',
        evidence: [],
        createdAt: new Date().toISOString(),
        decidedAt: null,
      }
    },

    async markStandalone(sourceId) {
      await delay(150)
      return { sourceId, collectionId: null }
    },

    async rebuild(sourceId) {
      await delay(500)
      return { jobId: `job-rebuild-${Date.now()}` }
    },

    async retryJob(jobId) {
      await delay(200)
      return {
        id: `job-retry-${Date.now()}`,
        jobType: 'rebuild',
        status: 'pending',
        startedAt: new Date().toISOString(),
        inputRef: jobId,
        logsJson: [`Retry requested from ${jobId}`],
        stepsJson: [{ name: 'queued', status: 'pending', progress: 0, details: {}, updatedAt: new Date().toISOString() }],
        progressPercent: 0,
        actor: 'Current User',
      }
    },

    async cancelJob(jobId) {
      await delay(150)
      return {
        id: jobId,
        jobType: 'rebuild',
        status: 'canceled',
        startedAt: new Date().toISOString(),
        finishedAt: new Date().toISOString(),
        inputRef: 'mock',
        logsJson: ['Job canceled by user'],
        stepsJson: [{ name: 'cancel', status: 'canceled', progress: 0, details: {}, updatedAt: new Date().toISOString() }],
        progressPercent: 0,
        actor: 'Current User',
      }
    },

    async archive(sourceId) {
      await delay(150)
      const source = MOCK_SOURCES.find(item => item.id === sourceId)
      if (!source) throw new Error(`Source ${sourceId} not found`)
      return { ...source, metadataJson: { ...source.metadataJson, archived: true, archivedAt: new Date().toISOString() } }
    },

    async restore(sourceId) {
      await delay(150)
      const source = MOCK_SOURCES.find(item => item.id === sourceId)
      if (!source) throw new Error(`Source ${sourceId} not found`)
      return { ...source, metadataJson: { ...source.metadataJson, archived: false, restoredAt: new Date().toISOString() } }
    },

    async updateMetadata(sourceId, payload) {
      await delay(180)
      const source = MOCK_SOURCES.find(item => item.id === sourceId)
      if (!source) throw new Error(`Source ${sourceId} not found`)
      return {
        ...source,
        description: payload.description ?? source.description,
        tags: payload.tags ?? source.tags,
        trustLevel: (payload.trustLevel as Source['trustLevel']) ?? source.trustLevel,
        documentType: payload.documentType ?? source.documentType,
        sourceStatus: payload.sourceStatus ?? source.sourceStatus,
        authorityLevel: payload.authorityLevel ?? source.authorityLevel,
        effectiveDate: payload.effectiveDate ?? source.effectiveDate,
        version: payload.version ?? source.version,
        owner: payload.owner ?? source.owner,
        metadataJson: {
          ...source.metadataJson,
          ...(payload.documentType !== undefined ? { documentType: payload.documentType } : {}),
          ...(payload.sourceStatus !== undefined ? { sourceStatus: payload.sourceStatus } : {}),
          ...(payload.authorityLevel !== undefined ? { authorityLevel: payload.authorityLevel } : {}),
          ...(payload.effectiveDate !== undefined ? { effectiveDate: payload.effectiveDate } : {}),
          ...(payload.version !== undefined ? { version: payload.version } : {}),
          ...(payload.owner !== undefined ? { owner: payload.owner } : {}),
        },
      }
    },

    async upload(file, collectionId) {
      await delay(800)
      const newSource: Source = {
        id: `src-${Date.now()}`,
        title: file.name,
        sourceType: 'pdf',
        mimeType: file.type,
        uploadedAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        createdBy: 'Current User',
        parseStatus: 'uploaded',
        ingestStatus: 'uploaded',
        metadataJson: {},
        checksum: `${Date.now()}`,
        trustLevel: 'medium',
        fileSize: file.size,
        tags: [],
        collectionId,
      }
      return newSource
    },

    async ingestUrl(payload) {
      await delay(700)
      return {
        id: `src-url-${Date.now()}`,
        title: payload.title || payload.url,
        sourceType: 'url',
        mimeType: 'text/plain',
        url: payload.url,
        uploadedAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        createdBy: 'Current User',
        parseStatus: 'parsing',
        ingestStatus: 'parsing',
        metadataJson: { inputConnector: 'url', sourceKind: 'web' },
        checksum: `${Date.now()}`,
        trustLevel: 'medium',
        fileSize: 0,
        tags: [],
        collectionId: payload.collectionId,
      }
    },

    async ingestText(payload) {
      await delay(500)
      return {
        id: `src-text-${Date.now()}`,
        title: payload.title,
        sourceType: payload.sourceType || 'txt',
        mimeType: 'text/plain',
        uploadedAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        createdBy: 'Current User',
        parseStatus: 'parsing',
        ingestStatus: 'parsing',
        metadataJson: { inputConnector: payload.sourceType || 'txt' },
        checksum: `${Date.now()}`,
        trustLevel: 'medium',
        fileSize: payload.content.length,
        tags: [],
        collectionId: payload.collectionId,
      }
    },
  }
}
