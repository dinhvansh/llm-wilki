'use client'
import { useState, type ReactNode } from 'react'
import Link from 'next/link'
import { PageHeader } from '@/components/layout/page-header'
import { StatusBadge } from '@/components/data-display/status-badge'
import { EmptyState } from '@/components/data-display/empty-state'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { ErrorState } from '@/components/data-display/error-state'
import { ConfidenceBar } from '@/components/data-display/confidence-bar'
import { EvidenceCard } from '@/components/evidence/evidence-card'
import { formatRelativeTime, cn } from '@/lib/utils'
import { useReviewQueue, useApproveReview, useRejectReview, useMergeReview, useCreateIssuePageFromReview, useRequestReviewRebuild, useAddReviewComment } from '@/hooks/use-review'
import type { ReviewDiffLine, ReviewItem } from '@/lib/types'
import { useAuth } from '@/providers/auth-provider'
import {
  AlertTriangle, CheckCircle, XCircle, RefreshCw,
  ChevronRight, Filter, ArrowLeftRight, AlertCircle,
  Clock, ShieldAlert, BookOpen, GitMerge, Link2, FileText
} from 'lucide-react'

const ISSUE_TYPE_TABS = [
  { key: '', label: 'All', icon: Filter },
  { key: 'conflict_detected', label: 'Conflicts', icon: AlertCircle },
  { key: 'missing_citation', label: 'Citation Issues', icon: ShieldAlert },
  { key: 'stale_content', label: 'Stale Content', icon: Clock },
  { key: 'unsupported_claim', label: 'Unsupported Claims', icon: AlertTriangle },
] as const

function MetaBadge({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
      {children}
    </span>
  )
}

function DiffViewer({ diffLines }: { diffLines: ReviewDiffLine[] }) {
  return (
    <div className="space-y-0.5">
      {diffLines.map((line, i) => {
        const leftLine = line.oldLineNumber?.toString() ?? ''
        const rightLine = line.newLineNumber?.toString() ?? ''
        if (line.kind === 'modified') {
          return (
            <div key={`diff-${i}`} className="space-y-0.5">
              <div className="grid grid-cols-[40px_40px_1fr] items-start gap-2 px-3 py-1 bg-red-50 text-red-800 border-l-2 border-red-500 font-mono text-xs leading-relaxed">
                <span className="text-muted-foreground">{leftLine}</span>
                <span className="text-muted-foreground" />
                <span>{line.oldText || <em className="text-muted-foreground">empty</em>}</span>
              </div>
              <div className="grid grid-cols-[40px_40px_1fr] items-start gap-2 px-3 py-1 bg-green-50 text-green-800 border-l-2 border-green-500 font-mono text-xs leading-relaxed">
                <span className="text-muted-foreground" />
                <span className="text-muted-foreground">{rightLine}</span>
                <span>{line.newText || <em className="text-muted-foreground">empty</em>}</span>
              </div>
            </div>
          )
        }
        return (
          <div
            key={`line-${i}`}
            className={cn(
              'grid grid-cols-[40px_40px_1fr] items-start gap-2 px-3 py-1 font-mono text-xs leading-relaxed border-l-2',
              line.kind === 'added' && 'bg-green-50 text-green-800 border-green-500',
              line.kind === 'removed' && 'bg-red-50 text-red-800 border-red-500',
              line.kind === 'unchanged' && 'text-muted-foreground border-transparent',
            )}
          >
            <span className="text-muted-foreground">{leftLine}</span>
            <span className="text-muted-foreground">{rightLine}</span>
            <span>
              {line.kind === 'added' ? line.newText : line.kind === 'removed' ? line.oldText : line.newText}
              {!((line.kind === 'added' ? line.newText : line.kind === 'removed' ? line.oldText : line.newText)) && <em className="text-muted-foreground">empty</em>}
            </span>
          </div>
        )
      })}
    </div>
  )
}

export default function ReviewQueuePage() {
  const [issueTab, setIssueTab] = useState<string>('')
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null)
  const [rejectReason, setRejectReason] = useState('')
  const [showRejectForm, setShowRejectForm] = useState(false)
  const [mergeComment, setMergeComment] = useState('')
  const [commentDrafts, setCommentDrafts] = useState<Record<string, string>>({})
  const [mergeTargets, setMergeTargets] = useState<Record<string, string>>({})

  const { data, isLoading, isError, error, refetch } = useReviewQueue({
    issueType: (issueTab || undefined) as any,
  })
  const approveMutation = useApproveReview()
  const rejectMutation = useRejectReview()
  const mergeMutation = useMergeReview()
  const createIssuePageMutation = useCreateIssuePageFromReview()
  const rebuildMutation = useRequestReviewRebuild()
  const addCommentMutation = useAddReviewComment()
  const { hasRole } = useAuth()
  const canReview = hasRole('reviewer', 'admin')
  const canEdit = hasRole('editor', 'reviewer', 'admin')

  const items = data?.data ?? []

  const handleApprove = (id: string) => {
    approveMutation.mutate({ id })
    if (selectedItemId === id) setSelectedItemId(null)
  }

  const handleReject = (id: string) => {
    if (!rejectReason.trim()) return
    rejectMutation.mutate({ id, reason: rejectReason })
    setShowRejectForm(false)
    setRejectReason('')
    if (selectedItemId === id) setSelectedItemId(null)
  }

  const handleMerge = (id: string, fallbackTargetId?: string) => {
    const targetPageId = mergeTargets[id] || fallbackTargetId
    if (!targetPageId) return
    mergeMutation.mutate({ id, targetPageId, comment: mergeComment.trim() || undefined })
    setMergeComment('')
    setMergeTargets(prev => {
      const next = { ...prev }
      delete next[id]
      return next
    })
    if (selectedItemId === id) setSelectedItemId(null)
  }

  const renderReviewSummary = (item: ReviewItem) => {
    const stats = item.changeSet?.stats
    if (!stats) return null
    return (
      <div className="flex items-center gap-2 flex-wrap mt-2">
        {item.changeSet?.reviewLevel && <MetaBadge>{item.changeSet.reviewLevel}</MetaBadge>}
        {item.itemKind && <MetaBadge>{item.itemKind.replaceAll('_', ' ')}</MetaBadge>}
        {item.changeSet?.hasContentChanges ? (
          <>
            {stats.addedLines > 0 && <MetaBadge>+{stats.addedLines} lines</MetaBadge>}
            {stats.removedLines > 0 && <MetaBadge>-{stats.removedLines} lines</MetaBadge>}
            {stats.modifiedLines > 0 && <MetaBadge>{stats.modifiedLines} modified</MetaBadge>}
          </>
        ) : (
          <MetaBadge>No content diff</MetaBadge>
        )}
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        title="Review Queue"
        description="Review and approve AI-generated content before publishing"
        actions={
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">{items.length} items pending</span>
            {items.filter(i => i.severity === 'critical').length > 0 && (
              <span className="flex items-center gap-1 text-red-600 font-medium">
                <AlertTriangle className="w-4 h-4" />
                {items.filter(i => i.severity === 'critical').length} critical
              </span>
            )}
          </div>
        }
      />

      <div className="px-6 border-b border-border">
        <div className="flex gap-1 overflow-x-auto">
          {ISSUE_TYPE_TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => setIssueTab(tab.key)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px whitespace-nowrap',
                issueTab === tab.key ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
            >
              <tab.icon className="w-3.5 h-3.5" />
              {tab.label}
              {tab.key && (data?.data.filter(i => i.issueType === tab.key).length ?? 0) > 0 && (
                <span className="ml-1 text-xs bg-muted px-1.5 py-0.5 rounded-full">
                  {data?.data.filter(i => i.issueType === tab.key).length}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="p-6">
        {isLoading ? <LoadingSpinner label="Loading review queue..." /> :
         isError ? <ErrorState message={(error as Error)?.message ?? 'Failed to load review queue'} onRetry={() => refetch()} /> :
         items.length === 0 ? (
           <EmptyState
             icon="inbox"
             title="Review queue is empty"
             description="All content is up to date. No pending reviews at this time."
           />
         ) : (
           <div className="space-y-4">
             {items.map(item => {
               const pageMatchSuggestions = (item.suggestions ?? []).filter(suggestion => suggestion.type === 'page_match' && suggestion.targetId)
               const selectedMergeTarget = mergeTargets[item.id] || pageMatchSuggestions[0]?.targetId
               return (
               <div
                 key={item.id}
                 className={cn(
                   'bg-card border rounded-lg overflow-hidden transition-all cursor-pointer',
                   selectedItemId === item.id ? 'border-primary ring-1 ring-primary/20' : 'border-border hover:border-primary/50'
                 )}
                 onClick={() => setSelectedItemId(selectedItemId === item.id ? null : item.id)}
               >
                 <div className="p-4">
                   <div className="flex items-start justify-between mb-3">
                     <div className="flex items-start gap-3">
                       <div className={cn(
                         'w-10 h-10 rounded-lg flex items-center justify-center',
                         item.severity === 'critical' ? 'bg-red-100' :
                         item.severity === 'high' ? 'bg-orange-100' :
                         item.severity === 'medium' ? 'bg-yellow-100' : 'bg-gray-100'
                       )}>
                         {item.issueType === 'conflict_detected' ? <ArrowLeftRight className={cn('w-5 h-5', item.severity === 'critical' ? 'text-red-600' : 'text-orange-600')} /> :
                          item.issueType === 'missing_citation' ? <ShieldAlert className="w-5 h-5 text-red-600" /> :
                          item.issueType === 'stale_content' ? <Clock className="w-5 h-5 text-yellow-600" /> :
                          <AlertTriangle className="w-5 h-5 text-orange-600" />}
                       </div>
                       <div>
                         <Link href={`/pages/${item.pageSlug}`} className="font-semibold text-sm hover:text-primary transition-colors" onClick={e => e.stopPropagation()}>
                           {item.pageTitle}
                         </Link>
                         <div className="flex items-center gap-2 mt-1 flex-wrap">
                           <StatusBadge status={item.issueType} type="reviewIssue" />
                           <StatusBadge status={item.severity} type="severity" />
                           <span className="text-xs text-muted-foreground">in {formatRelativeTime(item.createdAt)}</span>
                         </div>
                         {renderReviewSummary(item)}
                       </div>
                     </div>
                     <ConfidenceBar score={item.confidenceScore} className="w-24" />
                   </div>

                   <div className="space-y-1.5 mb-3">
                     {item.issues.map((issue, i) => (
                       <p key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                         <span className="text-red-400 mt-0.5">-</span>
                         {issue.message}
                       </p>
                     ))}
                   </div>

                   {item.evidenceSnippets.length > 0 && (
                     <div className="bg-muted/50 rounded-md p-3 mb-3">
                       <p className="text-xs font-medium text-muted-foreground mb-1">Evidence</p>
                       <p className="text-xs leading-relaxed line-clamp-2 italic">"{item.evidenceSnippets[0].content}"</p>
                       <p className="text-xs text-muted-foreground mt-1">- {item.evidenceSnippets[0].sourceTitle}</p>
                     </div>
                   )}

                   <div className="flex items-center gap-2">
                     <button
                       onClick={(e) => { e.stopPropagation(); handleApprove(item.id) }}
                       disabled={approveMutation.isPending || !canReview}
                       className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 transition-colors"
                     >
                       <CheckCircle className="w-4 h-4" />
                       Approve
                     </button>
                     <button
                       onClick={(e) => { e.stopPropagation(); setSelectedItemId(selectedItemId === item.id ? null : item.id) }}
                       className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-input rounded-md hover:bg-accent transition-colors"
                     >
                       Review Detail
                       <ChevronRight className="w-4 h-4" />
                     </button>
                     {pageMatchSuggestions.length > 0 && (
                       <button
                         onClick={(e) => {
                           e.stopPropagation()
                           handleMerge(item.id, pageMatchSuggestions[0]?.targetId)
                         }}
                         disabled={mergeMutation.isPending || !canReview}
                         className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-input rounded-md hover:bg-accent disabled:opacity-50 transition-colors"
                       >
                         <GitMerge className="w-4 h-4" />
                         Merge
                       </button>
                     )}
                   </div>
                 </div>

                 {selectedItemId === item.id && (
                   <div className="border-t border-border bg-muted/20 p-4">
                     <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                       <div>
                         <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                           <ArrowLeftRight className="w-4 h-4" />
                           Change Set
                         </h4>
                         <div className="grid grid-cols-2 gap-2 mb-3">
                           <div className="bg-card border border-border rounded-lg p-3">
                             <p className="text-xs text-muted-foreground mb-1">Versions</p>
                             <p className="text-sm font-medium">
                               v{item.changeSet?.previousVersion ?? item.previousVersion ?? '-'}
                               {' -> '}
                               v{item.changeSet?.proposedVersion ?? item.previousVersion ?? '-'}
                             </p>
                           </div>
                           <div className="bg-card border border-border rounded-lg p-3">
                             <p className="text-xs text-muted-foreground mb-1">Summary</p>
                             <p className="text-sm font-medium line-clamp-2">{item.changeSet?.summary || item.changeSummary}</p>
                           </div>
                         </div>
                         <div className="bg-card border border-border rounded-lg p-3 space-y-0.5 overflow-y-auto max-h-96">
                           {item.issues.map((issue, i) => (
                             <div key={i} className="bg-orange-50 border border-orange-200 rounded px-3 py-2 mb-2">
                               <p className="text-xs font-medium text-orange-700">{issue.message}</p>
                               <p className="text-xs text-orange-600 mt-1">{issue.evidence}</p>
                             </div>
                           ))}
                           <DiffViewer diffLines={item.changeSet?.diffLines ?? []} />
                         </div>
                       </div>

                       <div>
                         <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
                           <div className="bg-card border border-border rounded-lg p-3">
                             <div className="flex items-center gap-2 mb-2">
                               <FileText className="w-4 h-4 text-muted-foreground" />
                               <p className="text-sm font-semibold">Page Context</p>
                             </div>
                             <p className="text-xs text-muted-foreground">{item.pageContext?.pageType} • {item.pageContext?.status}</p>
                             <p className="text-xs text-muted-foreground mt-1">{item.pageContext?.sourceCount ?? item.sourceIds.length} linked sources</p>
                             <p className="text-xs text-muted-foreground mt-1">{item.pageContext?.relatedEntityIds.length ?? 0} related entities</p>
                           </div>
                           <div className="bg-card border border-border rounded-lg p-3">
                             <p className="text-sm font-semibold mb-2">Available Actions</p>
                             <div className="flex gap-2 flex-wrap">
                               {item.reviewActions?.canApprove && <MetaBadge>approve</MetaBadge>}
                               {item.reviewActions?.canMerge && <MetaBadge>merge</MetaBadge>}
                               {item.reviewActions?.canReject && <MetaBadge>reject</MetaBadge>}
                               {item.reviewActions?.canRequestRebuild && <MetaBadge>rebuild</MetaBadge>}
                             </div>
                           </div>
                         </div>
                         <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                           <BookOpen className="w-4 h-4" />
                           Source Evidence
                         </h4>
                         <div className="space-y-2">
                           {item.evidenceSnippets.map((snippet, i) => (
                             <EvidenceCard
                               key={`${snippet.sourceId}-${snippet.chunkId ?? i}`}
                               index={i + 1}
                               title={snippet.sourceTitle}
                               snippet={<span className="italic">"{snippet.content}"</span>}
                               href={`/sources/${snippet.sourceId}${snippet.chunkId ? `?chunkId=${encodeURIComponent(snippet.chunkId)}` : ''}`}
                               type="review evidence"
                               confidence={snippet.relevance}
                               tone="review"
                               actions={[
                                 { label: 'Open source', href: `/sources/${snippet.sourceId}${snippet.chunkId ? `?chunkId=${encodeURIComponent(snippet.chunkId)}` : ''}` },
                                 { label: 'Ask about evidence', href: `/ask?pageId=${encodeURIComponent(item.pageId)}&pageTitle=${encodeURIComponent(item.pageTitle)}&prompt=${encodeURIComponent(`Review this evidence from ${snippet.sourceTitle}: ${snippet.content}`)}` },
                               ]}
                             />
                           ))}
                           {item.issues.map((issue, i) => (
                             <div key={`ev-${i}`} className="bg-muted/50 rounded-lg p-3">
                               <p className="text-xs font-medium mb-1">{issue.severity} issue evidence:</p>
                               <p className="text-xs text-muted-foreground">{issue.evidence}</p>
                             </div>
                           ))}
                         </div>

                         {(item.suggestions?.length ?? 0) > 0 && (
                           <div className="mt-4">
                             <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                               <GitMerge className="w-4 h-4" />
                               Suggestions
                             </h4>
                            <div className="space-y-2">
                              {item.suggestions?.map((suggestion, i) => (
                                 <label key={`${item.id}-suggestion-${i}`} className="flex items-start gap-3 bg-card border border-border rounded-lg p-3 cursor-pointer">
                                   {suggestion.type === 'page_match' && suggestion.targetId ? (
                                     <input
                                       type="radio"
                                       name={`merge-target-${item.id}`}
                                       checked={selectedMergeTarget === suggestion.targetId}
                                       onChange={() => setMergeTargets(prev => ({ ...prev, [item.id]: suggestion.targetId! }))}
                                       onClick={e => e.stopPropagation()}
                                       className="mt-1"
                                     />
                                   ) : (
                                     <span className="mt-1 w-3 h-3 rounded-full bg-muted" />
                                   )}
                                   <div className="min-w-0 flex-1">
                                     <div className="flex items-center justify-between gap-3">
                                       <div className="flex items-center gap-2 flex-wrap">
                                         <span className="text-sm font-medium">{suggestion.title}</span>
                                         <MetaBadge>{suggestion.type.replaceAll('_', ' ')}</MetaBadge>
                                       </div>
                                       <span className="text-xs text-muted-foreground">{Math.round(suggestion.confidenceScore * 100)}%</span>
                                     </div>
                                     <p className="text-xs text-muted-foreground mt-1">{suggestion.reason}</p>
                                     {suggestion.targetSlug && (
                                       <Link
                                         href={`/pages/${suggestion.targetSlug}`}
                                         className="inline-flex items-center gap-1 text-xs text-primary mt-2"
                                         onClick={e => e.stopPropagation()}
                                       >
                                         Open target page
                                         <ChevronRight className="w-3 h-3" />
                                       </Link>
                                     )}
                                   </div>
                                 </label>
                               ))}
                             </div>
                           </div>
                         )}

                          {(item.backlinks?.length ?? 0) > 0 && (
                           <div className="mt-4">
                             <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                               <Link2 className="w-4 h-4" />
                               Backlinks
                             </h4>
                             <div className="space-y-2">
                               {item.backlinks?.map(backlink => (
                                 <Link
                                   key={`${item.id}-${backlink.id}`}
                                   href={`/pages/${backlink.slug}`}
                                   className="block bg-card border border-border rounded-lg p-3 hover:border-primary/50 transition-colors"
                                   onClick={e => e.stopPropagation()}
                                 >
                                   <div className="flex items-center justify-between gap-3">
                                     <span className="text-sm font-medium">{backlink.title}</span>
                                     <MetaBadge>{backlink.relationType.replaceAll('_', ' ')}</MetaBadge>
                                   </div>
                                 </Link>
                               ))}
                             </div>
                           </div>
                          )}

                         <div className="mt-4">
                           <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                             <BookOpen className="w-4 h-4" />
                             Evidence Actions
                           </h4>
                           <div className="flex flex-wrap gap-2">
                             <Link
                               href={`/ask?pageId=${encodeURIComponent(item.pageId)}&pageTitle=${encodeURIComponent(item.pageTitle)}&prompt=${encodeURIComponent(`What evidence should a reviewer inspect first for ${item.pageTitle}?`)}`}
                               className="rounded-md border border-input px-3 py-1.5 text-xs hover:bg-accent"
                             >
                               Ask this page
                             </Link>
                             {item.sourceIds[0] && (
                               <Link
                                 href={`/sources/${item.sourceIds[0]}`}
                                 className="rounded-md border border-input px-3 py-1.5 text-xs hover:bg-accent"
                               >
                                 Inspect first source
                               </Link>
                             )}
                             {item.evidenceSnippets[0] && (
                               <Link
                                 href={`/ask?pageId=${encodeURIComponent(item.pageId)}&pageTitle=${encodeURIComponent(item.pageTitle)}&prompt=${encodeURIComponent(`Review this evidence from ${item.evidenceSnippets[0].sourceTitle}: ${item.evidenceSnippets[0].content}`)}`}
                                 className="rounded-md border border-input px-3 py-1.5 text-xs hover:bg-accent"
                               >
                                 Ask about top evidence
                               </Link>
                             )}
                           </div>
                         </div>

                         <div className="mt-4">
                           <h4 className="text-sm font-semibold mb-2">Review Comments</h4>
                           <div className="space-y-2">
                             {(item.comments ?? []).map(comment => (
                               <div key={comment.id} className="rounded-lg border border-border bg-card p-3">
                                 <div className="flex items-center justify-between gap-2">
                                   <span className="text-xs font-medium">{comment.actor}</span>
                                   <span className="text-[11px] text-muted-foreground">{formatRelativeTime(comment.createdAt)}</span>
                                 </div>
                                 <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{comment.comment}</p>
                               </div>
                             ))}
                             {!(item.comments ?? []).length && (
                               <p className="text-xs text-muted-foreground">No review comments yet.</p>
                             )}
                           </div>
                           <div className="mt-3 flex flex-col gap-2">
                             <textarea
                               value={commentDrafts[item.id] ?? ''}
                               onChange={event => setCommentDrafts(current => ({ ...current, [item.id]: event.target.value }))}
                               onClick={event => event.stopPropagation()}
                               placeholder="Add a reviewer note or evidence handoff..."
                               className="min-h-20 rounded-md border border-input bg-background px-3 py-2 text-sm"
                             />
                             <div className="flex justify-end">
                               <button
                                 onClick={event => {
                                   event.stopPropagation()
                                   const comment = (commentDrafts[item.id] ?? '').trim()
                                   if (!comment) return
                                   addCommentMutation.mutate({ id: item.id, comment })
                                   setCommentDrafts(current => ({ ...current, [item.id]: '' }))
                                 }}
                                 disabled={addCommentMutation.isPending || !canEdit}
                                 className="rounded-md border border-input px-3 py-1.5 text-sm hover:bg-accent disabled:opacity-50"
                               >
                                 Add comment
                               </button>
                             </div>
                           </div>
                         </div>

                         <div className="mt-4 pt-4 border-t border-border space-y-3">
                           {showRejectForm ? (
                             <div className="space-y-2">
                               <input
                                 type="text"
                                 placeholder="Reason for rejection..."
                                 value={rejectReason}
                                 onChange={e => setRejectReason(e.target.value)}
                                 className="w-full h-9 px-3 text-sm border border-input rounded-md"
                                 onClick={e => e.stopPropagation()}
                               />
                               <div className="flex gap-2">
                                 <button
                                   onClick={(e) => { e.stopPropagation(); handleReject(item.id) }}
                                   disabled={!rejectReason.trim() || rejectMutation.isPending || !canReview}
                                   className="px-3 py-1.5 text-sm bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
                                 >
                                   {rejectMutation.isPending ? 'Rejecting...' : 'Confirm Reject'}
                                 </button>
                                 <button
                                   onClick={(e) => { e.stopPropagation(); setShowRejectForm(false) }}
                                   className="px-3 py-1.5 text-sm border border-input rounded-md hover:bg-accent"
                                 >
                                   Cancel
                                 </button>
                               </div>
                             </div>
                           ) : (
                             <div className="space-y-3">
                               {pageMatchSuggestions.length > 0 && (
                                 <div className="space-y-2">
                                   <input
                                     type="text"
                                     placeholder="Optional merge note..."
                                     value={mergeComment}
                                     onChange={e => setMergeComment(e.target.value)}
                                     className="w-full h-9 px-3 text-sm border border-input rounded-md"
                                     onClick={e => e.stopPropagation()}
                                   />
                                   <button
                                     onClick={(e) => {
                                       e.stopPropagation()
                                       handleMerge(item.id, pageMatchSuggestions[0]?.targetId)
                                     }}
                                    disabled={!selectedMergeTarget || mergeMutation.isPending || !canReview}
                                    className="flex items-center gap-1.5 px-4 py-2 text-sm border border-input rounded-md hover:bg-accent transition-colors disabled:opacity-50"
                                  >
                                     <GitMerge className="w-4 h-4" />
                                     {mergeMutation.isPending ? 'Merging...' : 'Merge Into Suggested Page'}
                                   </button>
                                 </div>
                               )}
                               <div className="flex gap-2">
                               <button
                                 onClick={(e) => { e.stopPropagation(); handleApprove(item.id) }}
                                 disabled={!canReview}
                                 className="flex items-center gap-1.5 px-4 py-2 text-sm bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
                               >
                                 <CheckCircle className="w-4 h-4" />
                                 Approve & Publish
                               </button>
                               <button
                                 onClick={(e) => { e.stopPropagation(); setShowRejectForm(true) }}
                                 disabled={!canReview}
                                 className="flex items-center gap-1.5 px-4 py-2 text-sm bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
                               >
                                 <XCircle className="w-4 h-4" />
                                 Reject
                               </button>
                               <button
                                 onClick={(e) => {
                                   e.stopPropagation()
                                   createIssuePageMutation.mutate(item.id)
                                 }}
                                 disabled={createIssuePageMutation.isPending || !canEdit}
                                 className="flex items-center gap-1.5 px-4 py-2 text-sm border border-input rounded-md hover:bg-accent transition-colors disabled:opacity-50"
                               >
                                 <FileText className="w-4 h-4" />
                                 {createIssuePageMutation.isPending ? 'Creating...' : 'Create Issue Page'}
                               </button>
                               <button
                                 onClick={(e) => {
                                   e.stopPropagation()
                                   const sourceId = item.sourceIds[0]
                                   if (sourceId) rebuildMutation.mutate(sourceId)
                                 }}
                                 disabled={!item.sourceIds[0] || rebuildMutation.isPending || !canEdit}
                                 className="flex items-center gap-1.5 px-4 py-2 text-sm border border-input rounded-md hover:bg-accent transition-colors disabled:opacity-50"
                               >
                                 <RefreshCw className="w-4 h-4" />
                                 {rebuildMutation.isPending ? 'Rebuilding...' : 'Request Rebuild'}
                               </button>
                               </div>
                             </div>
                           )}
                         </div>
                       </div>
                     </div>
                   </div>
                 )}
               </div>
               )
             })}
           </div>
         )}
      </div>
    </div>
  )
}
