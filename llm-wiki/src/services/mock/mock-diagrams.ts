import type { AuditLog, Diagram, DiagramVersion, PaginatedResponse } from '@/lib/types'
import { emptyFlowDocument } from '@/lib/openflow'

import type { IDiagramService } from '../types'

const NOW = new Date().toISOString()

let diagrams: Diagram[] = [
  {
    id: 'diag-001',
    slug: 'document-review-process',
    title: 'Document Review Process',
    objective: 'Draft, review, and publish a knowledge page with BPM ownership lanes.',
    notation: 'bpm',
    status: 'draft',
    owner: 'Knowledge Ops',
    collectionId: 'col-003',
    currentVersion: 1,
    drawioXml: '<mxGraphModel><root /></mxGraphModel>',
    specJson: {
      title: 'Document Review Process',
      actors: [{ id: 'editor', label: 'Editor' }, { id: 'reviewer', label: 'Reviewer' }, { id: 'system', label: 'System' }],
    },
    flowDocument: emptyFlowDocument('Document Review Process', 'Draft, review, and publish a knowledge page with BPM ownership lanes.', 'Knowledge Ops'),
    sourcePageIds: ['page-004'],
    sourceIds: ['src-003'],
    actorLanes: ['Editor', 'Reviewer', 'System'],
    entryPoints: ['Draft ready'],
    exitPoints: ['Published', 'Rejected'],
    relatedDiagramIds: [],
    relatedDiagrams: [],
    linkedPages: [{ id: 'page-004', slug: 'document-processing-pipeline', title: 'Document Processing Pipeline', status: 'published' }],
    linkedSources: [{ id: 'src-003', title: 'Internal SOP: Document Processing Workflow', sourceType: 'markdown', parseStatus: 'indexed' }],
    createdAt: NOW,
    updatedAt: NOW,
    publishedAt: null,
  },
]

let versions: DiagramVersion[] = [
  {
    id: 'diagver-001',
    diagramId: 'diag-001',
    versionNo: 1,
    drawioXml: '<mxGraphModel><root /></mxGraphModel>',
    specJson: { title: 'Document Review Process' },
    flowDocument: emptyFlowDocument('Document Review Process', 'Draft, review, and publish a knowledge page with BPM ownership lanes.', 'Knowledge Ops'),
    changeSummary: 'Initial diagram draft',
    createdAt: NOW,
    createdByAgentOrUser: 'Knowledge Ops',
  },
]

const auditLogs: AuditLog[] = [
  {
    id: 'audit-diag-001',
    action: 'diagram_created',
    objectType: 'diagram',
    objectId: 'diag-001',
    actor: 'Knowledge Ops',
    summary: 'Created diagram `Document Review Process`',
    metadataJson: { diagramId: 'diag-001' },
    createdAt: NOW,
  },
]

function paginate<T>(data: T[], page = 1, pageSize = 20): PaginatedResponse<T> {
  const start = (page - 1) * pageSize
  const sliced = data.slice(start, start + pageSize)
  return { data: sliced, total: data.length, page, pageSize, hasMore: start + pageSize < data.length }
}

function createLocalDiagram(payload: {
  title: string
  objective?: string
  owner?: string
  collectionId?: string | null
  actorLanes?: string[]
  sourcePageIds?: string[]
  sourceIds?: string[]
  entryPoints?: string[]
  exitPoints?: string[]
  relatedDiagramIds?: string[]
  specJson?: Record<string, unknown>
  flowDocument?: Diagram['flowDocument']
  drawioXml?: string
}): Diagram {
  const created: Diagram = {
    id: `diag-${Date.now()}`,
    slug: payload.title.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
    title: payload.title,
    objective: payload.objective ?? '',
    notation: 'bpm',
    status: 'draft',
    owner: payload.owner ?? 'Current User',
    collectionId: payload.collectionId ?? null,
    currentVersion: 1,
    drawioXml: payload.drawioXml ?? '',
    specJson: payload.specJson ?? {},
    flowDocument: payload.flowDocument ?? emptyFlowDocument(payload.title, payload.objective ?? '', payload.owner ?? 'Current User'),
    sourcePageIds: payload.sourcePageIds ?? [],
    sourceIds: payload.sourceIds ?? [],
    actorLanes: payload.actorLanes ?? [],
    entryPoints: payload.entryPoints ?? [],
    exitPoints: payload.exitPoints ?? [],
    relatedDiagramIds: payload.relatedDiagramIds ?? [],
    relatedDiagrams: [],
    linkedPages: [],
    linkedSources: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    publishedAt: null,
  }
  diagrams = [created, ...diagrams]
  versions = [{
    id: `diagver-${Date.now()}`,
    diagramId: created.id,
    versionNo: 1,
    drawioXml: created.drawioXml,
    specJson: created.specJson,
    flowDocument: created.flowDocument,
    changeSummary: 'Initial diagram draft',
    createdAt: created.createdAt,
    createdByAgentOrUser: created.owner,
  }, ...versions]
  return created
}

export function createMockDiagramService(): IDiagramService {
  return {
    async list(params) {
      let filtered = diagrams
      if (params?.status) filtered = filtered.filter(item => item.status === params.status)
      if (params?.collectionId === 'standalone') filtered = filtered.filter(item => !item.collectionId)
      else if (params?.collectionId) filtered = filtered.filter(item => item.collectionId === params.collectionId)
      if (params?.pageId) {
        const pageId = params.pageId
        filtered = filtered.filter(item => item.sourcePageIds.includes(pageId))
      }
      if (params?.sourceId) {
        const sourceId = params.sourceId
        filtered = filtered.filter(item => item.sourceIds.includes(sourceId))
      }
      if (params?.search) {
        const needle = params.search.toLowerCase()
        filtered = filtered.filter(item => `${item.title} ${item.objective}`.toLowerCase().includes(needle))
      }
      return paginate(filtered, params?.page, params?.pageSize)
    },
    async getBySlug(slug) {
      const item = diagrams.find(entry => entry.slug === slug)
      if (!item) throw new Error('Diagram not found')
      return item
    },
    async assessPage() {
      return {
        eligible: true,
        score: 0.82,
        classification: 'recommended',
        recommendedAction: 'generate_bpm',
        reasons: ['Mock page is treated as process-oriented content.'],
        pageType: 'overview',
      }
    },
    async assessSource() {
      return {
        eligible: true,
        score: 0.79,
        classification: 'recommended',
        recommendedAction: 'generate_bpm',
        reasons: ['Mock source is treated as workflow/SOP material.'],
        sourceType: 'markdown',
        tags: ['workflow'],
      }
    },
    async getVersions(diagramId) {
      return versions.filter(entry => entry.diagramId === diagramId).sort((a, b) => b.versionNo - a.versionNo)
    },
    async getAudit(diagramId) {
      return auditLogs.filter(entry => entry.objectId === diagramId)
    },
    async generateFromPage(pageId, payload) {
      return createLocalDiagram({
        title: payload?.title ?? `Generated BPM From Page ${pageId}`,
        objective: payload?.objective ?? 'AI-generated BPM draft from page content.',
        owner: 'Current User',
        specJson: {
          title: payload?.title ?? `Generated BPM From Page ${pageId}`,
          scopeSummary: 'Mock BPM draft generated from page.',
          actors: [{ id: 'owner', label: 'Current User' }, { id: 'system', label: 'System' }],
          nodes: [
            { id: 'start', type: 'start', label: 'Document ready', owner: 'Current User' },
            { id: 'task-1', type: 'task', label: 'Review extracted process', owner: 'Current User' },
            { id: 'end', type: 'end', label: 'Draft saved', owner: 'System' },
          ],
          edges: [{ from: 'start', to: 'task-1' }, { from: 'task-1', to: 'end' }],
          openQuestions: ['Confirm actual decision and exception path.'],
          validation: { isValid: false, warnings: ['Mock diagram needs review before publish.'] },
        },
        sourcePageIds: [pageId],
        actorLanes: ['Current User', 'System'],
        entryPoints: ['Document ready'],
        exitPoints: ['Draft saved'],
        drawioXml: '<mxGraphModel><root /></mxGraphModel>',
        flowDocument: emptyFlowDocument(payload?.title ?? `Generated BPM From Page ${pageId}`, payload?.objective ?? 'AI-generated BPM draft from page content.', 'Current User'),
      })
    },
    async generateFromSource(sourceId, payload) {
      return createLocalDiagram({
        title: payload?.title ?? `Generated BPM From Source ${sourceId}`,
        objective: payload?.objective ?? 'AI-generated BPM draft from source content.',
        owner: 'Current User',
        specJson: {
          title: payload?.title ?? `Generated BPM From Source ${sourceId}`,
          scopeSummary: 'Mock BPM draft generated from source.',
          actors: [{ id: 'owner', label: 'Current User' }, { id: 'system', label: 'System' }],
          nodes: [
            { id: 'start', type: 'start', label: 'Source ingested', owner: 'System' },
            { id: 'task-1', type: 'task', label: 'Draft BPM from source', owner: 'Current User' },
            { id: 'end', type: 'end', label: 'Draft saved', owner: 'System' },
          ],
          edges: [{ from: 'start', to: 'task-1' }, { from: 'task-1', to: 'end' }],
          openQuestions: ['Confirm business owner and review branch.'],
          validation: { isValid: false, warnings: ['Mock diagram needs review before publish.'] },
        },
        sourceIds: [sourceId],
        actorLanes: ['Current User', 'System'],
        entryPoints: ['Source ingested'],
        exitPoints: ['Draft saved'],
        drawioXml: '<mxGraphModel><root /></mxGraphModel>',
        flowDocument: emptyFlowDocument(payload?.title ?? `Generated BPM From Source ${sourceId}`, payload?.objective ?? 'AI-generated BPM draft from source content.', 'Current User'),
      })
    },
    async create(payload) {
      return createLocalDiagram(payload)
    },
    async update(diagramId, payload) {
      const existing = diagrams.find(entry => entry.id === diagramId)
      if (!existing) throw new Error('Diagram not found')
      const nextVersion = existing.currentVersion + 1
      const updated: Diagram = {
        ...existing,
        title: payload.title,
        slug: payload.title.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
        objective: payload.objective ?? '',
        owner: payload.owner ?? existing.owner,
        collectionId: payload.collectionId ?? null,
        drawioXml: payload.drawioXml ?? '',
        specJson: payload.specJson ?? {},
        flowDocument: payload.flowDocument ?? existing.flowDocument,
        sourcePageIds: payload.sourcePageIds ?? [],
        sourceIds: payload.sourceIds ?? [],
        actorLanes: payload.actorLanes ?? [],
        entryPoints: payload.entryPoints ?? [],
        exitPoints: payload.exitPoints ?? [],
        relatedDiagramIds: payload.relatedDiagramIds ?? [],
        relatedDiagrams: [],
        linkedPages: existing.linkedPages,
        linkedSources: existing.linkedSources,
        currentVersion: nextVersion,
        updatedAt: new Date().toISOString(),
      }
      diagrams = diagrams.map(entry => entry.id === diagramId ? updated : entry)
      versions = [{
        id: `diagver-${Date.now()}`,
        diagramId,
        versionNo: nextVersion,
        drawioXml: updated.drawioXml,
        specJson: updated.specJson,
        flowDocument: updated.flowDocument,
        changeSummary: payload.changeSummary ?? 'Updated diagram',
        createdAt: updated.updatedAt,
        createdByAgentOrUser: updated.owner,
      }, ...versions]
      return updated
    },
    async publish(diagramId) {
      const existing = diagrams.find(entry => entry.id === diagramId)
      if (!existing) throw new Error('Diagram not found')
      existing.status = 'published'
      existing.publishedAt = new Date().toISOString()
      existing.updatedAt = existing.publishedAt
      return existing
    },
    async submitReview(diagramId) {
      const existing = diagrams.find(entry => entry.id === diagramId)
      if (!existing) throw new Error('Diagram not found')
      existing.status = 'in_review'
      existing.specJson = { ...existing.specJson, reviewStatus: 'in_review' }
      existing.updatedAt = new Date().toISOString()
      return existing
    },
    async approveReview(diagramId, payload) {
      const existing = diagrams.find(entry => entry.id === diagramId)
      if (!existing) throw new Error('Diagram not found')
      existing.status = 'draft'
      existing.specJson = { ...existing.specJson, reviewStatus: 'approved', reviewComment: payload?.comment ?? '' }
      existing.updatedAt = new Date().toISOString()
      return existing
    },
    async requestChanges(diagramId, payload) {
      const existing = diagrams.find(entry => entry.id === diagramId)
      if (!existing) throw new Error('Diagram not found')
      existing.status = 'draft'
      existing.specJson = { ...existing.specJson, reviewStatus: 'changes_requested', reviewComment: payload?.comment ?? '' }
      existing.updatedAt = new Date().toISOString()
      return existing
    },
    async unpublish(diagramId) {
      const existing = diagrams.find(entry => entry.id === diagramId)
      if (!existing) throw new Error('Diagram not found')
      existing.status = 'draft'
      existing.updatedAt = new Date().toISOString()
      return existing
    },
  }
}
