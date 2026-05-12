from pydantic import BaseModel


class RetrievalDiagnosticsOut(BaseModel):
    candidateType: str | None = None
    candidateId: str | None = None
    sourceId: str | None = None
    pageId: str | None = None
    sourceTitle: str | None = None
    sectionTitle: str | None = None
    excerpt: str | None = None
    lexicalScore: float | None = None
    vectorScore: float | None = None
    titleBonus: float | None = None
    metadataScore: float | None = None
    authorityScore: float | None = None
    rerankScore: float | None = None
    rerankReason: str | None = None
    finalScore: float | None = None
    semanticWeight: float | None = None
    vectorBackend: str | None = None


class AskConflictOut(BaseModel):
    summary: str
    preferredSourceId: str | None = None
    preferredSourceTitle: str | None = None
    preferredReason: str | None = None
    competingSourceId: str | None = None
    competingSourceTitle: str | None = None
    competingReason: str | None = None


class AskInterpretedQueryOut(BaseModel):
    standaloneQuery: str
    intent: str
    answerType: str
    targetEntities: list[str] = []
    filters: dict = {}
    needsClarification: bool = False
    clarificationQuestion: str | None = None
    conversationSummary: str | None = None
    planner: dict | None = None


class AskScopeOut(BaseModel):
    type: str
    id: str
    title: str
    description: str | None = None
    strict: bool = True
    matchedInScope: bool = True


class SuggestedPromptOut(BaseModel):
    text: str
    category: str
    reason: str | None = None


class AskDiagnosticsOut(BaseModel):
    candidateCount: int
    retrievalLimit: int
    searchResultLimit: int
    clarificationTriggered: bool = False
    planning: dict | None = None
    topChunks: list[RetrievalDiagnosticsOut] = []
    topCandidates: list[RetrievalDiagnosticsOut] = []
    selectedContext: list[dict] = []
    contextCoverage: dict = {}
    answerVerification: dict | None = None


class AskRequest(BaseModel):
    question: str
    sessionId: str | None = None
    sourceId: str | None = None
    collectionId: str | None = None
    pageId: str | None = None


class CitationOut(BaseModel):
    id: str
    index: int
    sourceId: str
    sourceTitle: str
    candidateType: str | None = None
    artifactId: str | None = None
    artifactType: str | None = None
    chunkId: str | None = None
    unitId: str | None = None
    sectionKey: str | None = None
    sectionTitle: str | None = None
    snippet: str
    matchedText: str | None = None
    chunkSpanStart: int | None = None
    chunkSpanEnd: int | None = None
    sourceSpanStart: int | None = None
    sourceSpanEnd: int | None = None
    pageId: str | None = None
    pageTitle: str | None = None
    url: str | None = None
    confidence: float
    evidenceGrade: dict | None = None
    citationReason: str | None = None


class RelatedPageOut(BaseModel):
    id: str
    slug: str
    title: str
    pageType: str
    relevanceScore: float
    excerpt: str


class RelatedSourceOut(BaseModel):
    id: str
    title: str
    sourceType: str
    trustLevel: str
    relevanceScore: float


class AskResponseOut(BaseModel):
    id: str
    sessionId: str | None = None
    question: str
    answer: str
    answerType: str | None = None
    interpretedQuery: AskInterpretedQueryOut | None = None
    scope: AskScopeOut | None = None
    suggestedPrompts: list[SuggestedPromptOut] = []
    citations: list[CitationOut]
    relatedPages: list[RelatedPageOut]
    relatedSources: list[RelatedSourceOut]
    confidence: float
    isInference: bool
    uncertainty: str | None = None
    conflicts: list[AskConflictOut] = []
    retrievalDebugId: str | None = None
    diagnostics: AskDiagnosticsOut | None = None
    answeredAt: str


class ChatSessionOut(BaseModel):
    id: str
    title: str
    createdAt: str
    updatedAt: str
    messageCount: int
    lastMessagePreview: str | None = None


class ChatMessageOut(BaseModel):
    id: str
    sessionId: str
    role: str
    content: str
    response: AskResponseOut | None = None
    createdAt: str


class ChatSessionDetailOut(ChatSessionOut):
    messages: list[ChatMessageOut]


class SearchResultOut(BaseModel):
    id: str
    type: str
    title: str
    excerpt: str
    pageId: str | None = None
    pageSlug: str | None = None
    sourceId: str | None = None
    relevanceScore: float
    status: str | None = None
    diagnostics: RetrievalDiagnosticsOut | None = None
