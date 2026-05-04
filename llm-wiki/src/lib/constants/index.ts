// === Status enums ===

export const SOURCE_STATUSES = ['uploaded', 'parsing', 'parsed', 'chunked', 'extracted', 'indexed', 'failed'] as const
export type SourceStatus = typeof SOURCE_STATUSES[number]

export const PAGE_STATUSES = ['draft', 'in_review', 'reviewed', 'published', 'stale', 'archived'] as const
export type PageStatus = typeof PAGE_STATUSES[number]

export const PAGE_TYPES = ['summary', 'overview', 'deep_dive', 'entity', 'source_derived', 'faq', 'glossary', 'timeline', 'sop', 'concept', 'issue'] as const
export type PageType = typeof PAGE_TYPES[number]

export const CLAIM_TYPES = ['fact', 'definition', 'process', 'rule', 'example', 'inference', 'requirement', 'condition', 'decision', 'metric', 'risk', 'instruction'] as const
export type ClaimType = typeof CLAIM_TYPES[number]

export const REVIEW_ISSUE_TYPES = ['missing_citation', 'unsupported_claim', 'conflict_detected', 'stale_content', 'low_confidence', 'broken_source_reference'] as const
export type ReviewIssueType = typeof REVIEW_ISSUE_TYPES[number]

export const JOB_STATUSES = ['pending', 'running', 'completed', 'failed', 'canceled'] as const
export type JobStatus = typeof JOB_STATUSES[number]

export const JOB_TYPES = ['ingest', 'chunk', 'extract', 'compose', 'review', 'embed', 'rebuild'] as const
export type JobType = typeof JOB_TYPES[number]

export const ENTITY_TYPES = ['concept', 'person', 'technology', 'organization', 'location', 'event', 'process', 'product'] as const
export type EntityType = typeof ENTITY_TYPES[number]

export const SOURCE_TYPES = ['pdf', 'markdown', 'txt', 'docx', 'url', 'transcript', 'image_ocr', 'confluence', 'notion'] as const
export type SourceType = typeof SOURCE_TYPES[number]

export const TRUST_LEVELS = ['low', 'medium', 'high', 'authoritative'] as const
export type TrustLevel = typeof TRUST_LEVELS[number]

export const RELATION_TYPES = ['parent_child', 'related_to', 'derived_from', 'mentions', 'supersedes', 'depends_on', 'merged_into'] as const
export type RelationType = typeof RELATION_TYPES[number]

export const SEVERITY_LEVELS = ['critical', 'high', 'medium', 'low'] as const
export type SeverityLevel = typeof SEVERITY_LEVELS[number]

export const REVIEW_DECISIONS = ['approved', 'rejected', 'needs_revision', 'escalated'] as const
export type ReviewDecision = typeof REVIEW_DECISIONS[number]

// === Status display configs ===

export const SOURCE_STATUS_CONFIG: Record<SourceStatus, { label: string; color: string }> = {
  uploaded: { label: 'Uploaded', color: 'bg-slate-100 text-slate-700' },
  parsing: { label: 'Parsing', color: 'bg-blue-100 text-blue-700' },
  parsed: { label: 'Parsed', color: 'bg-blue-100 text-blue-700' },
  chunked: { label: 'Chunked', color: 'bg-indigo-100 text-indigo-700' },
  extracted: { label: 'Extracted', color: 'bg-purple-100 text-purple-700' },
  indexed: { label: 'Indexed', color: 'bg-green-100 text-green-700' },
  failed: { label: 'Failed', color: 'bg-red-100 text-red-700' },
}

export const PAGE_STATUS_CONFIG: Record<PageStatus, { label: string; color: string }> = {
  draft: { label: 'Draft', color: 'bg-amber-100 text-amber-800' },
  in_review: { label: 'In Review', color: 'bg-purple-100 text-purple-700' },
  reviewed: { label: 'Reviewed', color: 'bg-blue-100 text-blue-700' },
  published: { label: 'Published', color: 'bg-green-100 text-green-700' },
  stale: { label: 'Stale', color: 'bg-red-100 text-red-700' },
  archived: { label: 'Archived', color: 'bg-gray-100 text-gray-500' },
}

export const PAGE_TYPE_CONFIG: Record<PageType, { label: string; color: string }> = {
  summary: { label: 'Summary', color: 'bg-cyan-100 text-cyan-700' },
  overview: { label: 'Overview', color: 'bg-sky-100 text-sky-700' },
  deep_dive: { label: 'Deep Dive', color: 'bg-violet-100 text-violet-700' },
  entity: { label: 'Entity', color: 'bg-teal-100 text-teal-700' },
  source_derived: { label: 'Source-Derived', color: 'bg-orange-100 text-orange-700' },
  faq: { label: 'FAQ', color: 'bg-lime-100 text-lime-700' },
  glossary: { label: 'Glossary', color: 'bg-emerald-100 text-emerald-700' },
  timeline: { label: 'Timeline', color: 'bg-amber-100 text-amber-700' },
  sop: { label: 'SOP', color: 'bg-blue-100 text-blue-700' },
  concept: { label: 'Concept', color: 'bg-fuchsia-100 text-fuchsia-700' },
  issue: { label: 'Issue', color: 'bg-rose-100 text-rose-700' },
}

export const REVIEW_ISSUE_CONFIG: Record<ReviewIssueType, { label: string; color: string }> = {
  missing_citation: { label: 'Missing Citation', color: 'bg-orange-100 text-orange-700' },
  unsupported_claim: { label: 'Unsupported Claim', color: 'bg-red-100 text-red-700' },
  conflict_detected: { label: 'Conflict', color: 'bg-red-200 text-red-800' },
  stale_content: { label: 'Stale Content', color: 'bg-yellow-100 text-yellow-700' },
  low_confidence: { label: 'Low Confidence', color: 'bg-gray-100 text-gray-700' },
  broken_source_reference: { label: 'Broken Reference', color: 'bg-rose-100 text-rose-700' },
}

export const SEVERITY_CONFIG: Record<SeverityLevel, { label: string; color: string }> = {
  critical: { label: 'Critical', color: 'bg-red-200 text-red-900 font-bold' },
  high: { label: 'High', color: 'bg-orange-100 text-orange-700' },
  medium: { label: 'Medium', color: 'bg-yellow-100 text-yellow-700' },
  low: { label: 'Low', color: 'bg-gray-100 text-gray-600' },
}

export const TRUST_LEVEL_CONFIG: Record<TrustLevel, { label: string; color: string }> = {
  low: { label: 'Low', color: 'bg-gray-100 text-gray-600' },
  medium: { label: 'Medium', color: 'bg-blue-100 text-blue-700' },
  high: { label: 'High', color: 'bg-green-100 text-green-700' },
  authoritative: { label: 'Authoritative', color: 'bg-emerald-100 text-emerald-700' },
}

export const SOURCE_TYPE_CONFIG: Record<SourceType, { label: string }> = {
  pdf: { label: 'PDF' },
  markdown: { label: 'Markdown' },
  txt: { label: 'Text' },
  docx: { label: 'Word' },
  url: { label: 'URL' },
  transcript: { label: 'Transcript' },
  image_ocr: { label: 'Image OCR' },
  confluence: { label: 'Confluence' },
  notion: { label: 'Notion' },
}

export const ENTITY_TYPE_CONFIG: Record<EntityType, { label: string; color: string }> = {
  concept: { label: 'Concept', color: 'bg-purple-100 text-purple-700' },
  person: { label: 'Person', color: 'bg-green-100 text-green-700' },
  technology: { label: 'Technology', color: 'bg-cyan-100 text-cyan-700' },
  organization: { label: 'Organization', color: 'bg-orange-100 text-orange-700' },
  location: { label: 'Location', color: 'bg-pink-100 text-pink-700' },
  event: { label: 'Event', color: 'bg-rose-100 text-rose-700' },
  process: { label: 'Process', color: 'bg-indigo-100 text-indigo-700' },
  product: { label: 'Product', color: 'bg-teal-100 text-teal-700' },
}

export const CLAIM_TYPE_CONFIG: Record<ClaimType, { label: string; color: string }> = {
  fact: { label: 'Fact', color: 'bg-blue-100 text-blue-700' },
  definition: { label: 'Definition', color: 'bg-purple-100 text-purple-700' },
  process: { label: 'Process', color: 'bg-orange-100 text-orange-700' },
  rule: { label: 'Rule', color: 'bg-red-100 text-red-700' },
  example: { label: 'Example', color: 'bg-green-100 text-green-700' },
  inference: { label: 'Inference', color: 'bg-yellow-100 text-yellow-700' },
  requirement: { label: 'Requirement', color: 'bg-rose-100 text-rose-700' },
  condition: { label: 'Condition', color: 'bg-amber-100 text-amber-700' },
  decision: { label: 'Decision', color: 'bg-fuchsia-100 text-fuchsia-700' },
  metric: { label: 'Metric', color: 'bg-cyan-100 text-cyan-700' },
  risk: { label: 'Risk', color: 'bg-red-200 text-red-800' },
  instruction: { label: 'Instruction', color: 'bg-emerald-100 text-emerald-700' },
}
