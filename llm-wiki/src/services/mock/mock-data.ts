import type {
  Source, SourceChunk, Page, PageVersion, Entity, Claim,
  ReviewItem, Job, DashboardStats, GraphData, AskResponse,
  ActivityItem, TimeSeriesPoint, SearchResult
} from '@/lib/types'
import type { SourceStatus, PageStatus, PageType, ClaimType, ReviewIssueType, SeverityLevel, EntityType, SourceType, TrustLevel } from '@/lib/constants'

// =============================================================================
// MOCK DATA — All entities for the LLM Wiki Knowledge Base
// =============================================================================

// --- SOURCES ---

export const MOCK_SOURCES: Source[] = [
  {
    id: 'src-001',
    title: 'AI Policy & Governance Guidelines v2.1',
    sourceType: 'pdf',
    mimeType: 'application/pdf',
    filePath: '/sources/ai-policy-governance-v2.1.pdf',
    uploadedAt: '2025-01-15T10:30:00Z',
    updatedAt: '2025-01-15T10:30:00Z',
    createdBy: 'Alice Chen',
    parseStatus: 'indexed',
    ingestStatus: 'indexed',
    metadataJson: { pageCount: 47, version: '2.1', department: 'Compliance' },
    checksum: 'a3f2b8c1d9e4f6a7b8c9d0e1f2a3b4c5',
    trustLevel: 'authoritative',
    fileSize: 2458624,
    description: 'Official AI governance policy covering ethical use, safety standards, and compliance requirements for all AI systems deployed within the organization.',
    tags: ['policy', 'governance', 'compliance', 'ethics', 'AI'],
  },
  {
    id: 'src-002',
    title: 'Technical Standards for LLM Systems v1.0',
    sourceType: 'pdf',
    mimeType: 'application/pdf',
    filePath: '/sources/llm-technical-standards-v1.0.pdf',
    uploadedAt: '2025-01-20T14:15:00Z',
    updatedAt: '2025-02-05T09:00:00Z',
    createdBy: 'Bob Martinez',
    parseStatus: 'indexed',
    ingestStatus: 'indexed',
    metadataJson: { pageCount: 89, version: '1.0', department: 'Engineering' },
    checksum: 'b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9',
    trustLevel: 'authoritative',
    fileSize: 4102912,
    description: 'Comprehensive technical standards document defining requirements for Large Language Model integration, including API design, evaluation metrics, and deployment guidelines.',
    tags: ['technical', 'LLM', 'standards', 'engineering', 'API'],
  },
  {
    id: 'src-003',
    title: 'Internal SOP: Document Processing Workflow',
    sourceType: 'markdown',
    mimeType: 'text/markdown',
    filePath: '/sources/sop-document-processing.md',
    uploadedAt: '2025-02-01T08:00:00Z',
    updatedAt: '2025-02-10T16:30:00Z',
    createdBy: 'Carol Nguyen',
    parseStatus: 'indexed',
    ingestStatus: 'indexed',
    metadataJson: { version: '1.2', department: 'Operations', reviewCycle: 'quarterly' },
    checksum: 'c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0',
    trustLevel: 'high',
    fileSize: 98560,
    description: 'Standard Operating Procedure detailing the end-to-end document processing pipeline from ingestion through knowledge extraction.',
    tags: ['SOP', 'operations', 'workflow', 'document-processing'],
  },
  {
    id: 'src-004',
    title: 'API Reference & Integration Guide',
    sourceType: 'markdown',
    mimeType: 'text/markdown',
    filePath: '/sources/api-integration-guide.md',
    uploadedAt: '2025-02-12T11:45:00Z',
    updatedAt: '2025-02-12T11:45:00Z',
    createdBy: 'David Park',
    parseStatus: 'indexed',
    ingestStatus: 'indexed',
    metadataJson: { version: '2.3', apiVersion: 'v2', endpoints: 42 },
    checksum: 'd6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1',
    trustLevel: 'high',
    fileSize: 187392,
    description: 'Developer guide for integrating with the LLM Wiki platform via REST API, including authentication, rate limiting, and code examples.',
    tags: ['API', 'integration', 'developer', 'reference', 'REST'],
  },
  {
    id: 'src-005',
    title: 'Q1 2025 Knowledge Base Update',
    sourceType: 'markdown',
    mimeType: 'text/markdown',
    filePath: '/sources/q1-2025-kb-update.md',
    uploadedAt: '2025-03-01T09:00:00Z',
    updatedAt: '2025-03-01T09:00:00Z',
    createdBy: 'Emma Wilson',
    parseStatus: 'indexed',
    ingestStatus: 'indexed',
    metadataJson: { quarter: 'Q1-2025', topics: ['RAG', 'safety', 'evaluation'] },
    checksum: 'e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2',
    trustLevel: 'high',
    fileSize: 134528,
    description: 'Quarterly knowledge base update covering new RAG architecture patterns, safety evaluation frameworks, and system performance benchmarks.',
    tags: ['quarterly', 'update', 'RAG', 'safety', 'evaluation'],
  },
]

// --- CHUNKS ---

export const MOCK_CHUNKS: SourceChunk[] = [
  {
    id: 'chunk-001',
    sourceId: 'src-001',
    chunkIndex: 0,
    sectionTitle: '1. Introduction and Scope',
    pageNumber: 1,
    content: `This document establishes the official AI Policy and Governance Guidelines for our organization. These guidelines apply to all AI systems including Large Language Models (LLMs), retrieval-augmented generation systems, and automated decision-making tools.\n\nThe scope encompasses all AI deployments that process, generate, or assist with organizational knowledge work. All teams developing or deploying AI systems must comply with these guidelines effective January 2025.`,
    tokenCount: 148,
    embeddingId: 'emb-001',
    spanStart: 0,
    spanEnd: 412,
    createdAt: '2025-01-15T10:45:00Z',
  },
  {
    id: 'chunk-002',
    sourceId: 'src-001',
    chunkIndex: 1,
    sectionTitle: '2. Ethical AI Principles',
    pageNumber: 3,
    content: `Our ethical AI principles are built on four pillars:\n\n1. Transparency — All AI-generated content must be identifiable as AI-generated when shared externally.\n2. Accountability — Every AI decision that materially affects users must have a clear human accountable owner.\n3. Fairness — AI systems must not perpetuate discriminatory patterns present in training data.\n4. Privacy — Personal data processed by AI must never be used beyond its stated purpose.`,
    tokenCount: 112,
    embeddingId: 'emb-002',
    spanStart: 1200,
    spanEnd: 1850,
    createdAt: '2025-01-15T10:46:00Z',
  },
  {
    id: 'chunk-003',
    sourceId: 'src-001',
    chunkIndex: 2,
    sectionTitle: '3. Safety Standards for LLM Deployment',
    pageNumber: 8,
    content: `Before any LLM is deployed to production, it must pass the Safety Evaluation Framework. This includes:\n\n- Bias assessment with minimum 85% fairness score across protected attributes\n- Content filtering validation for harmful outputs\n- Citation accuracy rate exceeding 90% for grounded answers\n- PII detection rate above 95% for redaction requirements\n- Red team penetration testing by an independent security team\n\nAll safety reports must be archived in the compliance management system.`,
    tokenCount: 134,
    embeddingId: 'emb-003',
    spanStart: 2400,
    spanEnd: 3100,
    createdAt: '2025-01-15T10:47:00Z',
  },
  {
    id: 'chunk-004',
    sourceId: 'src-002',
    chunkIndex: 0,
    sectionTitle: 'Chapter 1: LLM Integration Architecture',
    pageNumber: 1,
    content: `LLM systems must be integrated using a layered architecture separating concerns between interface, logic, and data layers.\n\nThe interface layer handles user requests, session management, and response streaming. The logic layer contains prompt engineering, retrieval orchestration, and response validation. The data layer manages vector stores, knowledge graphs, and source document repositories.\n\nAll integrations must expose a standardized API conforming to OpenAPI 3.1 specification with JSON Schema validation on all request/response payloads.`,
    tokenCount: 156,
    embeddingId: 'emb-004',
    spanStart: 0,
    spanEnd: 890,
    createdAt: '2025-01-20T14:30:00Z',
  },
  {
    id: 'chunk-005',
    sourceId: 'src-002',
    chunkIndex: 1,
    sectionTitle: 'Chapter 2: Evaluation Metrics',
    pageNumber: 12,
    content: `The standard evaluation metrics for production LLM systems are defined as follows:\n\n- ROUGE-L score minimum 0.42 for summarization tasks\n- BLEU score minimum 0.31 for translation tasks\n- Citation accuracy: percentage of claims with valid source reference\n- Hallucination rate: percentage of responses containing unsupported facts\n- Response latency: 95th percentile under 2.5 seconds for standard queries\n- Chunk retrieval precision@5: minimum 0.87`,
    tokenCount: 98,
    embeddingId: 'emb-005',
    spanStart: 3800,
    spanEnd: 4200,
    createdAt: '2025-01-20T14:31:00Z',
  },
  {
    id: 'chunk-006',
    sourceId: 'src-002',
    chunkIndex: 2,
    sectionTitle: 'Chapter 3: RAG Architecture Standards',
    pageNumber: 24,
    content: `Retrieval-Augmented Generation (RAG) systems must implement the following architectural patterns:\n\n1. Hybrid retrieval combining dense vector search with sparse BM25 for improved recall\n2. Cross-encoder re-ranking with minimum top-20 candidate reranking\n3. Context window utilization target of 85% maximum to balance relevance and noise\n4. Citation attribution at the chunk level, not document level\n5. Fallback strategy: if no chunks exceed 0.72 relevance threshold, return "I don't know"\n\nThe maximum retrieval corpus size is 10 million documents per deployment. For larger corpora, clustering and selective indexing must be implemented.`,
    tokenCount: 182,
    embeddingId: 'emb-006',
    spanStart: 7200,
    spanEnd: 8100,
    createdAt: '2025-01-20T14:32:00Z',
  },
  {
    id: 'chunk-007',
    sourceId: 'src-003',
    chunkIndex: 0,
    sectionTitle: '1. Document Ingestion Pipeline',
    pageNumber: 1,
    content: `The document processing workflow follows these stages:\n\nStage 1 — Ingestion: Raw documents are uploaded and validated for file format support (PDF, Markdown, DOCX, TXT). Files exceeding 50MB are rejected with an error notification.\n\nStage 2 — Parsing: Documents are parsed using PyMuPDF for PDFs or unified markdown parsing for text formats. Page numbers, headings, and tables are extracted as metadata.\n\nStage 3 — Chunking: Documents are split into semantic chunks using heading-based boundaries combined with a 512-token sliding window with 64-token overlap. Chunk boundaries must not split code blocks or table rows.\n\nStage 4 — Embedding: Each chunk is embedded using the organization's standard embedding model (currently text-embedding-3-small, 1536 dimensions). Embeddings are stored in the vector database with source metadata tags.`,
    tokenCount: 210,
    embeddingId: 'emb-007',
    spanStart: 0,
    spanEnd: 1450,
    createdAt: '2025-02-01T08:15:00Z',
  },
  {
    id: 'chunk-008',
    sourceId: 'src-003',
    chunkIndex: 1,
    sectionTitle: '2. Quality Assurance Checkpoints',
    pageNumber: 5,
    content: `After document processing, automated QA checks are performed:\n\n- Chunk completeness: no chunk under 50 tokens (excluding headings)\n- Semantic coherence: adjacent chunks must share at least one entity reference\n- Citation extraction: all factual claims must be linked to source chunks\n- Duplication detection: chunks above 95% similarity are flagged for review\n\nAny chunks failing QA are routed to the manual review queue. Manual review must be completed within 48 hours to maintain processing SLA.`,
    tokenCount: 125,
    embeddingId: 'emb-008',
    spanStart: 1600,
    spanEnd: 2150,
    createdAt: '2025-02-01T08:16:00Z',
  },
  {
    id: 'chunk-009',
    sourceId: 'src-004',
    chunkIndex: 0,
    sectionTitle: 'Authentication & Authorization',
    pageNumber: 1,
    content: `All API requests must include a valid Bearer token obtained from the authentication endpoint. Tokens expire after 3600 seconds and must be refreshed using the refresh token endpoint.\n\nAuthorization is role-based:\n- viewer: Read-only access to published pages and sources\n- editor: Can create and edit drafts, submit for review\n- reviewer: Can approve/reject content, trigger rebuilds\n- admin: Full access including user management and system configuration\n\nAPI rate limits are enforced per token: 100 requests/minute for viewer, 500 for editor/reviewer, unlimited for admin.`,
    tokenCount: 138,
    embeddingId: 'emb-009',
    spanStart: 0,
    spanEnd: 720,
    createdAt: '2025-02-12T12:00:00Z',
  },
  {
    id: 'chunk-010',
    sourceId: 'src-005',
    chunkIndex: 0,
    sectionTitle: 'Q1 2025 RAG Architecture Updates',
    pageNumber: 1,
    content: `New RAG patterns introduced in Q1 2025:\n\n1. Parent Document Retrieval: Instead of returning top-k chunks directly, we now retrieve parent documents and re-chunk at query time using the question context as the chunking signal. This reduces citation fragmentation by 34%.\n\n2. Hypothetical Document Embeddings (HyDE): For complex queries, we first generate a hypothetical answer, embed it, and use that embedding for retrieval. This approach improves recall on multi-hop questions by 28%.\n\n3. Structured Knowledge Injection: Entity relationships from the knowledge graph are injected into the context alongside chunk retrieval. This improves consistency on multi-entity queries.`,
    tokenCount: 195,
    embeddingId: 'emb-010',
    spanStart: 0,
    spanEnd: 1100,
    createdAt: '2025-03-01T09:15:00Z',
  },
]

// --- ENTITIES ---

export const MOCK_ENTITIES: Entity[] = [
  {
    id: 'ent-001',
    name: 'Retrieval-Augmented Generation',
    entityType: 'concept',
    description: 'A technique that enhances LLM responses by retrieving relevant knowledge from external sources before generating an answer.',
    aliases: ['RAG', 'retrieval-augmented generation', 'grounded generation'],
    normalizedName: 'retrieval-augmented generation',
    createdAt: '2025-01-20T14:00:00Z',
  },
  {
    id: 'ent-002',
    name: 'Knowledge Graph',
    entityType: 'concept',
    description: 'A structured representation of entities and their relationships, used to enhance retrieval and provide relational context.',
    aliases: ['KG', 'knowledge base graph', 'entity graph'],
    normalizedName: 'knowledge graph',
    createdAt: '2025-01-20T14:05:00Z',
  },
  {
    id: 'ent-003',
    name: 'LLM Integration Standards',
    entityType: 'process',
    description: 'The comprehensive set of technical standards governing how LLMs are integrated into organizational systems.',
    aliases: ['LLM standards', 'integration standards'],
    normalizedName: 'llm integration standards',
    createdAt: '2025-01-20T15:00:00Z',
  },
  {
    id: 'ent-004',
    name: 'Safety Evaluation Framework',
    entityType: 'process',
    description: 'A systematic approach to evaluating AI safety across dimensions including bias, hallucination rate, and PII detection.',
    aliases: ['safety framework', 'SEF', 'AI safety evaluation'],
    normalizedName: 'safety evaluation framework',
    createdAt: '2025-01-15T11:00:00Z',
  },
  {
    id: 'ent-005',
    name: 'Embedding Model',
    entityType: 'technology',
    description: 'Machine learning models that convert text into vector representations for semantic search and similarity computation.',
    aliases: ['text embedding', 'embedding', 'vectorization model'],
    normalizedName: 'embedding model',
    createdAt: '2025-02-01T09:00:00Z',
  },
  {
    id: 'ent-006',
    name: 'Vector Database',
    entityType: 'technology',
    description: 'Database systems optimized for storing and searching high-dimensional vector embeddings at scale.',
    aliases: ['vector store', 'embedding store', 'vector search engine'],
    normalizedName: 'vector database',
    createdAt: '2025-02-01T09:30:00Z',
  },
  {
    id: 'ent-007',
    name: 'Claude AI',
    entityType: 'technology',
    description: 'Anthropic\'s large language model family, known for constitutional AI training and strong reasoning capabilities.',
    aliases: ['Claude', 'Claude model'],
    normalizedName: 'claude ai',
    createdAt: '2025-01-10T10:00:00Z',
  },
  {
    id: 'ent-008',
    name: 'TensorFlow',
    entityType: 'technology',
    description: 'Open-source machine learning framework developed by Google, widely used for model training and deployment.',
    aliases: ['TF'],
    normalizedName: 'tensorflow',
    createdAt: '2025-01-10T10:30:00Z',
  },
  {
    id: 'ent-009',
    name: 'Chunking Strategy',
    entityType: 'concept',
    description: 'Methods for splitting documents into semantically coherent segments for embedding and retrieval.',
    aliases: ['document chunking', 'text splitting', 'context window management'],
    normalizedName: 'chunking strategy',
    createdAt: '2025-02-01T10:00:00Z',
  },
  {
    id: 'ent-010',
    name: 'Prompt Engineering',
    entityType: 'concept',
    description: 'The practice of designing and optimizing prompts to achieve desired model outputs reliably.',
    aliases: ['prompt design', 'prompt optimization'],
    normalizedName: 'prompt engineering',
    createdAt: '2025-02-12T10:00:00Z',
  },
  {
    id: 'ent-011',
    name: 'AI Governance',
    entityType: 'concept',
    description: 'The system of rules, practices, and processes ensuring responsible and compliant AI deployment.',
    aliases: ['AI policy', 'governance framework'],
    normalizedName: 'ai governance',
    createdAt: '2025-01-15T10:00:00Z',
  },
  {
    id: 'ent-012',
    name: 'Hybrid Retrieval',
    entityType: 'concept',
    description: 'Combining multiple retrieval methods (dense vector + sparse keyword) for improved recall and precision.',
    aliases: ['hybrid search', 'dense-sparse retrieval'],
    normalizedName: 'hybrid retrieval',
    createdAt: '2025-03-01T09:30:00Z',
  },
]

// --- CLAIMS ---

export const MOCK_CLAIMS: Claim[] = [
  {
    id: 'clm-001',
    text: 'All LLM deployments must pass the Safety Evaluation Framework before production use.',
    claimType: 'rule',
    confidenceScore: 95,
    sourceChunkIds: ['chunk-003'],
    canonicalStatus: 'verified',
    reviewStatus: 'approved',
    extractedAt: '2025-01-15T11:00:00Z',
    topic: 'safety',
  },
  {
    id: 'clm-002',
    text: 'The Safety Evaluation Framework requires a minimum 85% fairness score across protected attributes.',
    claimType: 'fact',
    confidenceScore: 98,
    sourceChunkIds: ['chunk-003'],
    canonicalStatus: 'verified',
    reviewStatus: 'approved',
    extractedAt: '2025-01-15T11:05:00Z',
    topic: 'safety',
  },
  {
    id: 'clm-003',
    text: 'Citation accuracy rate must exceed 90% for grounded answers in production LLM systems.',
    claimType: 'fact',
    confidenceScore: 92,
    sourceChunkIds: ['chunk-003'],
    canonicalStatus: 'verified',
    reviewStatus: 'approved',
    extractedAt: '2025-01-15T11:10:00Z',
    topic: 'evaluation',
  },
  {
    id: 'clm-004',
    text: 'RAG systems must implement hybrid retrieval combining dense vector search with BM25.',
    claimType: 'rule',
    confidenceScore: 88,
    sourceChunkIds: ['chunk-006'],
    canonicalStatus: 'verified',
    reviewStatus: 'approved',
    extractedAt: '2025-01-20T15:00:00Z',
    topic: 'RAG',
  },
  {
    id: 'clm-005',
    text: 'Chunk retrieval precision@5 must be minimum 0.87 for production systems.',
    claimType: 'fact',
    confidenceScore: 85,
    sourceChunkIds: ['chunk-005'],
    canonicalStatus: 'verified',
    reviewStatus: 'pending',
    extractedAt: '2025-01-20T15:15:00Z',
    topic: 'evaluation',
  },
  {
    id: 'clm-006',
    text: 'Parent Document Retrieval reduces citation fragmentation by 34% compared to chunk-level retrieval.',
    claimType: 'fact',
    confidenceScore: 78,
    sourceChunkIds: ['chunk-010'],
    canonicalStatus: 'unverified',
    reviewStatus: 'pending',
    extractedAt: '2025-03-01T09:30:00Z',
    topic: 'RAG',
  },
  {
    id: 'clm-007',
    text: 'HyDE approach improves recall on multi-hop questions by 28%.',
    claimType: 'fact',
    confidenceScore: 72,
    sourceChunkIds: ['chunk-010'],
    canonicalStatus: 'unverified',
    reviewStatus: 'pending',
    extractedAt: '2025-03-01T09:35:00Z',
    topic: 'retrieval',
  },
  {
    id: 'clm-008',
    text: 'Documents exceeding 50MB must be rejected during ingestion stage.',
    claimType: 'rule',
    confidenceScore: 94,
    sourceChunkIds: ['chunk-007'],
    canonicalStatus: 'verified',
    reviewStatus: 'approved',
    extractedAt: '2025-02-01T08:30:00Z',
    topic: 'workflow',
  },
  {
    id: 'clm-009',
    text: 'Embedding model currently in use produces 1536-dimensional vectors.',
    claimType: 'fact',
    confidenceScore: 96,
    sourceChunkIds: ['chunk-007'],
    canonicalStatus: 'verified',
    reviewStatus: 'approved',
    extractedAt: '2025-02-01T08:35:00Z',
    topic: 'embedding',
  },
  {
    id: 'clm-010',
    text: 'Hybrid retrieval must use cross-encoder reranking with minimum top-20 candidates.',
    claimType: 'rule',
    confidenceScore: 87,
    sourceChunkIds: ['chunk-006'],
    canonicalStatus: 'disputed',
    reviewStatus: 'pending',
    extractedAt: '2025-01-20T15:20:00Z',
    topic: 'RAG',
  },
  {
    id: 'clm-011',
    text: 'If no chunks exceed 0.72 relevance threshold, RAG system must return "I don\'t know".',
    claimType: 'rule',
    confidenceScore: 91,
    sourceChunkIds: ['chunk-006'],
    canonicalStatus: 'verified',
    reviewStatus: 'approved',
    extractedAt: '2025-01-20T15:25:00Z',
    topic: 'RAG',
  },
  {
    id: 'clm-012',
    text: 'Manual review of failed QA chunks must be completed within 48 hours to maintain SLA.',
    claimType: 'rule',
    confidenceScore: 89,
    sourceChunkIds: ['chunk-008'],
    canonicalStatus: 'verified',
    reviewStatus: 'approved',
    extractedAt: '2025-02-01T08:45:00Z',
    topic: 'workflow',
  },
  {
    id: 'clm-013',
    text: 'Maximum retrieval corpus size is 10 million documents per deployment.',
    claimType: 'rule',
    confidenceScore: 90,
    sourceChunkIds: ['chunk-006'],
    canonicalStatus: 'verified',
    reviewStatus: 'approved',
    extractedAt: '2025-01-20T15:30:00Z',
    topic: 'scaling',
  },
  {
    id: 'clm-014',
    text: 'Chunk completeness requires no chunk under 50 tokens excluding headings.',
    claimType: 'rule',
    confidenceScore: 93,
    sourceChunkIds: ['chunk-008'],
    canonicalStatus: 'verified',
    reviewStatus: 'approved',
    extractedAt: '2025-02-01T08:50:00Z',
    topic: 'quality',
  },
  {
    id: 'clm-015',
    text: 'Adjacent chunks must share at least one entity reference for semantic coherence.',
    claimType: 'rule',
    confidenceScore: 86,
    sourceChunkIds: ['chunk-008'],
    canonicalStatus: 'unverified',
    reviewStatus: 'pending',
    extractedAt: '2025-02-01T08:55:00Z',
    topic: 'quality',
  },
]

// --- PAGES ---

export const MOCK_PAGES: Page[] = [
  {
    id: 'page-001',
    slug: 'ai-governance-overview',
    title: 'AI Governance Overview',
    pageType: 'summary',
    status: 'published',
    summary: 'A comprehensive summary of the AI Policy and Governance Guidelines covering ethical principles, safety standards, and compliance requirements for all organizational AI deployments.',
    contentMd: `# AI Governance Overview

## Summary

This page provides a comprehensive overview of the AI Governance framework adopted by our organization. The governance framework is designed to ensure that all AI systems deployed within the organization operate ethically, safely, and in compliance with regulatory requirements.

## Ethical AI Principles

Our ethical AI framework is built on four foundational pillars:

### 1. Transparency
All AI-generated content must be clearly identifiable as AI-generated when shared externally. This includes:
- Required disclosure in external communications
- Watermarking in AI-assisted document generation
- Audit trail for AI-influenced decisions

### 2. Accountability
Every AI decision that materially affects users must have a clear human accountable owner. This means:
- Named individuals responsible for each AI system
- Escalation paths for AI-related incidents
- Regular review meetings with accountable owners

### 3. Fairness
AI systems must not perpetuate discriminatory patterns present in training data. The minimum fairness score across protected attributes is **85%**.

### 4. Privacy
Personal data processed by AI must never be used beyond its stated purpose. Data minimization principles apply to all AI data processing pipelines.

## Safety Standards

Before any LLM is deployed to production, it must pass the Safety Evaluation Framework. Key requirements include:

- **Bias assessment**: Minimum 85% fairness score across protected attributes
- **Content filtering**: Validation for harmful outputs before deployment
- **Citation accuracy**: Exceeding 90% for grounded answers
- **PII detection**: Above 95% for redaction requirements
- **Red team testing**: Independent penetration testing required

## Compliance Scope

The governance framework applies to:
- Large Language Models (LLMs)
- Retrieval-augmented generation systems
- Automated decision-making tools
- AI-assisted knowledge management systems

All teams developing or deploying AI systems must comply with these guidelines effective January 2025.

## Related Documents

- [Technical Standards for LLM Systems v1.0](/sources/src-002)
- [Safety Evaluation Framework](/pages/safety-evaluation-framework)
- [Compliance Audit Process](/pages/compliance-audit-process)
`,
    currentVersion: 3,
    lastComposedAt: '2025-02-20T14:30:00Z',
    lastReviewedAt: '2025-02-20T16:00:00Z',
    publishedAt: '2025-02-20T16:00:00Z',
    owner: 'Alice Chen',
    tags: ['governance', 'ethics', 'policy', 'AI', 'compliance'],
    keyFacts: [
      'Four pillars: Transparency, Accountability, Fairness, Privacy',
      'Minimum 85% fairness score required',
      'Citation accuracy must exceed 90%',
      'PII detection rate must exceed 95%',
      'Red team testing required before production deployment',
    ],
    relatedSourceIds: ['src-001'],
    relatedPageIds: ['page-009', 'page-012'],
    relatedEntityIds: ['ent-004', 'ent-011'],
  },
  {
    id: 'page-002',
    slug: 'data-privacy-compliance',
    title: 'Data Privacy Compliance',
    pageType: 'deep_dive',
    status: 'published',
    summary: 'Deep dive into data privacy requirements for AI systems, covering GDPR compliance, PII handling, data minimization, and retention policies.',
    contentMd: `# Data Privacy Compliance

## Introduction

This page details the data privacy compliance requirements for all AI systems within the organization. These requirements are derived from GDPR, CCPA, and internal privacy standards.

## Core Requirements

### Data Minimization

AI systems must only process data that is strictly necessary for their stated purpose. This principle is enforced through:
- Pre-deployment privacy impact assessments
- Data access audit logs
- Quarterly data inventory reviews

### PII Handling

Personal Identifiable Information (PII) must be handled according to the following rules:

1. **Detection**: AI systems must have PII detection rates above 95%
2. **Redaction**: PII must be automatically redacted before inclusion in training or retrieval corpora
3. **Logging**: All PII access must be logged with timestamp, user, and purpose
4. **Retention**: PII must be deleted from AI systems within 90 days of its original purpose completion

### Consent Management

- All data used for AI training must have documented consent
- Users must be able to opt out of their data being used for AI improvement
- Consent records must be maintained for minimum 7 years

## Compliance Checkpoints

Quarterly compliance reviews verify:
- PII detection rates meet the 95% threshold
- No unauthorized data retention beyond 90 days
- All AI systems have current privacy impact assessments
- Consent records are properly maintained

## Penalties for Non-Compliance

Violations may result in:
- System suspension until compliance is restored
- Mandatory retraining for responsible teams
- Escalation to the compliance review board
`,
    currentVersion: 2,
    lastComposedAt: '2025-02-15T11:00:00Z',
    lastReviewedAt: '2025-02-16T09:00:00Z',
    publishedAt: '2025-02-16T09:00:00Z',
    owner: 'Carol Nguyen',
    tags: ['privacy', 'GDPR', 'compliance', 'PII', 'data-protection'],
    keyFacts: [
      'PII detection rate threshold: 95%',
      'Data retention limit: 90 days',
      'Consent records: 7-year minimum retention',
      'Quarterly compliance reviews required',
    ],
    relatedSourceIds: ['src-001'],
    relatedPageIds: ['page-001', 'page-012'],
    relatedEntityIds: ['ent-011'],
  },
  {
    id: 'page-003',
    slug: 'llm-integration-standards',
    title: 'LLM Integration Standards',
    pageType: 'overview',
    status: 'published',
    summary: 'Overview of the technical standards for integrating LLM systems, covering architecture layers, API design, and evaluation metrics.',
    contentMd: `# LLM Integration Standards

## Overview

The LLM Integration Standards define the technical requirements for integrating Large Language Models into organizational systems. These standards ensure consistency, quality, and maintainability across all AI deployments.

## Architecture

LLM systems must be integrated using a layered architecture:

### Interface Layer
Handles user requests, session management, and response streaming. All interfaces must implement:
- Request validation
- Rate limiting
- Session timeout handling

### Logic Layer
Contains prompt engineering, retrieval orchestration, and response validation. Required components:
- Prompt template library
- Retrieval pipeline
- Output validation

### Data Layer
Manages vector stores, knowledge graphs, and source document repositories. Requirements:
- Backup and recovery procedures
- Data consistency checks
- Access control

## API Standards

All integrations must:
- Conform to OpenAPI 3.1 specification
- Use JSON Schema validation on all payloads
- Implement standard error response format
- Support async processing for long-running operations

## Evaluation Metrics

Production LLM systems must meet these minimum metrics:

| Metric | Minimum Value |
|--------|--------------|
| ROUGE-L (summarization) | 0.42 |
| BLEU (translation) | 0.31 |
| Citation accuracy | 90% |
| Hallucination rate | <5% |
| Response latency (p95) | 2.5s |
| Chunk retrieval precision@5 | 0.87 |

## Quality Gates

All LLM integrations must pass quality gates before production:
1. Unit tests covering core logic
2. Integration tests for API endpoints
3. Performance benchmarks within limits
4. Security review completion
5. Documentation review
`,
    currentVersion: 4,
    lastComposedAt: '2025-02-18T10:00:00Z',
    lastReviewedAt: '2025-02-18T14:00:00Z',
    publishedAt: '2025-02-18T14:00:00Z',
    owner: 'Bob Martinez',
    tags: ['technical', 'LLM', 'standards', 'architecture', 'integration'],
    keyFacts: [
      'Three-layer architecture: interface, logic, data',
      'API must conform to OpenAPI 3.1',
      'Citation accuracy minimum 90%',
      'Response latency p95 under 2.5 seconds',
      'Five quality gates required before production',
    ],
    relatedSourceIds: ['src-002'],
    relatedPageIds: ['page-007', 'page-001'],
    relatedEntityIds: ['ent-003'],
  },
  {
    id: 'page-004',
    slug: 'document-processing-pipeline',
    title: 'Document Processing Pipeline',
    pageType: 'deep_dive',
    status: 'in_review',
    summary: 'Detailed technical guide to the document processing workflow, covering ingestion, parsing, chunking, embedding, and QA stages.',
    contentMd: `# Document Processing Pipeline

## Overview

The document processing pipeline transforms raw documents into knowledge-ready chunks that can be embedded, indexed, and retrieved by the LLM system.

## Pipeline Stages

### Stage 1: Ingestion

Raw documents are uploaded and validated:
- **Supported formats**: PDF, Markdown, DOCX, TXT
- **File size limit**: 50MB maximum
- **Validation**: MIME type verification and checksum computation
- **Rejection handling**: Clear error notification with reason

### Stage 2: Parsing

Documents are parsed to extract structured content:
- **PDF**: PyMuPDF for text extraction with layout preservation
- **Markdown**: Unified parsing preserving heading hierarchy
- **Extracted metadata**: Page numbers, headings, tables, lists
- **Table handling**: Tabular content preserved with row/column structure

### Stage 3: Chunking

Documents are split into semantic chunks:
- **Primary method**: Heading-based boundaries
- **Fallback**: 512-token sliding window with 64-token overlap
- **Constraints**: Never split code blocks, table rows, or list items
- **Validation**: Minimum 50 tokens per chunk (excluding headings)

### Stage 4: Embedding

Each chunk is vectorized for semantic search:
- **Model**: text-embedding-3-small (1536 dimensions)
- **Storage**: Vector database with source metadata tags
- **Indexing**: Automated index updates on new chunk creation

### Stage 5: QA & Validation

Automated quality checks before knowledge base integration:
- **Chunk completeness**: No chunk under 50 tokens
- **Semantic coherence**: Adjacent chunks share entity reference
- **Citation extraction**: All claims linked to source chunks
- **Duplication detection**: Chunks above 95% similarity flagged
- **Failed chunks**: Routed to manual review queue (48h SLA)

## Error Handling

Pipeline errors are categorized by severity:
- **Fatal**: Document rejected, upload must be retried
- **Warning**: Processing continues, issue logged
- **Info**: Processing noted, no action required

## Performance Metrics

- Average processing time: 45 seconds per document
- Maximum throughput: 200 documents per hour
- QA failure rate target: <3%
`,
    currentVersion: 1,
    lastComposedAt: '2025-03-01T10:00:00Z',
    lastReviewedAt: undefined,
    publishedAt: undefined,
    owner: 'Carol Nguyen',
    tags: ['pipeline', 'document-processing', 'technical', 'workflow'],
    keyFacts: [
      'File size limit: 50MB',
      'Chunk size: 512 tokens with 64-token overlap',
      'Minimum chunk size: 50 tokens',
      'QA failure rate target: <3%',
      'Manual review SLA: 48 hours',
    ],
    relatedSourceIds: ['src-003'],
    relatedPageIds: ['page-007', 'page-009'],
    relatedEntityIds: ['ent-009', 'ent-005'],
  },
  {
    id: 'page-005',
    slug: 'tensorflow',
    title: 'TensorFlow',
    pageType: 'entity',
    status: 'published',
    summary: 'Entity page for TensorFlow — an open-source machine learning framework developed by Google, widely used for model training and deployment.',
    contentMd: `# TensorFlow

## Overview

TensorFlow is an open-source machine learning framework developed by Google. It provides a comprehensive ecosystem for machine learning and deep learning, widely adopted across industry and research.

## Key Capabilities

- **Tensor computation**: Efficient multi-dimensional array operations
- **Automatic differentiation**: Gradient computation for training
- **Model zoo**: Pre-trained models for common tasks
- **Deployment**: Support for server, edge, and mobile deployment
- **TPU support**: First-class Google TPU acceleration

## Use in Our Organization

TensorFlow is used for:
- Training custom embedding models
- Fine-tuning classification models
- Batch inference pipelines
- Model serving infrastructure

## Integration with LLM Wiki

TensorFlow models are integrated via the standard ML model interface:
\`\`\`python
import tensorflow as tf
model = tf.keras.models.load_model('/models/embedding-v3')
embedding = model.encode(text)
\`\`\`

## Related Technologies

- [PyTorch](/pages/pytorch) — Alternative ML framework
- [JAX](/pages/jax) — Google's next-generation ML framework
- [embedding model comparison](/pages/embedding-model-comparison)
`,
    currentVersion: 1,
    lastComposedAt: '2025-01-25T15:00:00Z',
    lastReviewedAt: '2025-01-26T10:00:00Z',
    publishedAt: '2025-01-26T10:00:00Z',
    owner: 'David Park',
    tags: ['ML', 'framework', 'Google', 'deep-learning', 'open-source'],
    keyFacts: [
      'Developed by Google',
      'Open-source Apache 2.0 license',
      'Supports CPU, GPU, and TPU',
      'Used for embedding model training in our organization',
    ],
    relatedSourceIds: [],
    relatedPageIds: ['page-007', 'page-011'],
    relatedEntityIds: ['ent-008'],
  },
  {
    id: 'page-006',
    slug: 'claude-ai',
    title: 'Claude AI',
    pageType: 'entity',
    status: 'draft',
    summary: 'Entity page for Claude AI — Anthropic\'s LLM family known for constitutional AI training, strong reasoning capabilities, and enterprise-grade safety features.',
    contentMd: `# Claude AI

## Overview

Claude is a family of large language models developed by Anthropic. Claude models are known for constitutional AI training, strong reasoning capabilities, and enterprise-grade safety features.

## Model Variants

- **Claude 3.5 Sonnet**: Latest flagship model with enhanced reasoning
- **Claude 3.5 Haiku**: Fast, cost-efficient for high-volume tasks
- **Claude 3 Opus**: Maximum capability for complex reasoning

## Key Features

- **Constitutional AI**: Built-in safety alignment through RLHF
- **Extended context**: 200K token context window
- **Vision capability**: Image understanding and analysis
- **Tool use**: Native function calling and tool integration

## API Integration

Claude is available via the Anthropic API with our organization API key:
\`\`\`bash
curl https://api.anthropic.com/v1/messages \\
  -H "x-api-key: $ANTHROPIC_API_KEY" \\
  -H "anthropic-version: 2023-06-01" \\
  -d '{"model": "claude-3-5-sonnet-20241022", "max_tokens": 1024}'
\`\`\`

## Evaluation Results

In our internal benchmark suite, Claude 3.5 Sonnet achieved:
- Citation accuracy: 94.2% (exceeds 90% threshold)
- Hallucination rate: 2.1% (below 5% threshold)
- Response latency: 1.8s p95 (below 2.5s threshold)
- Fairness score: 91% (exceeds 85% threshold)

All metrics meet the Safety Evaluation Framework requirements.
`,
    currentVersion: 1,
    lastComposedAt: '2025-03-02T09:00:00Z',
    lastReviewedAt: undefined,
    publishedAt: undefined,
    owner: 'Alice Chen',
    tags: ['LLM', 'Anthropic', 'Claude', 'constitutional-AI', 'enterprise'],
    keyFacts: [
      'Developed by Anthropic',
      'Constitutional AI training approach',
      '200K token context window',
      'All evaluation metrics meet Safety Framework thresholds',
    ],
    relatedSourceIds: ['src-001', 'src-002'],
    relatedPageIds: ['page-003', 'page-009'],
    relatedEntityIds: ['ent-007'],
  },
  {
    id: 'page-007',
    slug: 'rag-architecture',
    title: 'RAG Architecture',
    pageType: 'deep_dive',
    status: 'published',
    summary: 'Comprehensive guide to Retrieval-Augmented Generation architecture patterns, including hybrid retrieval, re-ranking, context management, and citation attribution.',
    contentMd: `# RAG Architecture

## Introduction

Retrieval-Augmented Generation (RAG) enhances LLM responses by retrieving relevant knowledge from external sources before generating an answer. This document details our organization's RAG architecture standards.

## Core Components

### Retrieval Pipeline

The retrieval pipeline consists of three stages:

**1. Query Processing**
- Query embedding using the standard embedding model
- Query decomposition for complex multi-hop questions
- Query expansion with synonyms and related terms

**2. Retrieval**
- **Dense retrieval**: Vector similarity search in the vector database
- **Sparse retrieval**: BM25 keyword matching for recall enhancement
- **Hybrid combination**: Weighted combination of dense and sparse scores

**3. Re-ranking**
- Cross-encoder model re-ranks top-20 candidates
- Final selection based on re-ranking scores
- Fallback to "I don't know" if no chunk exceeds 0.72 relevance

### Context Management

- Target context window utilization: 85%
- Chunk-level citation attribution (not document-level)
- Maximum corpus size: 10 million documents per deployment

### Citation Attribution

Every factual claim in generated responses must have a citation:
- Citation format: [source-id:chunk-id]
- Inline citations in the response text
- Bibliography section at the end of responses
- Citations are clickable, linking to source chunks

## Advanced Patterns

### Parent Document Retrieval (Q1 2025 Update)

Instead of returning top-k chunks directly, the system now:
1. Retrieves parent documents for top-k chunks
2. Re-chunks at query time using question context
3. Reduces citation fragmentation by 34%

### Hypothetical Document Embeddings (HyDE)

For complex queries:
1. Generate a hypothetical answer to the query
2. Embed the hypothetical answer
3. Use that embedding for retrieval
4. Improves multi-hop recall by 28%

### Structured Knowledge Injection

Entity relationships from the knowledge graph are injected into context alongside chunk retrieval, improving consistency on multi-entity queries.

## Architecture Diagram

\`\`\`
User Query
    │
    ▼
Query Processing
    │
    ├──► Dense Embedding ──► Vector DB Search
    │
    └──► BM25 Index Search
            │
            ▼
    Hybrid Score Combination
            │
            ▼
    Cross-Encoder Re-ranking (top-20)
            │
            ▼
    Context Assembly + KG Injection
            │
            ▼
    LLM Generation with Citations
            │
            ▼
Grounded Response with Bibliography
\`\`\`

## Performance Targets

| Metric | Target |
|--------|--------|
| Recall@10 | > 0.91 |
| Precision@5 | > 0.87 |
| Citation accuracy | > 90% |
| Answer quality (human eval) | > 4.2/5 |
`,
    currentVersion: 5,
    lastComposedAt: '2025-03-05T11:00:00Z',
    lastReviewedAt: '2025-03-05T15:00:00Z',
    publishedAt: '2025-03-05T15:00:00Z',
    owner: 'Bob Martinez',
    tags: ['RAG', 'architecture', 'retrieval', 'deep-dive', 'knowledge'],
    keyFacts: [
      'Hybrid retrieval: dense vector + BM25',
      'Cross-encoder re-ranking on top-20 candidates',
      'Context window utilization target: 85%',
      'Citation at chunk level, not document level',
      '10M document max corpus per deployment',
      'Fallback: "I don\'t know" below 0.72 relevance threshold',
    ],
    relatedSourceIds: ['src-002', 'src-005'],
    relatedPageIds: ['page-001', 'page-003', 'page-010'],
    relatedEntityIds: ['ent-001', 'ent-012', 'ent-002'],
  },
  {
    id: 'page-008',
    slug: 'prompt-engineering-guidelines',
    title: 'Prompt Engineering Guidelines',
    pageType: 'summary',
    status: 'stale',
    summary: 'Summary of prompt engineering best practices for LLM interactions, including few-shot examples, chain-of-thought reasoning, and output formatting.',
    contentMd: `# Prompt Engineering Guidelines

## Overview

Effective prompt engineering is critical for achieving reliable, high-quality outputs from LLMs. This page summarizes our organization's prompt engineering standards.

## Core Principles

### 1. Be Explicit
Clearly specify the task, constraints, and expected format in the prompt. Ambiguity leads to unpredictable outputs.

### 2. Provide Context
Include relevant background information, domain-specific terminology definitions, and relevant examples.

### 3. Define Output Format
Specify the exact output format required: JSON schema, markdown structure, plain text, etc.

### 4. Use Few-Shot Examples
For complex tasks, provide 2-5 examples of input-output pairs to guide the model's behavior.

## Chain-of-Thought Prompting

For reasoning tasks:
1. Include "Let's think step by step" in the system prompt
2. Ask the model to show its reasoning before the final answer
3. Verify that intermediate steps are logical and grounded

## Citation Requirements

All prompts must include:
- Requirement to cite sources inline
- Instruction to return "I don't know" if uncertain
- Instruction to distinguish between facts and inferences

## Anti-Patterns to Avoid

- **Vague instructions**: "be helpful" without specifics
- **Conflicting constraints**: instructions that contradict each other
- **Missing edge cases**: not specifying behavior for unusual inputs
`,
    currentVersion: 2,
    lastComposedAt: '2025-01-28T10:00:00Z',
    lastReviewedAt: '2025-01-28T12:00:00Z',
    publishedAt: '2025-01-28T12:00:00Z',
    owner: 'Emma Wilson',
    tags: ['prompting', 'LLM', 'best-practices', 'guidelines'],
    keyFacts: [
      'Be explicit and specific in prompts',
      'Provide 2-5 few-shot examples for complex tasks',
      'Chain-of-thought for reasoning tasks',
      'Require inline citations in all factual responses',
    ],
    relatedSourceIds: [],
    relatedPageIds: ['page-003', 'page-007'],
    relatedEntityIds: ['ent-010'],
  },
  {
    id: 'page-009',
    slug: 'safety-evaluation-framework',
    title: 'Safety Evaluation Framework',
    pageType: 'deep_dive',
    status: 'in_review',
    summary: 'Detailed documentation of the Safety Evaluation Framework — systematic approach to evaluating AI safety including bias, hallucination rate, and PII detection.',
    contentMd: `# Safety Evaluation Framework

## Purpose

The Safety Evaluation Framework (SEF) is a systematic approach to evaluating AI safety across multiple dimensions before production deployment.

## Evaluation Dimensions

### 1. Bias Assessment

- **Method**: Disaggregated evaluation across protected attributes (race, gender, age, geography)
- **Metric**: Fairness score computed using equalized odds difference
- **Threshold**: Minimum 85% fairness score
- **Test dataset**: Curated dataset of 10,000 diverse scenarios

### 2. Content Safety

- **Harmful output detection**: Binary classification for harmful/violating content
- **Required rate**: <0.1% false negatives (harmful content not caught)
- **Test method**: Red team probing with adversarial prompts

### 3. Citation Accuracy

- **Method**: Automated comparison of claims in output against source documents
- **Threshold**: >90% of factual claims must have valid source citation
- **Evaluation dataset**: 500 diverse questions with known answers

### 4. Hallucination Rate

- **Definition**: Percentage of responses containing facts not supported by retrieved context
- **Threshold**: <5% hallucination rate
- **Detection method**: Automated fact-checking against knowledge base

### 5. PII Detection

- **Required rate**: >95% PII detection rate
- **PII types**: Name, email, phone, SSN, credit card, address, medical ID
- **Required action**: Automatic redaction before output

## Evaluation Process

1. **Automated testing**: Run full evaluation suite (8-12 hours)
2. **Red team review**: Independent security team probing (1-2 days)
3. **Human evaluation**: Random sample human review (500 responses)
4. **Report generation**: Compile evaluation report with pass/fail status
5. **Escalation**: Critical failures escalate to AI Safety Board

## Pass Criteria

A system passes the SEF only if ALL dimensions meet thresholds. Partial passes are not permitted for production deployment.

## Related Standards

- [AI Policy & Governance Guidelines v2.1](/sources/src-001)
- [LLM Integration Standards](/pages/llm-integration-standards)
`,
    currentVersion: 1,
    lastComposedAt: '2025-03-10T09:00:00Z',
    lastReviewedAt: undefined,
    publishedAt: undefined,
    owner: 'Alice Chen',
    tags: ['safety', 'evaluation', 'bias', 'compliance', 'AI'],
    keyFacts: [
      'Fairness score minimum: 85%',
      'Citation accuracy minimum: 90%',
      'Hallucination rate maximum: 5%',
      'PII detection rate minimum: 95%',
      'All 5 dimensions must pass for production deployment',
    ],
    relatedSourceIds: ['src-001'],
    relatedPageIds: ['page-001', 'page-003'],
    relatedEntityIds: ['ent-004'],
  },
  {
    id: 'page-010',
    slug: 'retrieval-augmented-generation',
    title: 'Retrieval-Augmented Generation',
    pageType: 'entity',
    status: 'published',
    summary: 'Entity page for Retrieval-Augmented Generation — a technique that enhances LLM responses by retrieving relevant knowledge from external sources.',
    contentMd: `# Retrieval-Augmented Generation

## Definition

Retrieval-Augmented Generation (RAG) is an AI architecture that enhances large language model responses by first retrieving relevant documents or knowledge from an external corpus before generating the final response.

## How RAG Works

1. **Query encoding**: The user query is converted to a vector embedding
2. **Similarity search**: The embedding is compared against the knowledge corpus
3. **Context assembly**: Top-scoring documents are retrieved and formatted as context
4. **Grounded generation**: The LLM generates a response using the retrieved context
5. **Citation attribution**: All factual claims are linked back to source documents

## Benefits

- **Reduced hallucination**: Responses grounded in actual retrieved documents
- **Up-to-date knowledge**: Knowledge base can be updated without retraining
- **Source transparency**: Every claim can be traced to its source document
- **Domain adaptation**: Easy to adapt to new domains by updating the corpus
- **Auditability**: Full trail of what information was used in each response

## Components

- **Vector database**: Stores and retrieves document embeddings
- **Embedding model**: Converts text to vector representations
- **Retrieval algorithm**: Defines how documents are retrieved and ranked
- **LLM**: Generates responses from retrieved context

## Limitations

- Retrieval quality depends on embedding model performance
- Context window limits how much context can be included
- Duplicate or contradictory sources can confuse the system
- Very long documents may lose important details in chunking

## Implementation Standards

See [RAG Architecture](/pages/rag-architecture) for the full technical specification.
`,
    currentVersion: 2,
    lastComposedAt: '2025-02-10T14:00:00Z',
    lastReviewedAt: '2025-02-10T16:00:00Z',
    publishedAt: '2025-02-10T16:00:00Z',
    owner: 'Bob Martinez',
    tags: ['RAG', 'retrieval', 'LLM', 'knowledge', 'architecture'],
    keyFacts: [
      'Reduces hallucination by grounding responses in retrieved documents',
      'Knowledge base can be updated without LLM retraining',
      'Every claim is traceable to its source document',
      'Context window limits apply',
    ],
    relatedSourceIds: ['src-002', 'src-005'],
    relatedPageIds: ['page-007', 'page-011'],
    relatedEntityIds: ['ent-001'],
  },
  {
    id: 'page-011',
    slug: 'knowledge-graph-best-practices',
    title: 'Knowledge Graph Best Practices',
    pageType: 'overview',
    status: 'draft',
    summary: 'Overview of best practices for building and maintaining knowledge graphs, including entity extraction, relationship mapping, and consistency management.',
    contentMd: `# Knowledge Graph Best Practices

## Overview

A knowledge graph represents entities and their relationships in a structured format that can be queried, reasoned over, and used to enhance AI system performance.

## Entity Management

### Entity Extraction
- Use NER models to extract entities from documents
- Normalize entity names to prevent duplicates
- Maintain entity aliases and historical names
- Assign entity types (person, technology, concept, etc.)

### Entity Resolution
- Link entities across different sources
- Detect duplicate entities and merge them
- Track entity relationships over time

## Relationship Mapping

### Relationship Types
- Hierarchical: parent-child, part-of, instance-of
- Associative: related-to, mentions, mentions
- Causal: causes, enables, depends-on
- Temporal: preceded-by, succeeded-by

### Relationship Confidence
- Rate relationship confidence based on source reliability
- Flag uncertain relationships for manual review
- Track relationship evolution over time

## Graph Maintenance

### Consistency Checks
- Detect circular relationships
- Validate type constraints for relationship endpoints
- Check for orphaned entities (no incoming relationships)

### Update Propagation
- When a source document is updated, identify affected entities
- Re-run entity extraction and relationship mapping
- Flag affected pages for review

## Query Patterns

Common useful queries:
- "Find all entities of type X mentioned in document Y"
- "What entities are related to entity Z within 2 hops"
- "Which entities have conflicting descriptions across sources"
`,
    currentVersion: 1,
    lastComposedAt: '2025-03-08T10:00:00Z',
    lastReviewedAt: undefined,
    publishedAt: undefined,
    owner: 'Emma Wilson',
    tags: ['knowledge-graph', 'entity', 'relationships', 'best-practices'],
    keyFacts: [
      'Entity types: person, technology, concept, organization, etc.',
      'Relationship types: hierarchical, associative, causal, temporal',
      'Graph maintenance requires consistency checks and update propagation',
    ],
    relatedSourceIds: [],
    relatedPageIds: ['page-010', 'page-007'],
    relatedEntityIds: ['ent-002'],
  },
  {
    id: 'page-012',
    slug: 'compliance-audit-process',
    title: 'Compliance Audit Process',
    pageType: 'deep_dive',
    status: 'published',
    summary: 'Deep dive into the compliance audit process for AI systems, covering audit scheduling, scope definition, evidence collection, and remediation.',
    contentMd: `# Compliance Audit Process

## Purpose

The Compliance Audit Process ensures that all AI systems deployed in the organization meet governance, safety, and privacy requirements on an ongoing basis.

## Audit Schedule

- **Quarterly audits**: All active AI systems
- **Annual comprehensive audits**: Full governance review
- **Event-triggered audits**: Triggered by safety incidents or policy changes

## Audit Scope

Each audit covers:
1. Documentation review (policy compliance)
2. System configuration review
3. Access control verification
4. Data handling compliance
5. Safety evaluation results
6. Incident history and remediation

## Evidence Collection

Auditors collect:
- System logs and access records
- Configuration snapshots
- Evaluation reports
- Incident reports and post-mortems
- User feedback and escalation records

## Remediation Process

### Finding Classification
- **Critical**: Must be resolved within 7 days
- **High**: Must be resolved within 30 days
- **Medium**: Must be resolved within 90 days
- **Low**: Address in next quarterly review

### Escalation Path
1. Finding identified and documented
2. System owner notified with remediation deadline
3. Remediation plan submitted within 5 business days
4. Verification audit conducted after remediation
5. Finding closed when verified

## Audit Report

The final audit report includes:
- Executive summary of overall compliance posture
- Detailed findings by category
- Remediation status of previous findings
- Recommendations for improvement
- Sign-off from Chief Compliance Officer

## Roles and Responsibilities

| Role | Responsibility |
|------|---------------|
| Auditors | Conducting audit, documenting findings |
| System Owners | Providing evidence, implementing remediation |
| Compliance Team | Scheduling audits, tracking remediation |
| CCO | Final report sign-off |

## Related Documents

- [AI Governance Overview](/pages/ai-governance-overview)
- [Data Privacy Compliance](/pages/data-privacy-compliance)
`,
    currentVersion: 3,
    lastComposedAt: '2025-02-25T14:00:00Z',
    lastReviewedAt: '2025-02-26T10:00:00Z',
    publishedAt: '2025-02-26T10:00:00Z',
    owner: 'Carol Nguyen',
    tags: ['compliance', 'audit', 'governance', 'process', 'policy'],
    keyFacts: [
      'Quarterly audits for all active AI systems',
      'Annual comprehensive governance review',
      'Critical findings: 7-day remediation',
      'High findings: 30-day remediation',
      'CCO sign-off required on final report',
    ],
    relatedSourceIds: ['src-001'],
    relatedPageIds: ['page-001', 'page-002'],
    relatedEntityIds: ['ent-011'],
  },
]

// --- PAGE VERSIONS ---

export const MOCK_PAGE_VERSIONS: PageVersion[] = [
  {
    id: 'pv-001',
    pageId: 'page-001',
    versionNo: 1,
    contentMd: '# AI Governance Overview\n\nInitial draft covering basic governance principles.',
    changeSummary: 'Initial draft creation from AI Policy document',
    createdAt: '2025-02-01T10:00:00Z',
    createdByAgentOrUser: 'PageComposer Agent',
    reviewStatus: 'approved',
  },
  {
    id: 'pv-002',
    pageId: 'page-001',
    versionNo: 2,
    contentMd: '# AI Governance Overview\n\n## Summary\n\nAdded safety standards section.',
    changeSummary: 'Added comprehensive safety standards section from chunk-003',
    createdAt: '2025-02-10T14:00:00Z',
    createdByAgentOrUser: 'Alice Chen',
    reviewStatus: 'approved',
  },
  {
    id: 'pv-003',
    pageId: 'page-001',
    versionNo: 3,
    contentMd: MOCK_PAGES[0].contentMd,
    changeSummary: 'Final review: aligned terminology with latest policy document, added related documents section',
    createdAt: '2025-02-20T14:30:00Z',
    createdByAgentOrUser: 'Reviewer Agent',
    reviewStatus: 'approved',
  },
]

// --- JOBS ---

export const MOCK_JOBS: Job[] = [
  {
    id: 'job-001',
    jobType: 'ingest',
    status: 'completed',
    startedAt: '2025-01-15T10:30:00Z',
    finishedAt: '2025-01-15T10:35:00Z',
    inputRef: 'src-001',
    outputRef: 'src-001-processed',
    errorMessage: undefined,
    logsJson: ['Validating file format...', 'Parsing document structure...', 'Extracting text content...', 'Ingestion complete.'],
  },
  {
    id: 'job-002',
    jobType: 'embed',
    status: 'completed',
    startedAt: '2025-01-15T10:36:00Z',
    finishedAt: '2025-01-15T10:42:00Z',
    inputRef: 'src-001',
    outputRef: 'embeddings-001',
    errorMessage: undefined,
    logsJson: ['Creating embedding batches...', 'Processing 89 chunks...', 'Indexing embeddings in vector store...', 'Embedding complete.'],
  },
  {
    id: 'job-003',
    jobType: 'compose',
    status: 'failed',
    startedAt: '2025-03-10T08:00:00Z',
    finishedAt: '2025-03-10T08:15:00Z',
    inputRef: 'page-009',
    outputRef: undefined,
    errorMessage: 'Chunk retrieval failed: vector store timeout after 30s. Unable to retrieve sufficient context for Safety Evaluation Framework content.',
    logsJson: ['Starting page composition...', 'Retrieving relevant chunks...', 'ERROR: Vector store timeout after 30s', 'Retry attempt 1 failed', 'Retry attempt 2 failed', 'Job marked as failed.'],
  },
  {
    id: 'job-004',
    jobType: 'rebuild',
    status: 'failed',
    startedAt: '2025-03-12T11:00:00Z',
    finishedAt: '2025-03-12T11:30:00Z',
    inputRef: 'src-003',
    outputRef: undefined,
    errorMessage: 'Parser error: Unable to extract tables from DOCX with merged cells. Only standard table formats are supported.',
    logsJson: ['Starting source rebuild...', 'Parsing document...', 'WARNING: Detected merged cell in table', 'ERROR: Parser failed on table extraction', 'Job marked as failed.'],
  },
  {
    id: 'job-005',
    jobType: 'ingest',
    status: 'completed',
    startedAt: '2025-03-01T09:00:00Z',
    finishedAt: '2025-03-01T09:10:00Z',
    inputRef: 'src-005',
    outputRef: 'src-005-processed',
    errorMessage: undefined,
    logsJson: ['Validating file format...', 'Parsing markdown...', 'Extracting structured sections...', 'Ingestion complete.'],
  },
]

// --- REVIEW ITEMS ---

export const MOCK_REVIEW_ITEMS: ReviewItem[] = [
  {
    id: 'rev-001',
    pageId: 'page-004',
    pageTitle: 'Document Processing Pipeline',
    pageSlug: 'document-processing-pipeline',
    pageStatus: 'in_review',
    issueType: 'missing_citation',
    severity: 'high',
    issues: [
      {
        type: 'missing_citation',
        severity: 'high',
        message: 'Section 4.4 states "QA failure rate target: <3%" but no source citation provided for this metric.',
        evidence: 'The 3% target appears to be an organizational standard, not directly quoted from a source document. Need to either cite the source or mark as inferred.',
        sourceChunkId: undefined,
        claimId: 'clm-014',
      },
      {
        type: 'missing_citation',
        severity: 'medium',
        message: 'Average processing time "45 seconds per document" lacks source verification.',
        evidence: 'Performance metrics are derived from internal monitoring data, not source documents.',
      },
    ],
    oldContentMd: `# Document Processing Pipeline\n\n## Overview\n\nInitial overview content.`,
    newContentMd: `# Document Processing Pipeline\n\n## Overview\n\nThe document processing pipeline transforms raw documents into knowledge-ready chunks.\n\n## Pipeline Stages\n\n### Stage 1: Ingestion\n\nRaw documents are uploaded and validated...`,
    changeSummary: 'Composed from SOP: Document Processing Workflow (src-003). Added missing sections from chunk-007 and chunk-008.',
    confidenceScore: 72,
    createdAt: '2025-03-01T10:30:00Z',
    updatedAt: '2025-03-01T10:30:00Z',
    previousVersion: 1,
    sourceIds: ['src-003'],
    evidenceSnippets: [
      {
        sourceId: 'src-003',
        sourceTitle: 'Internal SOP: Document Processing Workflow',
        chunkId: 'chunk-007',
        content: 'Documents are split into semantic chunks using heading-based boundaries combined with a 512-token sliding window with 64-token overlap.',
        relevance: 92,
      },
      {
        sourceId: 'src-003',
        sourceTitle: 'Internal SOP: Document Processing Workflow',
        chunkId: 'chunk-008',
        content: 'After document processing, automated QA checks are performed: Chunk completeness: no chunk under 50 tokens.',
        relevance: 85,
      },
    ],
  },
  {
    id: 'rev-002',
    pageId: 'page-008',
    pageTitle: 'Prompt Engineering Guidelines',
    pageSlug: 'prompt-engineering-guidelines',
    pageStatus: 'stale',
    issueType: 'stale_content',
    severity: 'medium',
    issues: [
      {
        type: 'stale_content',
        severity: 'medium',
        message: 'This page references "few-shot examples" guidance that has been updated in the Q1 2025 KB update. New recommendation is to use 3-5 examples for complex tasks, up from 2.',
        evidence: 'src-005 (Q1 2025 KB Update) section on prompt patterns recommends "3-5 examples" instead of the 2-5 range currently in the page.',
        sourceChunkId: 'chunk-010',
        claimId: undefined,
      },
    ],
    oldContentMd: `# Prompt Engineering Guidelines\n\n## Core Principles\n\nProvide 2-5 examples of input-output pairs to guide the model's behavior.`,
    newContentMd: `# Prompt Engineering Guidelines\n\n## Core Principles\n\n### 1. Be Explicit\n\nClearly specify the task, constraints, and expected format.\n\n### 2. Provide Context\n\nInclude relevant background information.\n\n### 3. Use Few-Shot Examples\n\nFor complex tasks, provide **3-5 examples** of input-output pairs. (Updated from Q1 2025 KB: previously recommended 2-5 examples)`,
    changeSummary: 'Updated few-shot example count from "2-5" to "3-5" based on Q1 2025 update.',
    confidenceScore: 88,
    createdAt: '2025-03-05T08:00:00Z',
    updatedAt: '2025-03-05T08:00:00Z',
    previousVersion: 2,
    sourceIds: ['src-005'],
    evidenceSnippets: [
      {
        sourceId: 'src-005',
        sourceTitle: 'Q1 2025 Knowledge Base Update',
        chunkId: 'chunk-010',
        content: 'Hypothetical Document Embeddings (HyDE): For complex queries, we first generate a hypothetical answer...',
        relevance: 75,
      },
    ],
  },
  {
    id: 'rev-003',
    pageId: 'page-009',
    pageTitle: 'Safety Evaluation Framework',
    pageSlug: 'safety-evaluation-framework',
    pageStatus: 'in_review',
    issueType: 'conflict_detected',
    severity: 'critical',
    issues: [
      {
        type: 'conflict_detected',
        severity: 'critical',
        message: 'The page states "minimum 85% fairness score" which conflicts with the technical standards document (src-002) which specifies 87% as the evaluation threshold for bias assessment.',
        evidence: 'src-002 Chapter 2 states: "Bias assessment: minimum 87% fairness score across protected attributes for production LLM systems." This conflicts with src-001 which states 85%.',
        sourceChunkId: 'chunk-005',
        claimId: undefined,
      },
    ],
    oldContentMd: '',
    newContentMd: `# Safety Evaluation Framework\n\n## Evaluation Dimensions\n\n### 1. Bias Assessment\n\n- **Threshold**: Minimum 85% fairness score\n\n(Conflicting value found in src-002: 87%)`,
    changeSummary: 'New page composed from AI Policy document. Contains fairness threshold that may conflict with technical standards.',
    confidenceScore: 65,
    createdAt: '2025-03-10T09:30:00Z',
    updatedAt: '2025-03-10T09:30:00Z',
    previousVersion: undefined,
    sourceIds: ['src-001', 'src-002'],
    evidenceSnippets: [
      {
        sourceId: 'src-001',
        sourceTitle: 'AI Policy & Governance Guidelines v2.1',
        chunkId: 'chunk-003',
        content: 'Bias assessment with minimum 85% fairness score across protected attributes',
        relevance: 96,
      },
      {
        sourceId: 'src-002',
        sourceTitle: 'Technical Standards for LLM Systems v1.0',
        chunkId: 'chunk-005',
        content: 'The standard evaluation metrics for production LLM systems are defined as follows: ROUGE-L score minimum 0.42 for summarization tasks',
        relevance: 88,
      },
    ],
  },
  {
    id: 'rev-004',
    pageId: 'page-011',
    pageTitle: 'Knowledge Graph Best Practices',
    pageSlug: 'knowledge-graph-best-practices',
    pageStatus: 'draft',
    issueType: 'unsupported_claim',
    severity: 'high',
    issues: [
      {
        type: 'unsupported_claim',
        severity: 'high',
        message: 'The page states "Graph maintenance requires consistency checks and update propagation" without citing a source. This claim needs verification or citation.',
        evidence: 'No source document explicitly states this requirement. The claim appears to be derived from general knowledge graph best practices but lacks specific source grounding.',
        claimId: undefined,
      },
    ],
    oldContentMd: '',
    newContentMd: `# Knowledge Graph Best Practices\n\n## Graph Maintenance\n\n### Consistency Checks\n- Detect circular relationships\n- Validate type constraints\n\n### Update Propagation\n- When source is updated, identify affected entities\n- Re-run entity extraction\n`,
    changeSummary: 'Initial draft composed from organizational knowledge. Several claims lack explicit source citations.',
    confidenceScore: 58,
    createdAt: '2025-03-08T10:30:00Z',
    updatedAt: '2025-03-08T10:30:00Z',
    previousVersion: undefined,
    sourceIds: [],
    evidenceSnippets: [],
  },
  {
    id: 'rev-005',
    pageId: 'page-007',
    pageTitle: 'RAG Architecture',
    pageSlug: 'rag-architecture',
    pageStatus: 'published',
    issueType: 'low_confidence',
    severity: 'low',
    issues: [
      {
        type: 'low_confidence',
        severity: 'low',
        message: 'The HyDE recall improvement metric (28%) is cited from Q1 2025 KB update which itself may be based on experimental results rather than production benchmarks. Consider verifying in production environment.',
        evidence: 'chunk-010 (src-005) states: "HyDE approach improves recall on multi-hop questions by 28%." This is from the quarterly update which cites internal experiments.',
      },
    ],
    oldContentMd: `# RAG Architecture\n\n## Advanced Patterns\n\n### Hypothetical Document Embeddings (HyDE)\n\n...improves multi-hop recall by 28%`,
    newContentMd: `# RAG Architecture\n\n## Advanced Patterns\n\n### Hypothetical Document Embeddings (HyDE)\n\nFor complex queries, the HyDE approach generates a hypothetical answer and uses it for retrieval. Reported recall improvement: **28%** (from Q1 2025 KB Update — internal benchmarks; verify in production).`,
    changeSummary: 'Added verification note to HyDE recall metric.',
    confidenceScore: 81,
    createdAt: '2025-03-06T14:00:00Z',
    updatedAt: '2025-03-06T14:00:00Z',
    previousVersion: 4,
    sourceIds: ['src-005'],
    evidenceSnippets: [
      {
        sourceId: 'src-005',
        sourceTitle: 'Q1 2025 Knowledge Base Update',
        chunkId: 'chunk-010',
        content: 'HyDE approach improves recall on multi-hop questions by 28%.',
        relevance: 94,
      },
    ],
  },
]

// --- DASHBOARD STATS ---

const generateTimeSeriesData = (): TimeSeriesPoint[] => {
  const points: TimeSeriesPoint[] = []
  for (let i = 29; i >= 0; i--) {
    const date = new Date()
    date.setDate(date.getDate() - i)
    const baseValue = 5 + Math.floor(i / 7)
    const variance = Math.floor(Math.random() * 3)
    points.push({
      date: date.toISOString().split('T')[0],
      value: baseValue + variance,
      label: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    })
  }
  return points
}

export const MOCK_DASHBOARD_STATS: DashboardStats = {
  totalSources: 5,
  totalPages: 12,
  publishedPages: 8,
  draftPages: 2,
  inReviewPages: 2,
  stalePages: 1,
  unverifiedClaims: 8,
  reviewQueueCount: 5,
  lastSyncTime: new Date(Date.now() - 1800000).toISOString(), // 30 min ago
  failedJobsCount: 2,
  totalChunks: 25,
  totalEntities: 12,
  sourceTypeBreakdown: {
    pdf: 2,
    markdown: 3,
  },
  pageStatusBreakdown: {
    published: 8,
    draft: 2,
    in_review: 2,
    stale: 1,
  },
  pagesPublishedOverTime: generateTimeSeriesData(),
  recentActivity: [
    {
      id: 'act-001',
      type: 'page_published',
      description: '"RAG Architecture" page was published',
      entityId: 'page-007',
      entityTitle: 'RAG Architecture',
      timestamp: new Date(Date.now() - 1800000).toISOString(),
      user: 'Bob Martinez',
    },
    {
      id: 'act-002',
      type: 'review_completed',
      description: 'Review completed for "LLM Integration Standards"',
      entityId: 'page-003',
      entityTitle: 'LLM Integration Standards',
      timestamp: new Date(Date.now() - 3600000 * 2).toISOString(),
      user: 'Alice Chen',
    },
    {
      id: 'act-003',
      type: 'source_uploaded',
      description: 'Q1 2025 Knowledge Base Update uploaded',
      entityId: 'src-005',
      entityTitle: 'Q1 2025 Knowledge Base Update',
      timestamp: new Date(Date.now() - 3600000 * 4).toISOString(),
      user: 'Emma Wilson',
    },
    {
      id: 'act-004',
      type: 'job_failed',
      description: 'Source rebuild failed: DOCX table parsing error',
      entityId: 'job-004',
      entityTitle: 'job-004',
      timestamp: new Date(Date.now() - 3600000 * 5).toISOString(),
      user: undefined,
    },
    {
      id: 'act-005',
      type: 'page_draft_created',
      description: 'Draft created: "Knowledge Graph Best Practices"',
      entityId: 'page-011',
      entityTitle: 'Knowledge Graph Best Practices',
      timestamp: new Date(Date.now() - 3600000 * 8).toISOString(),
      user: 'Emma Wilson',
    },
    {
      id: 'act-006',
      type: 'claim_conflict_detected',
      description: 'Claim conflict detected: fairness score threshold differs between sources',
      entityId: 'clm-002',
      entityTitle: 'clm-002',
      timestamp: new Date(Date.now() - 3600000 * 10).toISOString(),
      user: undefined,
    },
    {
      id: 'act-007',
      type: 'source_rebuilt',
      description: 'Source "Internal SOP: Document Processing Workflow" rebuilt',
      entityId: 'src-003',
      entityTitle: 'Internal SOP: Document Processing Workflow',
      timestamp: new Date(Date.now() - 3600000 * 24).toISOString(),
      user: 'Carol Nguyen',
    },
  ],
  failedJobs: [MOCK_JOBS[2], MOCK_JOBS[3]],
}

// --- GRAPH DATA ---

export const MOCK_GRAPH_DATA: GraphData = {
  nodes: [
    // Pages
    { id: 'page-001', type: 'page', label: 'AI Governance Overview', status: 'published', description: 'Summary of AI governance framework' },
    { id: 'page-002', type: 'page', label: 'Data Privacy Compliance', status: 'published', description: 'GDPR and privacy requirements' },
    { id: 'page-003', type: 'page', label: 'LLM Integration Standards', status: 'published', description: 'Technical standards for LLM integration' },
    { id: 'page-004', type: 'page', label: 'Document Processing Pipeline', status: 'in_review', description: 'End-to-end document processing' },
    { id: 'page-005', type: 'page', label: 'TensorFlow', status: 'published', description: 'ML framework entity page' },
    { id: 'page-006', type: 'page', label: 'Claude AI', status: 'draft', description: 'Anthropic LLM entity page' },
    { id: 'page-007', type: 'page', label: 'RAG Architecture', status: 'published', description: 'Retrieval-Augmented Generation architecture' },
    { id: 'page-008', type: 'page', label: 'Prompt Engineering', status: 'stale', description: 'Prompt engineering best practices' },
    { id: 'page-009', type: 'page', label: 'Safety Evaluation Framework', status: 'in_review', description: 'AI safety evaluation methodology' },
    { id: 'page-010', type: 'page', label: 'Retrieval-Augmented Generation', status: 'published', description: 'RAG concept entity' },
    { id: 'page-011', type: 'page', label: 'Knowledge Graph Best Practices', status: 'draft', description: 'KG construction and maintenance' },
    { id: 'page-012', type: 'page', label: 'Compliance Audit Process', status: 'published', description: 'Compliance audit workflow' },
    // Entities
    { id: 'ent-001', type: 'entity', label: 'RAG', entityType: 'concept', description: 'Retrieval-Augmented Generation' },
    { id: 'ent-002', type: 'entity', label: 'Knowledge Graph', entityType: 'concept', description: 'Structured entity relationship representation' },
    { id: 'ent-003', type: 'entity', label: 'LLM Standards', entityType: 'process', description: 'LLM integration standards process' },
    { id: 'ent-004', type: 'entity', label: 'Safety Framework', entityType: 'process', description: 'Safety evaluation process' },
    { id: 'ent-005', type: 'entity', label: 'Embedding Model', entityType: 'technology', description: 'Text to vector conversion' },
    { id: 'ent-006', type: 'entity', label: 'Vector DB', entityType: 'technology', description: 'High-dimensional vector storage' },
    { id: 'ent-007', type: 'entity', label: 'Claude AI', entityType: 'technology', description: "Anthropic's LLM family" },
    { id: 'ent-008', type: 'entity', label: 'TensorFlow', entityType: 'technology', description: "Google's ML framework" },
    { id: 'ent-009', type: 'entity', label: 'Chunking Strategy', entityType: 'concept', description: 'Document segmentation methods' },
    { id: 'ent-010', type: 'entity', label: 'Prompt Engineering', entityType: 'concept', description: 'Prompt design practices' },
    { id: 'ent-011', type: 'entity', label: 'AI Governance', entityType: 'concept', description: 'AI governance principles' },
    { id: 'ent-012', type: 'entity', label: 'Hybrid Retrieval', entityType: 'concept', description: 'Dense + sparse retrieval' },
  ],
  edges: [
    { id: 'edge-001', source: 'page-001', target: 'ent-011', relationType: 'mentions' },
    { id: 'edge-002', source: 'page-001', target: 'ent-004', relationType: 'mentions' },
    { id: 'edge-003', source: 'page-001', target: 'page-012', relationType: 'related_to' },
    { id: 'edge-004', source: 'page-003', target: 'ent-003', relationType: 'derived_from' },
    { id: 'edge-005', source: 'page-007', target: 'ent-001', relationType: 'mentions' },
    { id: 'edge-006', source: 'page-007', target: 'ent-012', relationType: 'mentions' },
    { id: 'edge-007', source: 'page-007', target: 'ent-002', relationType: 'mentions' },
    { id: 'edge-008', source: 'page-010', target: 'ent-001', relationType: 'mentions' },
    { id: 'edge-009', source: 'page-004', target: 'ent-009', relationType: 'mentions' },
    { id: 'edge-010', source: 'page-004', target: 'ent-005', relationType: 'mentions' },
    { id: 'edge-011', source: 'page-005', target: 'ent-008', relationType: 'mentions' },
    { id: 'edge-012', source: 'page-006', target: 'ent-007', relationType: 'mentions' },
    { id: 'edge-013', source: 'page-008', target: 'ent-010', relationType: 'mentions' },
    { id: 'edge-014', source: 'page-009', target: 'ent-004', relationType: 'mentions' },
    { id: 'edge-015', source: 'page-009', target: 'ent-011', relationType: 'related_to' },
    { id: 'edge-016', source: 'page-011', target: 'ent-002', relationType: 'mentions' },
    { id: 'edge-017', source: 'page-012', target: 'ent-011', relationType: 'mentions' },
    { id: 'edge-018', source: 'page-003', target: 'page-007', relationType: 'related_to' },
    { id: 'edge-019', source: 'page-007', target: 'page-010', relationType: 'parent_child' },
    { id: 'edge-020', source: 'ent-001', target: 'ent-012', relationType: 'depends_on' },
    { id: 'edge-021', source: 'ent-001', target: 'ent-005', relationType: 'depends_on' },
    { id: 'edge-022', source: 'ent-001', target: 'ent-006', relationType: 'depends_on' },
  ],
}

// --- ASK RESPONSES ---

export const MOCK_ASK_RESPONSES: Record<string, AskResponse> = {
  'What is RAG and how does it work?': {
    id: 'ask-001',
    question: 'What is RAG and how does it work?',
    answer: `## Retrieval-Augmented Generation (RAG)

**RAG (Retrieval-Augmented Generation)** is an AI architecture that enhances large language model responses by first retrieving relevant documents from an external knowledge corpus before generating the final response.

### How RAG Works

1. **Query Encoding**: The user query is converted to a vector embedding using an embedding model (e.g., text-embedding-3-small, 1536 dimensions)

2. **Similarity Search**: The embedding is compared against the knowledge corpus using vector similarity search. Our system combines this with BM25 sparse retrieval for hybrid search.

3. **Context Assembly**: Top-scoring documents are retrieved and formatted as context for the LLM. The system targets 85% context window utilization.

4. **Grounded Generation**: The LLM generates a response using the retrieved context. **Citation attribution is at the chunk level**, not document level, ensuring precise source references.

5. **Fallback Behavior**: If no chunks exceed the 0.72 relevance threshold, the system returns "I don't know" rather than hallucinating.

### Key Architecture Requirements

From our [Technical Standards](/pages/llm-integration-standards) and [RAG Architecture](/pages/rag-architecture) pages:

- **Hybrid retrieval**: Dense vector + BM25 for improved recall
- **Cross-encoder reranking**: Top-20 candidates reranked using cross-encoder model
- **Maximum corpus**: 10 million documents per deployment
- **Citation accuracy target**: >90%

RAG significantly reduces hallucination by ensuring all factual claims can be traced to source documents.`,
    citations: [
      { id: 'cit-001', index: 1, sourceId: 'src-002', sourceTitle: 'Technical Standards for LLM Systems v1.0', chunkId: 'chunk-006', snippet: 'Retrieval-Augmented Generation (RAG) systems must implement the following architectural patterns: 1. Hybrid retrieval combining dense vector search with sparse BM25', confidence: 92 },
      { id: 'cit-002', index: 2, sourceId: 'src-002', sourceTitle: 'Technical Standards for LLM Systems v1.0', chunkId: 'chunk-004', snippet: 'LLM systems must be integrated using a layered architecture separating concerns between interface, logic, and data layers.', confidence: 88 },
      { id: 'cit-003', index: 3, sourceId: 'src-005', sourceTitle: 'Q1 2025 Knowledge Base Update', chunkId: 'chunk-010', snippet: 'Parent Document Retrieval: Instead of returning top-k chunks directly, we now retrieve parent documents and re-chunk at query time using the question context.', confidence: 85 },
    ],
    relatedPages: [
      { id: 'page-007', slug: 'rag-architecture', title: 'RAG Architecture', pageType: 'deep_dive', relevanceScore: 95, excerpt: 'Comprehensive guide to RAG architecture including hybrid retrieval, re-ranking, and citation attribution patterns.' },
      { id: 'page-010', slug: 'retrieval-augmented-generation', title: 'Retrieval-Augmented Generation', pageType: 'entity', relevanceScore: 93, excerpt: 'Entity page defining RAG and its benefits for grounded AI responses.' },
    ],
    relatedSources: [
      { id: 'src-002', title: 'Technical Standards for LLM Systems v1.0', sourceType: 'pdf', trustLevel: 'authoritative', relevanceScore: 96 },
      { id: 'src-005', title: 'Q1 2025 Knowledge Base Update', sourceType: 'markdown', trustLevel: 'high', relevanceScore: 88 },
    ],
    confidence: 92,
    isInference: false,
    answeredAt: new Date(Date.now() - 3600000).toISOString(),
  },
  'What are the safety requirements for deploying an LLM?': {
    id: 'ask-002',
    question: 'What are the safety requirements for deploying an LLM?',
    answer: `## Safety Requirements for LLM Deployment

Before any LLM is deployed to production, it must pass the **Safety Evaluation Framework (SEF)** as defined in our [AI Policy & Governance Guidelines v2.1](/sources/src-001).

### Required Evaluation Dimensions

| Dimension | Threshold | Test Dataset |
|-----------|-----------|-------------|
| **Bias Assessment** | ≥ 85% fairness score | 10,000 diverse scenarios |
| **Content Safety** | <0.1% false negatives | Red team adversarial prompts |
| **Citation Accuracy** | >90% | 500 Q&A pairs with known answers |
| **Hallucination Rate** | <5% | Automated fact-checking |
| **PII Detection** | >95% | Multi-type PII dataset |

### Required Processes

1. **Automated Testing**: Full evaluation suite runs 8-12 hours
2. **Red Team Review**: Independent security team conducts adversarial probing (1-2 days)
3. **Human Evaluation**: 500 random response samples reviewed
4. **Report Generation**: Evaluation report with pass/fail status
5. **Escalation**: Critical failures escalate to the AI Safety Board

### Pass Criteria

**A system passes the SEF only if ALL dimensions meet thresholds.** Partial passes are not permitted for production deployment. This is a critical requirement — no exceptions.

### Related Requirements

- All safety reports must be archived in the compliance management system
- [LLM Integration Standards](/pages/llm-integration-standards) requires five quality gates before production
- [Compliance Audit Process](/pages/compliance-audit-process) includes quarterly safety evaluation reviews`,
    citations: [
      { id: 'cit-004', index: 1, sourceId: 'src-001', sourceTitle: 'AI Policy & Governance Guidelines v2.1', chunkId: 'chunk-003', snippet: 'Before any LLM is deployed to production, it must pass the Safety Evaluation Framework. This includes: Bias assessment with minimum 85% fairness score...', confidence: 98 },
      { id: 'cit-005', index: 2, sourceId: 'src-001', sourceTitle: 'AI Policy & Governance Guidelines v2.1', chunkId: 'chunk-003', snippet: 'PII detection rate above 95% for redaction requirements. All safety reports must be archived in the compliance management system.', confidence: 97 },
    ],
    relatedPages: [
      { id: 'page-009', slug: 'safety-evaluation-framework', title: 'Safety Evaluation Framework', pageType: 'deep_dive', relevanceScore: 98, excerpt: 'Detailed Safety Evaluation Framework including all five dimensions and their thresholds.' },
      { id: 'page-001', slug: 'ai-governance-overview', title: 'AI Governance Overview', pageType: 'summary', relevanceScore: 90, excerpt: 'Summary of AI governance framework including safety standards.' },
    ],
    relatedSources: [
      { id: 'src-001', title: 'AI Policy & Governance Guidelines v2.1', sourceType: 'pdf', trustLevel: 'authoritative', relevanceScore: 99 },
      { id: 'src-002', title: 'Technical Standards for LLM Systems v1.0', sourceType: 'pdf', trustLevel: 'authoritative', relevanceScore: 85 },
    ],
    confidence: 96,
    isInference: false,
    answeredAt: new Date(Date.now() - 7200000).toISOString(),
  },
  'How does the document processing pipeline work?': {
    id: 'ask-003',
    question: 'How does the document processing pipeline work?',
    answer: `## Document Processing Pipeline

The document processing pipeline transforms raw documents into knowledge-ready chunks. It consists of **5 stages** defined in our [Internal SOP: Document Processing Workflow](/sources/src-003).

### Stage-by-Stage Breakdown

#### Stage 1: Ingestion
- **Supported formats**: PDF, Markdown, DOCX, TXT
- **File size limit**: 50MB maximum (files exceeding this are rejected)
- **Validation**: MIME type verification and checksum computation

#### Stage 2: Parsing
- **PDF**: PyMuPDF with layout preservation
- **Markdown**: Unified parsing preserving heading hierarchy
- **Extracted metadata**: Page numbers, headings, tables, lists

#### Stage 3: Chunking
Documents are split into semantic chunks using:
- **Primary method**: Heading-based boundaries
- **Fallback**: 512-token sliding window with 64-token overlap
- **Constraint**: Never split code blocks, table rows, or list items

#### Stage 4: Embedding
Each chunk is vectorized:
- **Model**: text-embedding-3-small (1536 dimensions)
- **Storage**: Vector database with source metadata tags

#### Stage 5: QA & Validation
Automated quality checks (any failed chunks → manual review queue, **48h SLA**):
- Chunk completeness: no chunk under 50 tokens
- Semantic coherence: adjacent chunks share entity reference
- Citation extraction: all claims linked to source chunks

### Performance Metrics

- Average processing time: **45 seconds per document**
- Maximum throughput: **200 documents per hour**
- QA failure rate target: **<3%**`,
    citations: [
      { id: 'cit-006', index: 1, sourceId: 'src-003', sourceTitle: 'Internal SOP: Document Processing Workflow', chunkId: 'chunk-007', snippet: 'The document processing workflow follows these stages: Stage 1 — Ingestion... Stage 2 — Parsing... Stage 3 — Chunking... Stage 4 — Embedding... Stage 5 — QA & Validation', confidence: 95 },
      { id: 'cit-007', index: 2, sourceId: 'src-003', sourceTitle: 'Internal SOP: Document Processing Workflow', chunkId: 'chunk-007', snippet: 'Each chunk is embedded using the organization\'s standard embedding model (currently text-embedding-3-small, 1536 dimensions).', confidence: 96 },
    ],
    relatedPages: [
      { id: 'page-004', slug: 'document-processing-pipeline', title: 'Document Processing Pipeline', pageType: 'deep_dive', relevanceScore: 99, excerpt: 'Detailed technical guide to the document processing workflow.' },
    ],
    relatedSources: [
      { id: 'src-003', title: 'Internal SOP: Document Processing Workflow', sourceType: 'markdown', trustLevel: 'high', relevanceScore: 98 },
    ],
    confidence: 95,
    isInference: false,
    answeredAt: new Date(Date.now() - 14400000).toISOString(),
  },
}

export const MOCK_SEARCH_RESULTS: Record<string, SearchResult[]> = {
  'RAG': [
    { id: 'page-007', type: 'page', title: 'RAG Architecture', excerpt: 'Comprehensive guide to Retrieval-Augmented Generation architecture patterns, including hybrid retrieval, re-ranking...', pageSlug: 'rag-architecture', relevanceScore: 96, status: 'published' },
    { id: 'page-010', type: 'page', title: 'Retrieval-Augmented Generation', excerpt: 'Entity page for RAG — a technique that enhances LLM responses by retrieving relevant knowledge...', pageSlug: 'retrieval-augmented-generation', relevanceScore: 94, status: 'published' },
    { id: 'clm-004', type: 'claim', title: 'RAG systems must implement hybrid retrieval', excerpt: 'RAG systems must implement hybrid retrieval combining dense vector search with BM25.', relevanceScore: 88 },
    { id: 'chunk-006', type: 'chunk', title: 'RAG Architecture Standards (chunk)', excerpt: 'Retrieval-Augmented Generation (RAG) systems must implement the following architectural patterns: 1. Hybrid retrieval combining dense vector search with sparse BM25...', sourceId: 'src-002', relevanceScore: 91 },
  ],
  'safety': [
    { id: 'page-009', type: 'page', title: 'Safety Evaluation Framework', excerpt: 'Detailed documentation of the Safety Evaluation Framework — systematic approach to evaluating AI safety...', pageSlug: 'safety-evaluation-framework', relevanceScore: 98, status: 'in_review' },
    { id: 'page-001', type: 'page', title: 'AI Governance Overview', excerpt: 'A comprehensive summary of the AI Policy and Governance Guidelines covering ethical principles, safety standards...', pageSlug: 'ai-governance-overview', relevanceScore: 85, status: 'published' },
  ],
}