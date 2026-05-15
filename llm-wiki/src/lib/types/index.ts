// Core data models matching the spec

import type {
  SourceStatus, PageStatus, PageType, ClaimType, ReviewIssueType,
  JobStatus, JobType, EntityType, SourceType, TrustLevel,
  RelationType, SeverityLevel, ReviewDecision
} from '@/lib/constants'

export interface AuthUser {
  id: string
  email: string
  name: string
  role: 'admin' | 'reviewer' | 'editor' | 'reader' | string
  departmentId?: string | null
  departmentName?: string | null
  permissions: string[]
  scopeMode: 'all' | 'restricted' | string
  accessibleCollectionIds: string[]
  collectionMemberships: Array<{
    collectionId: string
    role: string
  }>
}

export interface ManagedUser extends AuthUser {
  isActive: boolean
  createdAt?: string | null
  updatedAt?: string | null
}

export interface Department {
  id: string
  name: string
  slug: string
  description: string
  createdAt?: string | null
  updatedAt?: string | null
}

export interface AdminRole {
  id: string
  name: string
  slug: string
  description: string
  permissions: string[]
  isSystem: boolean
}

// === Source ===

export interface Source {
  id: string
  title: string
  sourceType: SourceType
  documentType?: string | null
  mimeType: string
  filePath?: string
  url?: string
  uploadedAt: string
  updatedAt: string
  createdBy: string
  parseStatus: SourceStatus
  ingestStatus: SourceStatus
  metadataJson: Record<string, unknown>
  checksum: string
  trustLevel: TrustLevel
  fileSize?: number
  description?: string
  tags: string[]
  collectionId?: string | null
  sourceStatus?: string | null
  authorityLevel?: string | null
  effectiveDate?: string | null
  version?: string | null
  owner?: string | null
}

export interface SourceSuggestion {
  id: string
  sourceId: string
  suggestionType: 'collection_match' | 'page_match' | 'entity_match' | 'timeline_match' | 'new_page' | string
  targetType: 'collection' | 'page' | 'entity' | 'timeline' | 'standalone' | string
  targetId?: string | null
  targetLabel: string
  status: 'pending' | 'accepted' | 'rejected' | string
  confidenceScore: number
  reason: string
  evidence: Array<Record<string, unknown>>
  createdAt: string
  decidedAt?: string | null
}

export interface Collection {
  id: string
  name: string
  slug: string
  description: string
  color: string
  sourceCount: number
  pageCount: number
  memberCount: number
  createdAt: string
  updatedAt: string
}

export interface SourceChunk {
  id: string
  sourceId: string
  chunkIndex: number
  sectionTitle: string
  pageNumber?: number
  content: string
  tokenCount: number
  embeddingId?: string
  metadataJson?: Record<string, unknown>
  spanStart: number
  spanEnd: number
  createdAt: string
}

export interface SourceArtifact {
  id: string
  sourceId: string
  artifactType: 'ocr' | 'image' | 'table' | 'structure' | 'notebook' | string
  title: string
  status: string
  contentType?: string | null
  summary?: string | null
  previewText?: string | null
  url?: string | null
  pageNumber?: number | null
  metadataJson?: Record<string, unknown> | null
}

export interface NoteAnchor {
  id: string
  noteId: string
  targetType: string
  targetId?: string | null
  sourceId?: string | null
  chunkId?: string | null
  artifactId?: string | null
  pageId?: string | null
  sectionKey?: string | null
  reviewItemId?: string | null
  askMessageId?: string | null
  citationId?: string | null
  snippet: string
  metadataJson?: Record<string, unknown> | null
  createdAt: string
}

export interface Note {
  id: string
  title: string
  body: string
  scope: 'private' | 'collection' | 'workspace' | string
  status: 'active' | 'archived' | string
  ownerId?: string | null
  ownerName: string
  collectionId?: string | null
  tags: string[]
  metadataJson?: Record<string, unknown> | null
  anchors: NoteAnchor[]
  createdAt: string
  updatedAt: string
  archivedAt?: string | null
}

// === Entity & Claim ===

export interface Entity {
  id: string
  name: string
  entityType: EntityType
  description: string
  aliases: string[]
  normalizedName: string
  status?: 'active' | 'archived' | 'merged' | string
  verificationStatus?: 'verified' | 'disputed' | 'unverified' | string
  mergedIntoEntityId?: string | null
  reviewedAt?: string | null
  reviewedBy?: string | null
  sourceIds?: string[]
  pageIds?: string[]
  createdAt: string
}

export interface ExplorerEntity extends Entity {
  sourceCount: number
  pageCount: number
}

export interface EntityDetail extends ExplorerEntity {
  linkedSources: Array<{ id: string; title: string; sourceType: string }>
  linkedPages: Array<{ id: string; slug: string; title: string; status: string }>
  mergeCandidates: Array<{ id: string; name: string; entityType: string; verificationStatus: string }>
}

export interface PageTypeCandidate {
  pageType: PageType
  confidence: number
  reason: string
}

export interface TimelineEvent {
  id: string
  eventDate: string
  sortKey: string
  title: string
  description: string
  precision: 'day' | 'month' | 'quarter' | 'year' | string
  entityIds: string[]
  sourceId?: string
  pageId?: string
}

export interface GlossaryTerm {
  id: string
  term: string
  normalizedTerm: string
  definition: string
  aliases: string[]
  confidenceScore: number
  sourceId?: string
  pageId?: string
}

export interface PageCitation {
  id: string
  index: number
  claimId: string
  claimText: string
  sectionKey: string
  citationStyle: string
  sourceId: string
  sourceTitle: string
  chunkId: string
  chunkIndex: number
  chunkSectionTitle: string
  pageNumber?: number
  snippet: string
  chunkSpanStart?: number
  chunkSpanEnd?: number
  sourceSpanStart?: number
  sourceSpanEnd?: number
  confidence: number
}

export interface Claim {
  id: string
  text: string
  claimType: ClaimType
  confidenceScore: number
  sourceChunkIds: string[]
  canonicalStatus: 'verified' | 'disputed' | 'unverified' | 'deprecated'
  reviewStatus: 'pending' | 'approved' | 'rejected'
  extractedAt: string
  topic?: string
  extractionMethod?: string
  evidenceSpanStart?: number | null
  evidenceSpanEnd?: number | null
  metadataJson?: Record<string, unknown>
}

export interface KnowledgeUnit {
  id: string
  sourceId: string
  sourceChunkId?: string | null
  claimId?: string | null
  unitType: string
  title: string
  text: string
  status: string
  reviewStatus: string
  canonicalStatus: string
  confidenceScore: number
  topic?: string | null
  entityIds: string[]
  evidenceSpanStart?: number | null
  evidenceSpanEnd?: number | null
  metadataJson?: Record<string, unknown>
  createdAt: string
  updatedAt: string
}

export interface ExtractionRun {
  id: string
  sourceId: string
  runType: string
  status: string
  method: string
  taskProfile: string
  modelProvider: string
  modelName: string
  promptVersion: string
  inputChunkCount: number
  outputCount: number
  errorMessage?: string | null
  metadataJson?: Record<string, unknown>
  startedAt: string
  finishedAt?: string | null
}

export interface ClaimRelation {
  id: string
  fromClaimId?: string
  fromEntityId?: string
  toClaimId?: string
  toEntityId?: string
  relationType: string
  confidenceScore: number
}

// === Page ===

export interface Page {
  id: string
  slug: string
  title: string
  pageType: PageType
  status: PageStatus
  summary: string
  contentMd: string
  contentJson?: import('@/lib/page-blocks').PageBlock[]
  contentHtml?: string
  currentVersion: number
  lastComposedAt: string
  lastReviewedAt?: string
  publishedAt?: string
  owner: string
  tags: string[]
  parentPageId?: string
  keyFacts: string[]
  relatedSourceIds: string[]
  relatedPageIds: string[]
  relatedEntityIds: string[]
  collectionId?: string | null
  backlinks?: Array<{ id: string; slug: string; title: string; relationType: string }>
  citations?: PageCitation[]
  pageTypeCandidates?: PageTypeCandidate[]
  timelineEvents?: TimelineEvent[]
  glossaryTerms?: GlossaryTerm[]
}

export interface PageVersion {
  id: string
  pageId: string
  versionNo: number
  contentMd: string
  changeSummary: string
  createdAt: string
  createdByAgentOrUser: string
  reviewStatus: ReviewDecision
}

export interface AuditLog {
  id: string
  action: string
  objectType: string
  objectId: string
  actor: string
  summary: string
  metadataJson: Record<string, unknown>
  createdAt: string
}

export interface PageClaimLink {
  id: string
  pageId: string
  claimId: string
  sectionKey: string
  citationStyle: 'inline' | 'footnote' | 'bibliography'
}

export interface PageLink {
  id: string
  fromPageId: string
  toPageId: string
  relationType: RelationType
  autoGenerated: boolean
}

export interface Diagram {
  id: string
  slug: string
  title: string
  objective: string
  notation: string
  status: 'draft' | 'published' | string
  owner: string
  collectionId?: string | null
  currentVersion: number
  flowDocument: FlowDocument
  sourcePageIds: string[]
  sourceIds: string[]
  actorLanes: string[]
  entryPoints: string[]
  exitPoints: string[]
  relatedDiagramIds: string[]
  relatedDiagrams: Array<{ id: string; slug: string; title: string; status: string }>
  linkedPages: Array<{ id: string; slug: string; title: string; status: string }>
  linkedSources: Array<{ id: string; title: string; sourceType: string; parseStatus: string }>
  createdAt: string
  updatedAt: string
  publishedAt?: string | null
}

export interface DiagramVersion {
  id: string
  diagramId: string
  versionNo: number
  flowDocument: FlowDocument
  changeSummary: string
  createdAt: string
  createdByAgentOrUser: string
}

export interface FlowDocument {
  version: string
  engine?: string
  family: string
  pages: FlowPage[]
  metadata: FlowMetadata
}

export interface FlowPage {
  id: string
  name: string
  lanes?: FlowLane[]
  nodes: FlowNode[]
  edges: FlowEdge[]
  groups?: Array<Record<string, unknown>>
  viewport?: { x?: number; y?: number; zoom?: number }
}

export interface FlowLane {
  id: string
  label: string
  x?: number
  width?: number
}

export interface FlowNode {
  id: string
  type: string
  label: string
  owner?: string
  position?: { x: number; y: number }
  size?: { width?: number; height?: number }
  data?: Record<string, unknown>
}

export interface FlowEdge {
  id: string
  source: string
  target: string
  label?: string
  type?: string
  data?: Record<string, unknown>
}

export interface FlowMetadata {
  title?: string
  objective?: string
  owner?: string
  sourceIds?: string[]
  sourcePageIds?: string[]
  reviewStatus?: string
  scopeSummary?: string
  openQuestions?: string[]
  citations?: Array<Record<string, unknown>>
  validation?: { isValid?: boolean; warnings?: string[] }
  legacySpec?: Record<string, unknown>
  reviewNotes?: Array<Record<string, unknown>>
}

// === Job ===

export interface Job {
  id: string
  jobType: JobType
  status: JobStatus
  startedAt: string
  finishedAt?: string
  inputRef: string
  outputRef?: string
  errorMessage?: string
  logsJson: string[]
  stepsJson?: JobStep[]
  progressPercent?: number
  actor?: string
}

export interface JobStep {
  name: string
  status: string
  progress?: number | null
  details: Record<string, unknown>
  updatedAt?: string | null
}

// === Review ===

export interface ReviewIssue {
  type: ReviewIssueType
  severity: SeverityLevel
  message: string
  evidence: string
  sourceChunkId?: string
  claimId?: string
}

export interface EvidenceSnippet {
  sourceId: string
  sourceTitle: string
  chunkId?: string
  content: string
  relevance: number
}

export interface ReviewDiffLine {
  kind: 'added' | 'removed' | 'modified' | 'unchanged' | string
  oldLineNumber?: number
  newLineNumber?: number
  oldText: string
  newText: string
}

export interface ReviewChangeSet {
  summary: string
  hasContentChanges: boolean
  reviewLevel: 'page' | 'update' | string
  previousVersion?: number
  proposedVersion?: number
  issueCount: number
  stats: {
    addedLines: number
    removedLines: number
    modifiedLines: number
    unchangedLines: number
  }
  diffLines: ReviewDiffLine[]
}

export interface ReviewPageContext {
  id: string
  slug: string
  title: string
  status: PageStatus
  pageType: PageType
  sourceIds: string[]
  sourceCount: number
  relatedPageIds: string[]
  relatedEntityIds: string[]
  backlinks: Array<{ id: string; slug: string; title: string; relationType: string }>
}

export interface ReviewActions {
  canApprove: boolean
  canReject: boolean
  canMerge: boolean
  canRequestRebuild: boolean
  primaryAction: string
  secondaryActions: string[]
  itemId: string
}

export interface ReviewItem {
  id: string
  pageId: string
  pageTitle: string
  pageSlug: string
  pageStatus: PageStatus
  issueType: ReviewIssueType
  severity: SeverityLevel
  issues: ReviewIssue[]
  oldContentMd: string
  newContentMd: string
  changeSummary: string
  confidenceScore: number
  createdAt: string
  updatedAt: string
  assignedTo?: string
  previousVersion?: number
  sourceIds: string[]
  evidenceSnippets: EvidenceSnippet[]
  reviewLevel?: 'page' | 'update' | string
  itemKind?: 'heuristic' | 'generated_update' | string
  suggestions?: Array<{ type: string; title: string; targetId?: string; targetSlug?: string; confidenceScore: number; reason: string }>
  backlinks?: Array<{ id: string; slug: string; title: string; relationType: string }>
  comments?: Array<{ id: string; reviewItemId: string; actor: string; comment: string; createdAt: string }>
  pageContext?: ReviewPageContext
  changeSet?: ReviewChangeSet
  reviewActions?: ReviewActions
  isVirtual?: boolean
}

export interface SkillPackage {
  id: string
  name: string
  version: string
  scope: string
  status: string
  summary: string
  description: string
  capabilities: string[]
  tags: string[]
  entryPoints: string[]
  owner?: string | null
  reviewStatus: string
  instructions?: string
  taskProfile?: string
  latestTest?: SkillTestResult | null
  reviewHistory?: Array<{
    id: string
    type: string
    actor: string
    comment?: string | null
    createdAt: string
  }>
  metadataJson: Record<string, unknown>
}

export interface SkillTestResult {
  id: string
  input: string
  output: string
  taskProfile: string
  provider: string
  model: string
  success: boolean
  actor: string
  createdAt: string
  latencyMs?: number | null
}

// === Dashboard ===

export interface TimeSeriesPoint {
  date: string
  value: number
  label?: string
}

export interface ActivityItem {
  id: string
  type: 'source_uploaded' | 'page_published' | 'page_draft_created' | 'review_completed' | 'job_failed' | 'claim_conflict_detected' | 'source_rebuilt'
  description: string
  entityId?: string
  entityTitle?: string
  timestamp: string
  user?: string
}

export interface DashboardStats {
  totalSources: number
  totalPages: number
  publishedPages: number
  draftPages: number
  inReviewPages: number
  stalePages: number
  unverifiedClaims: number
  reviewQueueCount: number
  lastSyncTime: string
  failedJobsCount: number
  totalChunks: number
  totalEntities: number
  sourceTypeBreakdown: Record<string, number>
  pageStatusBreakdown: Record<string, number>
  pagesPublishedOverTime: TimeSeriesPoint[]
  recentActivity: ActivityItem[]
  failedJobs: Job[]
}

// === Graph ===

export interface GraphNode {
  id: string
  type: 'page' | 'entity'
  label: string
  status?: PageStatus
  pageType?: PageType
  entityType?: EntityType
  description?: string
  url?: string
  sourceIds?: string[]
  collectionId?: string | null
  metrics?: {
    degree: number
    backlinkCount: number
    relatedEntityCount: number
    sourceCount?: number
    citationCount?: number
    hubScore?: number
    clusterId?: number | null
  }
  flags?: {
    orphan: boolean
    stale: boolean
    conflict: boolean
    hub: boolean
    recent: boolean
  }
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  relationType: RelationType
  label?: string
  semanticGroup?: string
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  detailById?: Record<string, {
    id: string
    label: string
    type: 'page' | 'entity'
    status?: PageStatus
    pageType?: PageType
    entityType?: EntityType
    description?: string
    url?: string
    sourceIds: string[]
    collectionId?: string | null
    metrics: {
      degree: number
      backlinkCount: number
      relatedEntityCount: number
      sourceCount?: number
      citationCount?: number
      hubScore?: number
      clusterId?: number | null
    }
    flags?: {
      orphan: boolean
      stale: boolean
      conflict: boolean
      hub: boolean
      recent: boolean
    }
    connections: Array<{
      id: string
      relationType: string
      otherNodeId: string
    }>
  }>
  meta?: {
    nodeCount: number
    edgeCount: number
    localMode: boolean
    focusId?: string
    availableRelationTypes: string[]
    availablePageTypes: string[]
    availableEntityTypes: string[]
    clusters?: {
      count: number
      disconnectedCount: number
    }
    analyticsFilters?: {
      showOrphans: boolean
      showStale: boolean
      showConflicts: boolean
      showHubs: boolean
    }
  }
}

export interface LintIssue {
  id: string
  pageId: string
  pageSlug: string
  pageTitle: string
  pageStatus: PageStatus
  pageType: PageType
  ruleId: string
  severity: SeverityLevel
  title: string
  message: string
  suggestion: string
  metadata: Record<string, unknown>
}

export interface LintSummary {
  issueCount: number
  affectedPages: number
  byRule: Record<string, number>
  bySeverity: Record<string, number>
  rules: Array<{ id: string; label: string }>
}

export interface LintResponse extends PaginatedResponse<LintIssue> {
  summary: LintSummary
}

// === Ask / Query ===

export interface Citation {
  id: string
  index: number
  sourceId: string
  sourceTitle: string
  candidateType?: string | null
  artifactId?: string | null
  artifactType?: string | null
  chunkId?: string
  unitId?: string
  sectionKey?: string
  sectionTitle?: string
  snippet: string
  matchedText?: string
  chunkSpanStart?: number
  chunkSpanEnd?: number
  sourceSpanStart?: number
  sourceSpanEnd?: number
  pageId?: string
  pageTitle?: string
  url?: string
  confidence: number
  evidenceGrade?: {
    relevance?: number
    specificity?: number
    authority?: number
    freshness?: number
    termCoverage?: number
    contradictionRisk?: number
  } | null
  citationReason?: string | null
}

export interface RelatedPage {
  id: string
  slug: string
  title: string
  pageType: PageType
  relevanceScore: number
  excerpt: string
}

export interface RelatedSource {
  id: string
  title: string
  sourceType: SourceType
  trustLevel: TrustLevel
  relevanceScore: number
}

export interface AskInterpretedQuery {
  standaloneQuery: string
  intent: string
  answerType: string
  targetEntities: string[]
  filters: Record<string, unknown>
  needsClarification: boolean
  clarificationQuestion?: string | null
  conversationSummary?: string | null
  answerLanguage?: string | null
  queryVariants?: Array<{
    id: string
    query: string
    language?: string
    type?: string
  }>
  planner?: {
    strategy: string
    rationale?: string | null
    askBackMode?: string | null
    subQueries: Array<{
      id: string
      query: string
      intent: string
      role: string
      reason?: string | null
    }>
  } | null
}

export interface AskConflict {
  summary: string
  preferredSourceId?: string | null
  preferredSourceTitle?: string | null
  preferredReason?: string | null
  competingSourceId?: string | null
  competingSourceTitle?: string | null
  competingReason?: string | null
}

export interface RetrievalDiagnostic {
  candidateType?: string | null
  candidateId?: string | null
  sourceId?: string | null
  pageId?: string | null
  sourceTitle?: string | null
  sectionTitle?: string | null
  excerpt?: string | null
  lexicalScore?: number | null
  vectorScore?: number | null
  titleBonus?: number | null
  metadataScore?: number | null
  authorityScore?: number | null
  rerankScore?: number | null
  rerankReason?: string | null
  finalScore?: number | null
  semanticWeight?: number | null
  vectorBackend?: string | null
}

export interface AskDiagnostics {
  candidateCount: number
  retrievalLimit: number
  searchResultLimit: number
  clarificationTriggered?: boolean
  planning?: {
    strategy: string
    rationale?: string | null
    askBackMode?: string | null
    subQueries: Array<{
      id: string
      query: string
      intent: string
      role: string
      reason?: string | null
    }>
  } | null
  topChunks: RetrievalDiagnostic[]
  topCandidates: RetrievalDiagnostic[]
  selectedContext: Array<Record<string, unknown>>
  contextCoverage: Record<string, unknown>
  answerVerification?: {
    supported: boolean
    coverage: number
    coverageLevel?: 'full' | 'partial' | 'none' | string
    finalDecision?: 'answer' | 'partial_answer' | 'no_answer' | string
    risk?: 'low' | 'medium' | 'high' | string
    answerEvidenceOverlap?: number
    citationCount: number
    missingEvidenceRisk: 'low' | 'medium' | 'high' | string
    unsupportedClaims?: string[]
    missingEvidence?: string[]
    notes: string[]
  } | null
  evidenceGate?: {
    passed: boolean
    status: 'supported' | 'partial' | 'insufficient' | string
    reason: string
    warnings: string[]
    topScore: number
    coverage: number
    selectedCount: number
    candidateCount: number
    citationCount: number
  } | null
  queryVariants?: Array<{
    id: string
    query: string
    language?: string
    type?: string
  }>
  answerGeneration?: {
    mode: 'llm' | 'retrieval_fallback' | string
    provider?: string | null
    model?: string | null
    reason?: string | null
  } | null
}

export interface AskScope {
  type: 'source' | 'page' | 'collection' | string
  id: string
  title: string
  description?: string | null
  strict?: boolean
  matchedInScope?: boolean
}

export interface SuggestedPrompt {
  text: string
  category: string
  reason?: string | null
}

export interface AskResponse {
  id: string
  sessionId?: string | null
  question: string
  answer: string
  answerType?: string | null
  interpretedQuery?: AskInterpretedQuery | null
  scope?: AskScope | null
  suggestedPrompts?: SuggestedPrompt[]
  citations: Citation[]
  relatedPages: RelatedPage[]
  relatedSources: RelatedSource[]
  answerMode?: 'answer' | 'partial_answer' | 'no_answer' | 'general_fallback' | string
  answerLanguage?: string | null
  sourceLanguages?: string[]
  evidenceStatus?: 'supported' | 'partial' | 'insufficient' | 'unsupported' | string
  evidenceGate?: {
    passed: boolean
    status: 'supported' | 'partial' | 'insufficient' | string
    reason: string
    warnings: string[]
    topScore: number
    coverage: number
    selectedCount: number
    candidateCount: number
    citationCount: number
  } | null
  confidence: number
  isInference: boolean
  uncertainty?: string | null
  conflicts?: AskConflict[]
  retrievalDebugId?: string | null
  diagnostics?: AskDiagnostics | null
  answeredAt: string
}

export interface ChatSession {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  messageCount: number
  lastMessagePreview?: string | null
}

export interface ChatMessage {
  id: string
  sessionId: string
  role: 'user' | 'assistant' | string
  content: string
  response?: AskResponse | null
  createdAt: string
}

export interface ChatSessionDetail extends ChatSession {
  messages: ChatMessage[]
}

export interface SearchResult {
  id: string
  type: 'page' | 'chunk' | 'claim'
  title: string
  excerpt: string
  pageId?: string
  pageSlug?: string
  sourceId?: string
  relevanceScore: number
  status?: PageStatus
}

export interface RuntimeSettings {
  answerProvider: string
  answerModel: string
  answerApiKey: string
  answerBaseUrl: string
  answerTimeoutSeconds: number
  ingestProvider: string
  ingestModel: string
  ingestApiKey: string
  ingestBaseUrl: string
  ingestTimeoutSeconds: number
  embeddingProvider: string
  embeddingModel: string
  embeddingApiKey: string
  embeddingBaseUrl: string
  aiTaskProfiles: AITaskProfiles
  chunkMode: 'structured' | 'window'
  chunkSizeWords: number
  chunkOverlapWords: number
  retrievalLimit: number
  hybridSemanticWeight: number
  searchResultLimit: number
  graphNodeLimit: number
  lintPageLimit: number
  autoReviewThreshold: number
  askPolicy: {
    minimumTopScore: number
    minimumTermCoverage: number
    allowPartialAnswers: boolean
    allowGeneralFallback: boolean
    crossLingualRewriteEnabled: boolean
  }
  updatedAt: string
}

export interface RuntimeConnectionTestResult {
  success: boolean
  provider: string
  model: string
  purpose: string
  message: string
  latencyMs?: number
}

export interface RuntimeModelListResult {
  success: boolean
  provider: string
  models: string[]
  message: string
  latencyMs?: number
}

export type AITaskKey =
  | 'ingest_summary'
  | 'claim_extraction'
  | 'entity_glossary_timeline'
  | 'bpm_generation'
  | 'ask_answer'
  | 'review_assist'
  | 'embeddings'

export interface AIModelProfile {
  provider: string
  model: string
  apiKey: string
  hasApiKey?: boolean
  baseUrl: string
  timeoutSeconds: number
}

export interface AITaskProfiles {
  ingest_summary: AIModelProfile
  claim_extraction: AIModelProfile
  entity_glossary_timeline: AIModelProfile
  bpm_generation: AIModelProfile
  ask_answer: AIModelProfile
  review_assist: AIModelProfile
  embeddings: AIModelProfile
}

// === API Wrappers ===

export interface ApiResponse<T> {
  data: T
  success: boolean
  message?: string
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  pageSize: number
  hasMore: boolean
}
