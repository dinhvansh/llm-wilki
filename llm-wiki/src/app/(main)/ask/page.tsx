'use client'
import { useState, useRef, useEffect } from 'react'
import { PageHeader } from '@/components/layout/page-header'
import { EmptyState } from '@/components/data-display/empty-state'
import { MarkdownRenderer } from '@/components/data-display/markdown-renderer'
import { StatusBadge } from '@/components/data-display/status-badge'
import { ConfidenceBar } from '@/components/data-display/confidence-bar'
import { formatRelativeTime } from '@/lib/utils'
import { useAskConversation, useChatSession, useChatSessions, useDeleteChatSession } from '@/hooks/use-ask'
import { useAuth } from '@/providers/auth-provider'
import {
  Send, BookOpen, FileText, Layers,
  Lightbulb, RefreshCw, Plus, Trash2
} from 'lucide-react'
import type { AskResponse } from '@/lib/types'
import Link from 'next/link'

interface Message {
  id: string
  role: 'user' | 'assistant'
  question?: string
  response?: AskResponse
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
  const { hasRole } = useAuth()
  const canDebug = hasRole('admin')
  return (
    <div className="space-y-4">
      {response.interpretedQuery && (
        <div className="rounded-lg border border-border/60 bg-accent/30 px-3 py-2 text-xs">
          <div className="font-medium text-foreground">Interpreted query</div>
          <div className="mt-1 text-muted-foreground">{response.interpretedQuery.standaloneQuery}</div>
          <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
            <span>Intent: {response.interpretedQuery.intent}</span>
            <span>Answer type: {response.interpretedQuery.answerType}</span>
            {response.interpretedQuery.needsClarification && <span>Clarification needed</span>}
          </div>
        </div>
      )}

      {/* Confidence */}
      <div className="flex items-center gap-3">
        <ConfidenceBar score={response.confidence} />
        {response.isInference && (
          <span className="text-xs text-yellow-600 bg-yellow-50 px-2 py-0.5 rounded border border-yellow-200">
            Contains inference
          </span>
        )}
      </div>

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

      {/* Citations */}
      {response.citations.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <BookOpen className="w-3.5 h-3.5" />
            Citations ({response.citations.length})
          </h4>
          <div className="space-y-2">
            {response.citations.map(cit => (
              <Link
                key={cit.id}
                href={`/sources/${cit.sourceId}${cit.chunkId ? `?chunkId=${cit.chunkId}` : ''}`}
                className="flex items-start gap-3 p-3 bg-accent/50 rounded-lg border border-border/50 transition-colors hover:border-primary/50 hover:bg-accent"
              >
                <span className="w-5 h-5 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">
                  {cit.index}
                </span>
                <div className="flex-1">
                  <p className="text-sm leading-relaxed">
                    <HighlightedSnippet text={cit.snippet} query={response.question} />
                  </p>
                  <div className="mt-2 flex items-center gap-2 text-[11px] text-muted-foreground">
                    <span className="font-medium">Source</span>
                    <span className="truncate">{cit.sourceTitle}</span>
                  </div>
                  {(typeof cit.sourceSpanStart === 'number' || cit.matchedText) && (
                    <div className="mt-1 text-[11px] text-muted-foreground">
                      {cit.matchedText && <span className="mr-2">Match: "{cit.matchedText}"</span>}
                      {typeof cit.sourceSpanStart === 'number' && typeof cit.sourceSpanEnd === 'number' && (
                        <span>Span: {cit.sourceSpanStart}-{cit.sourceSpanEnd}</span>
                      )}
                    </div>
                  )}
                </div>
              </Link>
            ))}
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
          </div>
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

export default function AskAIPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const { data: sessions } = useChatSessions()
  const { data: selectedSession } = useChatSession(selectedSessionId)
  const deleteSession = useDeleteChatSession()
  const { ask: askQuestion, isLoading, error } = useAskConversation(selectedSessionId)
  const messagesEndRef = useRef<HTMLDivElement>(null)

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
      setMessages(prev => [...prev, { id: response.id, role: 'assistant', response }])
    } catch {}
  }

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
  }, [selectedSession])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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
        {/* Messages area */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
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
                  {SUGGESTED_QUESTIONS.map((q, i) => (
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
              {messages.map(msg => (
                <div key={msg.id}>
                  {msg.role === 'user' ? (
                    <div className="flex justify-end">
                      <div className="bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-xl">
                        <p className="text-sm">{msg.question}</p>
                      </div>
                    </div>
                  ) : msg.response ? (
                    <div className="bg-card border border-border rounded-xl p-5">
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

              <div ref={messagesEndRef} />
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
