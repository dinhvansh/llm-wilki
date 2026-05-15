'use client'
import { Suspense, useState, useRef, useEffect } from 'react'
import { PageHeader } from '@/components/layout/page-header'
import { EmptyState } from '@/components/data-display/empty-state'
import { MarkdownRenderer } from '@/components/data-display/markdown-renderer'
import { StatusBadge } from '@/components/data-display/status-badge'
import { ConfidenceBar } from '@/components/data-display/confidence-bar'
import { EvidenceCard } from '@/components/evidence/evidence-card'
import { EvidenceDrawer } from '@/components/evidence/evidence-drawer'
import { formatRelativeTime } from '@/lib/utils'
import { useAskConversation, useChatSession, useChatSessions, useDeleteChatSession } from '@/hooks/use-ask'
import { useCollections } from '@/hooks/use-collections'
import { useCreateNote } from '@/hooks/use-notes'
import { useAuth } from '@/providers/auth-provider'
import {
  Send, BookOpen, FileText, Layers,
  Lightbulb, RefreshCw, Plus, Trash2, ShieldCheck, AlertTriangle, Search
} from 'lucide-react'
import type { AskResponse, AskScope } from '@/lib/types'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'

interface Message {
  id: string
  role: 'user' | 'assistant'
  question?: string
  response?: AskResponse
}

function citationHref(citation: AskResponse['citations'][number]): string {
  const params = new URLSearchParams()
  if (citation.chunkId) {
    params.set('chunkId', citation.chunkId)
  }
  if (citation.artifactId) {
    params.set('artifactId', citation.artifactId)
    params.set('tab', 'artifacts')
  }
  const query = params.toString()
  return `/sources/${citation.sourceId}${query ? `?${query}` : ''}`
}

function formatEvidenceLabel(value: string | null | undefined): string {
  return String(value || '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, letter => letter.toUpperCase())
}

function starterPromptsForScope(scope: AskScope | null): string[] {
  if (!scope) return SUGGESTED_QUESTIONS
  if (scope.type === 'source') {
    return [
      `Summarize ${scope.title}.`,
      `What are the most important points in ${scope.title}?`,
      `What should I read first in ${scope.title}?`,
      `What risks or caveats appear in ${scope.title}?`,
    ]
  }
  if (scope.type === 'page') {
    return [
      `What source evidence backs ${scope.title}?`,
      `Summarize ${scope.title}.`,
      `What parts of ${scope.title} may need review?`,
      `What related sources should I inspect next?`,
    ]
  }
  return [
    `Which document in ${scope.title} is most authoritative for this topic?`,
    `Summarize the most important documents in ${scope.title}.`,
    `Compare the top two relevant documents in ${scope.title}.`,
    `What should I read first in ${scope.title}?`,
  ]
}

function scopeFromSearchParams(params: URLSearchParams): AskScope | null {
  const sourceId = params.get('sourceId')
  const pageId = params.get('pageId')
  const collectionId = params.get('collectionId')
  if (sourceId) {
    return {
      type: 'source',
      id: sourceId,
      title: params.get('sourceTitle') || 'Scoped source',
      description: params.get('sourceDescription'),
      strict: true,
      matchedInScope: true,
    }
  }
  if (pageId) {
    return {
      type: 'page',
      id: pageId,
      title: params.get('pageTitle') || 'Scoped page',
      description: params.get('pageSummary'),
      strict: true,
      matchedInScope: true,
    }
  }
  if (collectionId) {
    return {
      type: 'collection',
      id: collectionId,
      title: params.get('collectionTitle') || 'Scoped collection',
      description: params.get('collectionDescription'),
      strict: true,
      matchedInScope: true,
    }
  }
  return null
}

const SUGGESTED_QUESTIONS = [
  'What is RAG and how does it work?',
  'What are the safety requirements for deploying an LLM?',
  'How does the document processing pipeline work?',
  'What are the AI governance principles?',
]

function HighlightedSnippet({ text, query }: { text: string; query: string }) {
  const terms = Array.from(new Set(
    query
      .toLowerCase()
      .split(/\s+/)
      .map(term => term.trim())
      .filter(term => term.length >= 3)
  ))

  if (terms.length === 0) {
    return <>{text}</>
  }

  const escapedTerms = terms.map(term => term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  const pattern = new RegExp(`(${escapedTerms.join('|')})`, 'gi')
  const parts = text.split(pattern)

  return (
    <>
      {parts.map((part, index) => {
        const isMatch = terms.some(term => part.toLowerCase() === term)
        if (!isMatch) return <span key={index}>{part}</span>
        return (
          <mark key={index} className="rounded bg-yellow-100 px-0.5 text-foreground">
            {part}
          </mark>
        )
      })}
    </>
  )
}

function AnswerDisplay({ response }: { response: AskResponse }) {
  const [selectedCitation, setSelectedCitation] = useState<AskResponse['citations'][number] | null>(null)
  const { hasRole } = useAuth()
  const canDebug = hasRole('admin')
  const canSaveNote = hasRole('editor', 'reviewer', 'admin')
  const createNote = useCreateNote()
  const artifactCitations = response.citations.filter(citation => Boolean(citation.artifactType))
  const textCitations = response.citations.filter(citation => !citation.artifactType)
  const verification = response.diagnostics?.answerVerification
  const generation = response.diagnostics?.answerGeneration
  const usedAiModel = generation?.mode === 'llm'

  const renderCitationCard = (cit: AskResponse['citations'][number]) => (
    <EvidenceCard
      key={cit.id}
      index={cit.index}
      title={cit.sourceTitle}
      subtitle={cit.sectionTitle ? `Section: ${cit.sectionTitle}` : undefined}
      snippet={<HighlightedSnippet text={cit.snippet} query={response.question} />}
      href={citationHref(cit)}
      type={cit.artifactType || cit.candidateType}
      confidence={cit.confidence}
      tone={cit.artifactType ? 'artifact' : 'default'}
      meta={[
        cit.citationReason ?? null,
        typeof cit.evidenceGrade?.termCoverage === 'number' ? `Term coverage: ${Math.round(cit.evidenceGrade.termCoverage * 100)}%` : null,
        typeof cit.evidenceGrade?.authority === 'number' ? `Authority: ${Math.round(cit.evidenceGrade.authority * 100)}%` : null,
        cit.matchedText ? `Match: ${cit.matchedText}` : null,
        typeof cit.sourceSpanStart === 'number' && typeof cit.sourceSpanEnd === 'number' ? `Span: ${cit.sourceSpanStart}-${cit.sourceSpanEnd}` : null,
      ]}
      actions={[
        { label: 'Inspect evidence', onClick: () => setSelectedCitation(cit), variant: 'primary' },
        { label: 'Open source', href: citationHref(cit), variant: 'secondary' },
        { label: 'Ask scoped', href: `/ask?sourceId=${encodeURIComponent(cit.sourceId)}&sourceTitle=${encodeURIComponent(cit.sourceTitle)}&prompt=${encodeURIComponent(`Explain this evidence: ${cit.snippet}`)}`, variant: 'secondary' },
        ...(canSaveNote ? [{
          label: createNote.isPending ? 'Saving note...' : 'Save note',
          disabled: createNote.isPending,
          onClick: () =>
            createNote.mutate({
                title: `Note from ${cit.sourceTitle}`,
                body: cit.snippet,
                scope: 'private',
                tags: ['ask-citation'],
                anchors: [
                  {
                    targetType: 'ask_citation',
                    targetId: cit.id,
                    sourceId: cit.sourceId,
                    chunkId: cit.chunkId,
                    artifactId: cit.artifactId,
                    pageId: cit.pageId,
                    sectionKey: cit.sectionKey,
                    citationId: cit.id,
                    snippet: cit.snippet,
                    metadataJson: {
                      question: response.question,
                      answerId: response.id,
                      confidence: cit.confidence,
                      candidateType: cit.candidateType,
                    },
                  },
                ],
              }),
        }] : []),
      ]}
    />
  )

  return (
    <div className="space-y-4">
      <EvidenceDrawer
        open={Boolean(selectedCitation)}
        title={selectedCitation?.sourceTitle ?? 'Evidence'}
        subtitle={selectedCitation?.sectionTitle ? `Section: ${selectedCitation.sectionTitle}` : selectedCitation?.candidateType?.replace(/_/g, ' ')}
        snippet={selectedCitation ? <HighlightedSnippet text={selectedCitation.snippet} query={response.question} /> : null}
        meta={[
          selectedCitation?.citationReason ?? null,
          typeof selectedCitation?.evidenceGrade?.termCoverage === 'number' ? `Term coverage: ${Math.round(selectedCitation.evidenceGrade.termCoverage * 100)}%` : null,
          typeof selectedCitation?.evidenceGrade?.specificity === 'number' ? `Specificity: ${Math.round(selectedCitation.evidenceGrade.specificity * 100)}%` : null,
          typeof selectedCitation?.evidenceGrade?.contradictionRisk === 'number' ? `Contradiction risk: ${Math.round(selectedCitation.evidenceGrade.contradictionRisk * 100)}%` : null,
          selectedCitation?.artifactType ? `Artifact: ${selectedCitation.artifactType}` : null,
          selectedCitation?.chunkId ? `Chunk: ${selectedCitation.chunkId}` : null,
          selectedCitation?.matchedText ? `Match: ${selectedCitation.matchedText}` : null,
          typeof selectedCitation?.sourceSpanStart === 'number' && typeof selectedCitation?.sourceSpanEnd === 'number'
            ? `Source span: ${selectedCitation.sourceSpanStart}-${selectedCitation.sourceSpanEnd}`
            : null,
        ]}
        actions={selectedCitation ? [
          { label: 'Open source detail', href: citationHref(selectedCitation), variant: 'primary' },
          { label: 'Ask scoped', href: `/ask?sourceId=${encodeURIComponent(selectedCitation.sourceId)}&sourceTitle=${encodeURIComponent(selectedCitation.sourceTitle)}&prompt=${encodeURIComponent(`Explain this evidence: ${selectedCitation.snippet}`)}` },
          ...(canSaveNote ? [{
            label: createNote.isPending ? 'Saving note...' : 'Save note',
            disabled: createNote.isPending,
            onClick: () => {
              createNote.mutate({
                title: `Note from ${selectedCitation.sourceTitle}`,
                body: selectedCitation.snippet,
                scope: 'private',
                tags: ['ask-citation'],
                anchors: [{
                  targetType: 'ask_citation',
                  targetId: selectedCitation.id,
                  sourceId: selectedCitation.sourceId,
                  chunkId: selectedCitation.chunkId,
                  artifactId: selectedCitation.artifactId,
                  pageId: selectedCitation.pageId,
                  sectionKey: selectedCitation.sectionKey,
                  citationId: selectedCitation.id,
                  snippet: selectedCitation.snippet,
                  metadataJson: {
                    question: response.question,
                    answerId: response.id,
                    confidence: selectedCitation.confidence,
                    candidateType: selectedCitation.candidateType,
                  },
                }],
              })
            },
          }] : []),
        ] : []}
        onClose={() => setSelectedCitation(null)}
      />
      {response.scope && (
        <div className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-900">
          <div className="font-medium">Scope</div>
          <div className="mt-1">
            {response.scope.type}: {response.scope.title}
          </div>
          {response.scope.description && <div className="mt-1 text-sky-800/80">{response.scope.description}</div>}
          {response.scope.matchedInScope === false && (
            <div className="mt-1 text-sky-800/80">No grounded evidence matched inside this scope.</div>
          )}
        </div>
      )}
      {response.interpretedQuery && (
        <div className="rounded-lg border border-border/60 bg-accent/30 px-3 py-2 text-xs">
          <div className="font-medium text-foreground">Interpreted query</div>
          <div className="mt-1 text-muted-foreground">{response.interpretedQuery.standaloneQuery}</div>
          <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
            <span>Intent: {response.interpretedQuery.intent}</span>
            <span>Answer type: {response.interpretedQuery.answerType}</span>
            {response.interpretedQuery.needsClarification && <span>Clarification needed</span>}
            {response.interpretedQuery.planner && <span>Planner: {response.interpretedQuery.planner.strategy}</span>}
          </div>
          {response.interpretedQuery.planner && response.interpretedQuery.planner.subQueries.length > 0 && (
            <div className="mt-2 space-y-1 text-[11px] text-muted-foreground">
              {response.interpretedQuery.planner.subQueries.map(step => (
                <div key={step.id}>
                  {step.id}. {step.intent} - {step.query}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Confidence */}
      <div className="flex items-center gap-3">
        <ConfidenceBar score={response.confidence} />
        <span
          className={`rounded border px-2 py-0.5 text-xs ${
            usedAiModel
              ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
              : 'border-slate-200 bg-slate-50 text-slate-600'
          }`}
          title={generation?.reason ?? undefined}
        >
          {usedAiModel
            ? `AI model: ${generation?.provider ?? 'provider'}/${generation?.model ?? 'model'}`
            : 'Retrieval fallback'}
        </span>
        {response.isInference && (
          <span className="text-xs text-yellow-600 bg-yellow-50 px-2 py-0.5 rounded border border-yellow-200">
            Contains inference
          </span>
        )}
      </div>

      {verification && (
        <div className={`rounded-lg border px-3 py-2 text-sm ${
          verification.supported
            ? 'border-emerald-200 bg-emerald-50 text-emerald-950'
            : 'border-amber-200 bg-amber-50 text-amber-950'
        }`}>
          <div className="flex items-center gap-2 font-medium">
            {verification.supported ? <ShieldCheck className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
            Evidence verification: {verification.supported ? 'supported' : 'inspect before using'}
          </div>
          <div className="mt-1 text-xs opacity-80">
            Coverage {(verification.coverage * 100).toFixed(0)}% · {verification.citationCount} citation{verification.citationCount === 1 ? '' : 's'} · risk {verification.missingEvidenceRisk}
          </div>
          {verification.notes.length > 0 && (
            <div className="mt-1 text-xs opacity-80">{verification.notes.join(' ')}</div>
          )}
        </div>
      )}

      {/* Answer */}
      <MarkdownRenderer content={response.answer} />

      {response.uncertainty && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          <div className="font-medium">Uncertainty</div>
          <div className="mt-1">{response.uncertainty}</div>
        </div>
      )}

      {response.conflicts && response.conflicts.length > 0 && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-900">
          <div className="font-medium">Source conflicts / priority</div>
          <div className="mt-2 space-y-2">
            {response.conflicts.map((conflict, index) => (
              <div key={`${conflict.summary}-${index}`}>
                <div>{conflict.summary}</div>
                {(conflict.preferredSourceTitle || conflict.competingSourceTitle) && (
                  <div className="mt-1 text-xs">
                    Preferred: {conflict.preferredSourceTitle ?? 'N/A'} | Competing: {conflict.competingSourceTitle ?? 'N/A'}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {response.suggestedPrompts && response.suggestedPrompts.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <Lightbulb className="w-3.5 h-3.5" />
            Suggested Follow-ups
          </h4>
          <div className="flex flex-wrap gap-2">
            {response.suggestedPrompts.map(prompt => (
              <button
                key={`${prompt.category}-${prompt.text}`}
                type="button"
                onClick={() => {
                  const event = new CustomEvent('ask-followup', { detail: prompt.text })
                  window.dispatchEvent(event)
                }}
                className="rounded-full border border-border bg-background px-3 py-1.5 text-xs hover:border-primary/50 hover:bg-accent"
                title={prompt.reason ?? undefined}
              >
                {prompt.text}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Citations */}
      {response.citations.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <BookOpen className="w-3.5 h-3.5" />
            Citations ({response.citations.length})
          </h4>
          <div className="space-y-3">
            {artifactCitations.length > 0 && (
              <div className="rounded-lg border border-sky-200 bg-sky-50/70 p-3">
                <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-sky-900">
                  <BookOpen className="h-3.5 w-3.5" />
                  Artifact Evidence ({artifactCitations.length})
                </div>
                <div className="mb-2 text-xs text-sky-900/80">
                  These citations come from structured multimodal artifacts such as notebook, OCR, table, image, or structure summaries.
                </div>
                <div className="space-y-2">
                  {artifactCitations.map(renderCitationCard)}
                </div>
              </div>
            )}
            {textCitations.length > 0 && (
              <div className="space-y-2">
                {artifactCitations.length > 0 && (
                  <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Text Evidence ({textCitations.length})
                  </div>
                )}
                {textCitations.map(renderCitationCard)}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Related Pages */}
      {response.relatedPages.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5" />
            Related Pages
          </h4>
          <div className="flex gap-2 flex-wrap">
            {response.relatedPages.map(page => (
              <a
                key={page.id}
                href={`/pages/${page.slug}`}
                className="px-3 py-1.5 text-xs border border-border rounded-md hover:border-primary/50 transition-colors"
              >
                <div className="font-medium">{page.title}</div>
                <div className="text-muted-foreground line-clamp-1 mt-0.5">{page.excerpt}</div>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Related Sources */}
      {response.relatedSources.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5" />
            Related Sources
          </h4>
          <div className="flex gap-2 flex-wrap">
            {response.relatedSources.map(source => (
              <div key={source.id} className="flex items-center gap-2 px-3 py-1.5 text-xs border border-border rounded-md">
                <span className="font-medium line-clamp-1">{source.title}</span>
                <StatusBadge status={source.trustLevel} type="trust" />
              </div>
            ))}
          </div>
        </div>
      )}

      {canDebug && response.diagnostics && (
        <div className="rounded-lg border border-border/60 bg-background px-3 py-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Admin Debug</div>
          <div className="mt-2 grid gap-2 text-xs text-muted-foreground">
            <div>Candidate count: {response.diagnostics.candidateCount}</div>
            <div>Retrieval limit: {response.diagnostics.retrievalLimit}</div>
            {response.retrievalDebugId && <div>Debug ID: {response.retrievalDebugId}</div>}
            {response.diagnostics.planning && <div>Planning strategy: {response.diagnostics.planning.strategy}</div>}
          </div>
          {response.diagnostics.planning && response.diagnostics.planning.subQueries.length > 0 && (
            <div className="mt-3 rounded border border-border/50 p-2 text-xs text-muted-foreground">
              <div className="font-medium text-foreground">Planner steps</div>
              <div className="mt-1 space-y-1">
                {response.diagnostics.planning.subQueries.map(step => (
                  <div key={step.id}>
                    {step.id}. {step.intent} ({step.role}) - {step.query}
                  </div>
                ))}
              </div>
            </div>
          )}
          {response.diagnostics.contextCoverage && Object.keys(response.diagnostics.contextCoverage).length > 0 && (
            <div className="mt-3 rounded border border-border/50 p-2 text-xs text-muted-foreground">
              <div className="font-medium text-foreground">Context coverage</div>
              <div className="mt-1 flex flex-wrap gap-2">
                {Object.entries(response.diagnostics.contextCoverage).map(([key, value]) => (
                  <span key={key}>{key}={String(value)}</span>
                ))}
              </div>
            </div>
          )}
          {response.diagnostics.topCandidates.length > 0 && (
            <div className="mt-3 space-y-2">
              {response.diagnostics.topCandidates.slice(0, 5).map(candidate => (
                <div key={`${candidate.candidateType}-${candidate.candidateId}`} className="rounded border border-border/50 p-2 text-xs">
                  <div className="font-medium text-foreground">
                    {candidate.candidateType} {candidate.sourceTitle ? `- ${candidate.sourceTitle}` : ''}
                  </div>
                  {candidate.candidateType === 'artifact_summary' && candidate.sectionTitle && (
                    <div className="mt-1 text-muted-foreground">artifact: {candidate.sectionTitle}</div>
                  )}
                  <div className="mt-1 text-muted-foreground">
                    final={candidate.finalScore ?? '-'} rerank={candidate.rerankScore ?? '-'} lexical={candidate.lexicalScore ?? '-'} vector={candidate.vectorScore ?? '-'} authority={candidate.authorityScore ?? '-'}
                  </div>
                  {candidate.rerankReason && <div className="mt-1 text-muted-foreground">rerank reason: {candidate.rerankReason}</div>}
                  {candidate.excerpt && <div className="mt-1 line-clamp-3 text-muted-foreground">{candidate.excerpt}</div>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function AskAIPageInner() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const [chatSearch, setChatSearch] = useState('')
  const [showAllHistory, setShowAllHistory] = useState(false)
  const [focusedAnswerId, setFocusedAnswerId] = useState<string | null>(null)
  const searchParams = useSearchParams()
  const [activeScope, setActiveScope] = useState<AskScope | null>(null)
  const { data: sessions } = useChatSessions()
  const { data: selectedSession } = useChatSession(selectedSessionId)
  const { data: collections } = useCollections()
  const deleteSession = useDeleteChatSession()
  const { ask: askQuestion, isLoading, error } = useAskConversation(selectedSessionId, {
    sourceId: activeScope?.type === 'source' ? activeScope.id : null,
    collectionId: activeScope?.type === 'collection' ? activeScope.id : null,
    pageId: activeScope?.type === 'page' ? activeScope.id : null,
  })
  const latestAnswerRef = useRef<HTMLDivElement>(null)

  const ask = async (question: string) => {
    if (!question.trim()) return
    const userMsg: Message = { id: `user-${Date.now()}`, role: 'user', question }
    setMessages(prev => [...prev, userMsg])
    setInput('')

    try {
      const response = await askQuestion(question)
      if (!selectedSessionId && response.sessionId) {
        setSelectedSessionId(response.sessionId)
      }
      if (response.scope) {
        setActiveScope(response.scope)
      }
      setMessages(prev => [...prev, { id: response.id, role: 'assistant', response }])
      setFocusedAnswerId(response.id)
      setShowAllHistory(false)
    } catch {}
  }

  useEffect(() => {
    const initialScope = scopeFromSearchParams(searchParams)
    if (initialScope) {
      setActiveScope(initialScope)
    }
    const prompt = searchParams.get('prompt')
    if (prompt && !selectedSessionId && messages.length === 0) {
      setInput(prompt)
    }
  }, [messages.length, searchParams, selectedSessionId])

  useEffect(() => {
    if (!selectedSession) return
    const restoredMessages = selectedSession.messages.reduce<Message[]>((items, message) => {
      if (message.role === 'user') {
        items.push({ id: message.id, role: 'user', question: message.content })
        return items
      }
      if (message.response) {
        items.push({ id: message.id, role: 'assistant', response: message.response })
      }
      return items
    }, [])
    setMessages(restoredMessages)
    setShowAllHistory(false)
    setFocusedAnswerId(null)
    const latestScopedResponse = [...selectedSession.messages]
      .reverse()
      .find(message => message.role === 'assistant' && message.response?.scope)
    if (latestScopedResponse?.response?.scope) {
      setActiveScope(latestScopedResponse.response.scope)
    } else {
      setActiveScope(scopeFromSearchParams(searchParams))
    }
  }, [searchParams, selectedSession])

  useEffect(() => {
    if (!focusedAnswerId) return
    latestAnswerRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [focusedAnswerId])

  useEffect(() => {
    const handler = (event: Event) => {
      const customEvent = event as CustomEvent<string>
      if (customEvent.detail) {
        ask(customEvent.detail)
      }
    }
    window.addEventListener('ask-followup', handler as EventListener)
    return () => window.removeEventListener('ask-followup', handler as EventListener)
  })

  const starterPrompts = starterPromptsForScope(activeScope)
  const normalizedChatSearch = chatSearch.trim().toLowerCase()
  const matchingMessages = normalizedChatSearch
    ? messages.filter(message => {
        const text = message.role === 'user'
          ? message.question ?? ''
          : [
              message.response?.question,
              message.response?.answer,
              message.response?.citations.map(citation => `${citation.sourceTitle} ${citation.snippet}`).join(' '),
            ].filter(Boolean).join(' ')
        return text.toLowerCase().includes(normalizedChatSearch)
      })
    : messages
  const recentLimit = 8
  const visibleMessages = normalizedChatSearch || showAllHistory
    ? matchingMessages
    : matchingMessages.slice(-recentLimit)
  const hiddenMessageCount = Math.max(0, matchingMessages.length - visibleMessages.length)

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Ask AI"
        description="Ask questions about your knowledge base with grounded, cited answers"
        actions={
          <Link
            href="/sources"
            className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-sm hover:bg-accent"
          >
            Upload Source
          </Link>
        }
      />

      <div className="flex-1 overflow-hidden grid grid-cols-1 lg:grid-cols-[280px_1fr]">
        <aside className="hidden lg:flex min-h-0 flex-col border-r border-border bg-card/60">
          <div className="border-b border-border p-3">
            <button
              onClick={() => {
                setSelectedSessionId(null)
                setMessages([])
                setInput('')
                setChatSearch('')
                setShowAllHistory(false)
                setFocusedAnswerId(null)
              }}
              className="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              <Plus className="h-4 w-4" />
              New chat
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {sessions && sessions.length > 0 ? (
              <div className="space-y-1">
                {sessions.map(session => (
                  <div
                    key={session.id}
                    className={`group flex items-start gap-2 rounded-lg p-2 text-left transition-colors ${selectedSessionId === session.id ? 'bg-accent' : 'hover:bg-accent/60'}`}
                  >
                    <button
                      onClick={() => setSelectedSessionId(session.id)}
                      className="min-w-0 flex-1 text-left"
                    >
                      <div className="truncate text-sm font-medium">{session.title}</div>
                      <div className="mt-0.5 truncate text-xs text-muted-foreground">{session.lastMessagePreview ?? `${session.messageCount} messages`}</div>
                      <div className="mt-1 text-[11px] text-muted-foreground">{formatRelativeTime(session.updatedAt)}</div>
                    </button>
                    <button
                      onClick={() => {
                        deleteSession.mutate(session.id)
                        if (selectedSessionId === session.id) {
                          setSelectedSessionId(null)
                          setMessages([])
                          setChatSearch('')
                          setShowAllHistory(false)
                          setFocusedAnswerId(null)
                        }
                      }}
                      className="rounded-md p-1 text-muted-foreground opacity-0 hover:bg-background hover:text-destructive group-hover:opacity-100"
                      title="Delete chat"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="p-3 text-xs text-muted-foreground">No saved chats yet. Ask a question to start one.</p>
            )}
          </div>
        </aside>

        <div className="min-h-0 flex flex-col">
        <div className="border-b border-border bg-background/95 px-6 py-3 backdrop-blur">
          <div className="mx-auto flex max-w-3xl flex-col gap-3">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Conversation view</div>
                <div className="mt-1 text-sm text-foreground">
                  {messages.length > 0
                    ? 'Recent-first mode keeps the layout stable and lets you expand older chat only when needed.'
                    : 'Chat history will stay compact here. Older answers collapse automatically once the conversation grows.'}
                </div>
              </div>
              <div className="rounded-full border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground">
                {messages.length} message{messages.length !== 1 ? 's' : ''}
              </div>
            </div>
            <div className="flex flex-col gap-2 md:flex-row md:items-center">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                <input
                  value={chatSearch}
                  onChange={event => {
                    setChatSearch(event.target.value)
                    setShowAllHistory(true)
                  }}
                  placeholder={messages.length > 0 ? 'Search this conversation...' : 'Search will activate after the first question'}
                  disabled={messages.length === 0}
                  className="h-9 w-full rounded-full border border-input bg-card pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-primary/30 disabled:cursor-not-allowed disabled:opacity-60"
                />
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>{visibleMessages.length}/{matchingMessages.length} shown</span>
                {hiddenMessageCount > 0 && (
                  <button
                    type="button"
                    onClick={() => setShowAllHistory(true)}
                    className="rounded-full border border-border px-3 py-1.5 text-foreground hover:bg-accent"
                  >
                    Show {hiddenMessageCount} older
                  </button>
                )}
                {(showAllHistory || chatSearch) && (
                  <button
                    type="button"
                    onClick={() => {
                      setChatSearch('')
                      setShowAllHistory(false)
                    }}
                    className="rounded-full border border-border px-3 py-1.5 text-foreground hover:bg-accent"
                  >
                    Recent only
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
        {messages.length > 0 && (
          <div className="border-b border-border bg-background/95 px-6 py-3 backdrop-blur">
            <div className="mx-auto max-w-3xl text-xs text-muted-foreground">
              Scroll is now constrained to the conversation panel. New AI answers pin to the top of the latest card instead of forcing the page to jump to the bottom.
            </div>
          </div>
        )}
        {/* Messages area */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
          <div className="mx-auto max-w-3xl">
            <div className="rounded-xl border border-border bg-card/70 p-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Ask scope</div>
                  {activeScope ? (
                    <div className="mt-1">
                      <div className="text-sm font-medium text-foreground">{activeScope.type}: {activeScope.title}</div>
                      {activeScope.description && <div className="text-xs text-muted-foreground">{activeScope.description}</div>}
                    </div>
                  ) : (
                    <div className="mt-1 text-sm text-muted-foreground">Global knowledge base</div>
                  )}
                </div>
                <div className="flex flex-col gap-2 md:items-end">
                  <select
                    value={activeScope?.type === 'collection' ? activeScope.id : ''}
                    onChange={event => {
                      const nextId = event.target.value
                      if (!nextId) {
                        if (activeScope?.type === 'collection') setActiveScope(null)
                        return
                      }
                      const collection = collections?.find(item => item.id === nextId)
                      if (!collection) return
                      setSelectedSessionId(null)
                      setMessages([])
                      setActiveScope({
                        type: 'collection',
                        id: collection.id,
                        title: collection.name,
                        description: collection.description,
                        strict: true,
                        matchedInScope: true,
                      })
                    }}
                    disabled={activeScope?.type === 'source' || activeScope?.type === 'page'}
                    className="h-9 rounded-md border border-input bg-background px-3 text-sm disabled:opacity-50"
                  >
                    <option value="">Global knowledge base</option>
                    {(collections ?? []).map(collection => (
                      <option key={collection.id} value={collection.id}>{collection.name}</option>
                    ))}
                  </select>
                  {activeScope && (
                    <button
                      onClick={() => {
                        setSelectedSessionId(null)
                        setMessages([])
                        setActiveScope(null)
                      }}
                      className="text-xs text-primary hover:underline"
                    >
                      Clear scope
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
          {messages.length === 0 ? (
            <div className="max-w-2xl mx-auto pt-8">
              <EmptyState
                icon="message-square"
                title="Ask about your knowledge base"
                description="Ask questions and get grounded, cited answers from your indexed sources. All answers include citations and related pages."
              />
              <div className="mt-6">
                <p className="text-xs font-medium text-muted-foreground mb-3 uppercase tracking-wider">Suggested Questions</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {starterPrompts.map((q, i) => (
                    <button
                      key={i}
                      onClick={() => ask(q)}
                      disabled={isLoading}
                      className="text-left p-3 rounded-lg border border-border hover:border-primary/50 hover:bg-accent/50 transition-all group"
                    >
                      <div className="flex items-start gap-2">
                        <Lightbulb className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                        <span className="text-sm text-foreground group-hover:text-primary transition-colors">{q}</span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
                  ) : (
            <div className="max-w-3xl mx-auto space-y-6">
              {visibleMessages.length === 0 && normalizedChatSearch ? (
                <div className="rounded-xl border border-dashed border-border bg-card p-6 text-center text-sm text-muted-foreground">
                  No messages match "{chatSearch}".
                </div>
              ) : null}
              {!normalizedChatSearch && hiddenMessageCount > 0 && (
                <div className="sticky top-0 z-10 flex justify-center">
                  <button
                    type="button"
                    onClick={() => setShowAllHistory(true)}
                    className="rounded-full border border-border bg-background px-4 py-2 text-xs shadow-sm hover:bg-accent"
                  >
                    Showing latest {recentLimit} messages. Show {hiddenMessageCount} older messages
                  </button>
                </div>
              )}
              {visibleMessages.map(msg => (
                <div
                  key={msg.id}
                  ref={msg.id === focusedAnswerId ? latestAnswerRef : undefined}
                >
                  {msg.role === 'user' ? (
                    <div className="flex justify-end">
                      <div className="bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-xl">
                        <p className="text-sm">{msg.question}</p>
                      </div>
                    </div>
                  ) : msg.response ? (
                    <div className="bg-card border border-border rounded-xl p-5 scroll-mt-6">
                      <div className="flex items-center gap-2 mb-4 text-xs text-muted-foreground">
                        <div className="w-5 h-5 rounded-full bg-primary/10 flex items-center justify-center">
                          <span className="text-primary font-bold">W</span>
                        </div>
                        <span>LLM Wiki AI</span>
                        <span>•</span>
                        <span>{formatRelativeTime(msg.response.answeredAt)}</span>
                      </div>
                      <AnswerDisplay response={msg.response} />
                    </div>
                  ) : null}
                </div>
              ))}

              {/* Loading indicator */}
              {isLoading && (
                <div className="bg-card border border-border rounded-xl p-5">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Searching knowledge base...</span>
                  </div>
                </div>
              )}

              {/* Error */}
              {error && (
                <div className="bg-destructive/5 border border-destructive/20 rounded-xl p-4">
                  <p className="text-sm text-destructive">{error.message}</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Input area */}
        <div className="border-t border-border bg-card p-4">
          <div className="max-w-3xl mx-auto">
            <div className="mb-3 rounded-lg border border-border bg-background px-4 py-3 text-sm text-muted-foreground">
              Ask box is at the bottom of this page. If your knowledge base is empty, upload documents first in <Link href="/sources" className="font-medium text-primary hover:underline">Sources</Link>.
            </div>
            <form
              onSubmit={e => { e.preventDefault(); ask(input) }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="Ask a question about your knowledge base..."
                disabled={isLoading}
                className="flex-1 h-10 px-4 text-sm bg-background border border-input rounded-full focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={isLoading || !input.trim()}
                className="w-9 h-9 rounded-full bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
            <p className="text-xs text-muted-foreground text-center mt-2">
              Answers are grounded in your knowledge base. Citations are linked to source documents.
            </p>
          </div>
        </div>
        </div>
      </div>
    </div>
  )
}

export default function AskAIPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-muted-foreground">Loading Ask AI...</div>}>
      <AskAIPageInner />
    </Suspense>
  )
}
