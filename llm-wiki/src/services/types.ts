import type {
  Source, SourceChunk, SourceSuggestion, Page, PageVersion, Diagram, DiagramVersion, AuditLog, ReviewItem, Job,
  DashboardStats, GraphData, AskResponse, ChatSession, ChatSessionDetail, SearchResult,
  PaginatedResponse, Entity, EntityDetail, Claim, RuntimeConnectionTestResult, RuntimeSettings, ExplorerEntity, TimelineEvent, GlossaryTerm, LintResponse, Collection,
  KnowledgeUnit, ExtractionRun, SourceArtifact, SkillPackage, SkillTestResult, ManagedUser, Department, AdminRole, Note
} from '@/lib/types'
import type { PageBlock } from '@/lib/page-blocks'
import type { PageStatus, SourceStatus, SeverityLevel, ReviewIssueType } from '@/lib/constants'

export interface ISourceService {
  list(params?: { page?: number; pageSize?: number; status?: SourceStatus; type?: string; search?: string; collectionId?: string }): Promise<PaginatedResponse<Source>>
  getById(id: string): Promise<Source>
  getChunks(sourceId: string, params?: { page?: number; pageSize?: number }): Promise<PaginatedResponse<SourceChunk>>
  getArtifacts(sourceId: string): Promise<SourceArtifact[]>
  getClaims(sourceId: string): Promise<Claim[]>
  getKnowledgeUnits(sourceId: string): Promise<KnowledgeUnit[]>
  getExtractionRuns(sourceId: string): Promise<ExtractionRun[]>
  getEntities(sourceId: string): Promise<Entity[]>
  getAffectedPages(sourceId: string): Promise<Page[]>
  getSuggestions(sourceId: string): Promise<SourceSuggestion[]>
  getJobs(sourceId: string): Promise<Job[]>
  acceptSuggestion(suggestionId: string): Promise<SourceSuggestion>
  rejectSuggestion(suggestionId: string): Promise<SourceSuggestion>
  acceptAllSuggestions(sourceId: string): Promise<{ sourceId: string; acceptedCount: number; suggestions: SourceSuggestion[] }>
  rejectAllSuggestions(sourceId: string): Promise<{ sourceId: string; rejectedCount: number; suggestions: SourceSuggestion[] }>
  changeSuggestionTarget(suggestionId: string, targetId?: string | null): Promise<SourceSuggestion>
  markStandalone(sourceId: string): Promise<{ sourceId: string; collectionId?: string | null }>
  rebuild(sourceId: string): Promise<{ jobId: string }>
  retryJob(jobId: string): Promise<Job>
  cancelJob(jobId: string): Promise<Job>
  archive(sourceId: string): Promise<Source>
  restore(sourceId: string): Promise<Source>
  updateMetadata(sourceId: string, payload: {
    description?: string | null
    tags?: string[]
    trustLevel?: string | null
    documentType?: string | null
    sourceStatus?: string | null
    authorityLevel?: string | null
    effectiveDate?: string | null
    version?: string | null
    owner?: string | null
  }): Promise<Source>
  upload(file: File, collectionId?: string): Promise<Source>
  ingestUrl(payload: { url: string; title?: string; collectionId?: string }): Promise<Source>
  ingestText(payload: { title: string; content: string; sourceType?: 'txt' | 'transcript'; collectionId?: string }): Promise<Source>
}

export interface INoteService {
  list(params?: { sourceId?: string; pageId?: string; collectionId?: string; search?: string; limit?: number }): Promise<Note[]>
  create(payload: {
    title: string
    body?: string
    scope?: 'private' | 'collection' | 'workspace' | string
    collectionId?: string | null
    tags?: string[]
    anchors?: Array<Record<string, unknown>>
    metadataJson?: Record<string, unknown>
  }): Promise<Note>
  update(id: string, payload: { title?: string; body?: string; tags?: string[] }): Promise<Note>
  archive(id: string): Promise<Note>
  createPageDraft(id: string): Promise<{ success: boolean; pageId: string; pageSlug: string }>
  createReviewItem(id: string): Promise<{ success: boolean; reviewItemId: string }>
}

export interface ICollectionService {
  list(): Promise<Collection[]>
  create(payload: { name: string; description?: string; color?: string }): Promise<Collection>
  update(id: string, payload: { name: string; description?: string; color?: string }): Promise<Collection>
  delete(id: string): Promise<{ success: boolean }>
  assignSource(sourceId: string, collectionId?: string | null): Promise<{ sourceId: string; collectionId?: string | null }>
  assignPage(pageId: string, collectionId?: string | null): Promise<{ pageId: string; collectionId?: string | null }>
  setMemberships(collectionId: string, memberships: Array<{ userId: string; role: string }>): Promise<{ collectionId: string; memberships: Array<{ userId: string; role: string }> }>
}

export interface IPageService {
  list(params?: { page?: number; pageSize?: number; status?: PageStatus; type?: string; search?: string; sort?: string; collectionId?: string }): Promise<PaginatedResponse<Page>>
  getBySlug(slug: string): Promise<Page>
  getEntityExplorer(params?: { page?: number; pageSize?: number; search?: string; entityType?: string }): Promise<PaginatedResponse<ExplorerEntity>>
  getEntityById(entityId: string): Promise<EntityDetail>
  updateEntity(entityId: string, payload: { name: string; entityType: string; description: string; aliases: string[] }): Promise<EntityDetail>
  verifyEntity(entityId: string, payload: { verificationStatus: string }): Promise<EntityDetail>
  archiveEntity(entityId: string): Promise<EntityDetail>
  restoreEntity(entityId: string): Promise<EntityDetail>
  mergeEntity(entityId: string, payload: { targetEntityId: string }): Promise<EntityDetail>
  getTimelineExplorer(params?: { page?: number; pageSize?: number; search?: string }): Promise<PaginatedResponse<TimelineEvent>>
  getGlossary(params?: { page?: number; pageSize?: number; search?: string }): Promise<PaginatedResponse<GlossaryTerm>>
  getVersions(pageId: string): Promise<PageVersion[]>
  getAudit(pageId: string): Promise<AuditLog[]>
  getDiff(pageId: string, versionNo: number): Promise<{ old: string; new: string }>
  compose(payload: { topic: string; sourceIds?: string[]; contentMd?: string; contentJson?: PageBlock[]; collectionId?: string; pageType?: string }): Promise<Page>
  publish(pageId: string): Promise<Page>
  unpublish(pageId: string): Promise<Page>
  archive(pageId: string): Promise<Page>
  restore(pageId: string): Promise<Page>
  update(pageId: string, payload: { contentMd: string; contentJson?: PageBlock[] }): Promise<Page>
}

export interface IDiagramService {
  list(params?: { page?: number; pageSize?: number; status?: string; search?: string; collectionId?: string; pageId?: string; sourceId?: string }): Promise<PaginatedResponse<Diagram>>
  getBySlug(slug: string): Promise<Diagram>
  assessPage(pageId: string): Promise<{ eligible: boolean; score: number; classification: string; recommendedAction: string; reasons: string[]; pageType?: string }>
  assessSource(sourceId: string): Promise<{ eligible: boolean; score: number; classification: string; recommendedAction: string; reasons: string[]; sourceType?: string; tags?: string[] }>
  getVersions(diagramId: string): Promise<DiagramVersion[]>
  getAudit(diagramId: string): Promise<AuditLog[]>
  generateFromPage(pageId: string, payload?: { title?: string; objective?: string }): Promise<Diagram>
  generateFromSource(sourceId: string, payload?: { title?: string; objective?: string }): Promise<Diagram>
  create(payload: {
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
    drawioXml?: string
  }): Promise<Diagram>
  update(diagramId: string, payload: {
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
    drawioXml?: string
    changeSummary?: string
    expectedVersion?: number
  }): Promise<Diagram>
  submitReview(diagramId: string): Promise<Diagram>
  approveReview(diagramId: string, payload?: { comment?: string }): Promise<Diagram>
  requestChanges(diagramId: string, payload?: { comment?: string }): Promise<Diagram>
  publish(diagramId: string): Promise<Diagram>
  unpublish(diagramId: string): Promise<Diagram>
}

export interface IReviewService {
  getQueue(params?: { severity?: SeverityLevel; issueType?: ReviewIssueType; page?: number; pageSize?: number }): Promise<PaginatedResponse<ReviewItem>>
  getItem(id: string): Promise<ReviewItem>
  addComment(id: string, comment: string): Promise<{ id: string; reviewItemId: string; actor: string; comment: string; createdAt: string }>
  approve(id: string, comment?: string): Promise<{ success: boolean; page?: Page }>
  reject(id: string, reason: string): Promise<{ success: boolean }>
  merge(id: string, payload?: { targetPageId?: string; comment?: string }): Promise<{ success: boolean; mergedPage?: Page; archivedPage?: Page; targetPageId?: string }>
  createIssuePage(id: string): Promise<{ success: boolean; issuePage?: Page; sourceReviewItemId: string }>
  requestRebuild(id: string): Promise<{ jobId: string }>
}

export interface ISkillService {
  list(): Promise<SkillPackage[]>
  get(id: string): Promise<SkillPackage>
  create(payload: {
    id?: string
    name: string
    version?: string
    scope?: string
    status?: string
    reviewStatus?: string
    summary?: string
    description?: string
    instructions?: string
    capabilities?: string[]
    tags?: string[]
    entryPoints?: string[]
    owner?: string | null
    taskProfile?: string
    metadataJson?: Record<string, unknown>
    changeComment?: string
  }): Promise<SkillPackage>
  update(id: string, payload: {
    name: string
    version?: string
    scope?: string
    status?: string
    reviewStatus?: string
    summary?: string
    description?: string
    instructions?: string
    capabilities?: string[]
    tags?: string[]
    entryPoints?: string[]
    owner?: string | null
    taskProfile?: string
    metadataJson?: Record<string, unknown>
    changeComment?: string
  }): Promise<SkillPackage>
  test(id: string, input: string): Promise<{ skill: SkillPackage; result: SkillTestResult }>
  addComment(id: string, comment: string): Promise<SkillPackage>
  submitReview(id: string, comment?: string): Promise<SkillPackage>
  approve(id: string, comment?: string): Promise<SkillPackage>
  release(id: string, comment?: string): Promise<SkillPackage>
}

export interface IAdminService {
  listUsers(): Promise<ManagedUser[]>
  createUser(payload: { email: string; name: string; role: string; password: string; departmentId?: string | null; isActive?: boolean }): Promise<ManagedUser>
  updateUser(userId: string, payload: { email?: string; name?: string; role?: string; departmentId?: string | null; isActive?: boolean }): Promise<ManagedUser>
  setUserPassword(userId: string, password: string): Promise<{ success: boolean; user: ManagedUser }>
  listDepartments(): Promise<Department[]>
  createDepartment(payload: { name: string; description?: string }): Promise<Department>
  updateDepartment(departmentId: string, payload: { name?: string; description?: string }): Promise<Department>
  listRoles(): Promise<AdminRole[]>
}

export interface IQueryService {
  ask(
    question: string,
    sessionId?: string | null,
    scope?: { sourceId?: string | null; collectionId?: string | null; pageId?: string | null },
  ): Promise<AskResponse>
  listChatSessions(limit?: number): Promise<ChatSession[]>
  getChatSession(sessionId: string): Promise<ChatSessionDetail>
  deleteChatSession(sessionId: string): Promise<{ success: boolean }>
  search(query: string, params?: { type?: string; limit?: number }): Promise<SearchResult[]>
}

export interface IGraphService {
  getGraph(params?: { nodeType?: string; status?: PageStatus; relationTypes?: string[]; entityTypes?: string[]; pageTypes?: string[]; collectionId?: string; focusId?: string; localMode?: boolean; showOrphans?: boolean; showStale?: boolean; showConflicts?: boolean; showHubs?: boolean }): Promise<GraphData>
}

export interface ILintService {
  getLint(params?: { severity?: SeverityLevel; ruleId?: string; search?: string; pageType?: string; collectionId?: string; page?: number; pageSize?: number }): Promise<LintResponse>
}

export interface IDashboardService {
  getStats(): Promise<DashboardStats>
}

export interface ISettingsService {
  get(): Promise<RuntimeSettings>
  update(payload: Omit<RuntimeSettings, 'updatedAt'>): Promise<RuntimeSettings>
  testConnection(payload: {
    provider: string
    model: string
    apiKey: string
    baseUrl: string
    timeoutSeconds: number
    purpose: string
  }): Promise<RuntimeConnectionTestResult>
}
