from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class SourceOut(BaseModel):
    id: str
    title: str
    sourceType: str
    mimeType: str
    filePath: str | None = None
    url: str | None = None
    uploadedAt: str
    updatedAt: str
    createdBy: str
    parseStatus: str
    ingestStatus: str
    metadataJson: dict
    checksum: str
    trustLevel: str
    fileSize: int | None = None
    description: str | None = None
    tags: list[str]
    collectionId: str | None = None


class CollectionOut(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    color: str
    sourceCount: int = 0
    pageCount: int = 0
    createdAt: str
    updatedAt: str


class SourceChunkOut(BaseModel):
    id: str
    sourceId: str
    chunkIndex: int
    sectionTitle: str
    pageNumber: int | None = None
    content: str
    tokenCount: int
    embeddingId: str | None = None
    metadataJson: dict | None = None
    spanStart: int
    spanEnd: int
    createdAt: str


class EntityOut(BaseModel):
    id: str
    name: str
    entityType: str
    description: str
    aliases: list[str]
    normalizedName: str
    createdAt: str


class PageTypeCandidateOut(BaseModel):
    pageType: str
    confidence: float
    reason: str


class TimelineEventOut(BaseModel):
    id: str
    eventDate: str
    sortKey: str
    title: str
    description: str
    precision: str
    entityIds: list[str]
    sourceId: str | None = None
    pageId: str | None = None


class GlossaryTermOut(BaseModel):
    id: str
    term: str
    normalizedTerm: str
    definition: str
    aliases: list[str]
    confidenceScore: float
    sourceId: str | None = None
    pageId: str | None = None


class PageCitationOut(BaseModel):
    id: str
    index: int
    claimId: str
    claimText: str
    sectionKey: str
    citationStyle: str
    sourceId: str
    sourceTitle: str
    chunkId: str
    chunkIndex: int
    chunkSectionTitle: str
    pageNumber: int | None = None
    snippet: str
    chunkSpanStart: int | None = None
    chunkSpanEnd: int | None = None
    sourceSpanStart: int | None = None
    sourceSpanEnd: int | None = None
    confidence: float


class ClaimOut(BaseModel):
    id: str
    text: str
    claimType: str
    confidenceScore: float
    sourceChunkIds: list[str]
    canonicalStatus: str
    reviewStatus: str
    extractedAt: str
    topic: str | None = None
    extractionMethod: str | None = None
    evidenceSpanStart: int | None = None
    evidenceSpanEnd: int | None = None
    metadataJson: dict | None = None


class KnowledgeUnitOut(BaseModel):
    id: str
    sourceId: str
    sourceChunkId: str | None = None
    claimId: str | None = None
    unitType: str
    title: str
    text: str
    status: str
    reviewStatus: str
    canonicalStatus: str
    confidenceScore: float
    topic: str | None = None
    entityIds: list[str]
    evidenceSpanStart: int | None = None
    evidenceSpanEnd: int | None = None
    metadataJson: dict | None = None
    createdAt: str
    updatedAt: str


class ExtractionRunOut(BaseModel):
    id: str
    sourceId: str
    runType: str
    status: str
    method: str
    taskProfile: str
    modelProvider: str
    modelName: str
    promptVersion: str
    inputChunkCount: int
    outputCount: int
    errorMessage: str | None = None
    metadataJson: dict | None = None
    startedAt: str
    finishedAt: str | None = None


class PageOut(BaseModel):
    id: str
    slug: str
    title: str
    pageType: str
    status: str
    summary: str
    contentMd: str
    contentHtml: str | None = None
    currentVersion: int
    lastComposedAt: str
    lastReviewedAt: str | None = None
    publishedAt: str | None = None
    owner: str
    tags: list[str]
    parentPageId: str | None = None
    keyFacts: list[str]
    relatedSourceIds: list[str]
    relatedPageIds: list[str]
    relatedEntityIds: list[str]
    collectionId: str | None = None
    backlinks: list[dict] = []
    citations: list[PageCitationOut] = []
    pageTypeCandidates: list[PageTypeCandidateOut] = []
    timelineEvents: list[TimelineEventOut] = []
    glossaryTerms: list[GlossaryTermOut] = []


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    total: int
    page: int
    pageSize: int
    hasMore: bool
