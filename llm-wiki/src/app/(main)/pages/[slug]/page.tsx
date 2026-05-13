'use client'
import { useDeferredValue, useEffect, useRef, useState, use, type ClipboardEvent, type DragEvent } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { PageHeader } from '@/components/layout/page-header'
import { StatusBadge } from '@/components/data-display/status-badge'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { ErrorState } from '@/components/data-display/error-state'
import { MarkdownRenderer } from '@/components/data-display/markdown-renderer'
import {
  createHeadingBlock,
  createImageBlock,
  createParagraphBlock,
  displayPageAssetUrl,
  htmlToPageBlocks,
  markdownToPageBlocks,
  normalizePageBlocks,
  pageBlocksToMarkdown,
  type PageBlock,
} from '@/lib/page-blocks'
import { formatDate, formatDateTime, cn } from '@/lib/utils'
import { usePage, usePublishPage, useUnpublishPage, useUpdatePage, usePages } from '@/hooks/use-pages'
import { useAssignPageCollection, useCollections } from '@/hooks/use-collections'
import { useAssessDiagramPage, useDiagrams, useGenerateDiagramFromPage } from '@/hooks/use-diagrams'
import { useAuth } from '@/providers/auth-provider'
import { apiRequest } from '@/services/api-client'
import {
  BookOpen, ChevronLeft, ChevronRight,
  Edit3, AlertTriangle, RefreshCw,
  Layers, Tag, FileText, Link2, CheckCircle,
  PanelLeft, Search, Star, CalendarDays, ListChecks,
  Sparkles, PenSquare, ClipboardList, Wand2, Copy, Check, ImagePlus, Plus, Trash2,
  Heading2, List, ListTodo, Quote, Save, X,
} from 'lucide-react'

type SavedView = 'all' | 'drafts' | 'review' | 'stale' | 'source-linked'

const SAVED_VIEWS: Array<{ id: SavedView; label: string }> = [
  { id: 'all', label: 'All pages' },
  { id: 'drafts', label: 'Drafts' },
  { id: 'review', label: 'In review' },
  { id: 'stale', label: 'Stale' },
  { id: 'source-linked', label: 'Source-linked' },
]

const PAGE_TYPE_LABELS: Record<string, string> = {
  summary: 'Summaries',
  overview: 'Overviews',
  deep_dive: 'Deep dives',
  faq: 'FAQs',
}

const WORKSPACE_INSERTS = [
  { label: 'Summary', content: '\n## Summary\n\n- \n' },
  { label: 'Key points', content: '\n## Key points\n\n- \n' },
  { label: 'Questions', content: '\n## Open questions\n\n- \n' },
  { label: 'Action items', content: '\n## Action items\n\n- [ ] \n' },
  { label: 'Source notes', content: '\n## Source notes\n\n- Source:\n- Why it matters:\n' },
]

type UploadedPageAsset = {
  url: string
  filename: string
  contentType: string
  size: number
}

type AppendableBlockKind = 'paragraph' | 'heading' | 'bullet_list' | 'todo_list' | 'quote'

function listValueToLines(items: string[]) {
  return items.join('\n')
}

function linesToListValue(value: string) {
  return value.split('\n').map(line => line.trim()).filter(Boolean)
}

function todoItemsToText(items: Array<{ text: string; checked: boolean }>) {
  return items.map(item => `- [${item.checked ? 'x' : ' '}] ${item.text}`).join('\n')
}

function textToTodoItems(value: string) {
  return value
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean)
    .map(line => {
      const match = line.match(/^\-\s+\[([xX ])\]\s+(.+)$/)
      if (match) return { checked: match[1].toLowerCase() === 'x', text: match[2] }
      return { checked: false, text: line.replace(/^\-\s+/, '') }
    })
}

function isTextBlock(block: PageBlock): block is Extract<PageBlock, { type: 'heading' | 'paragraph' | 'quote' }> {
  return block.type === 'heading' || block.type === 'paragraph' || block.type === 'quote'
}

export default function PageDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params)
  const [leftPanelOpen, setLeftPanelOpen] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [editBlocks, setEditBlocks] = useState<PageBlock[]>([])
  const [pageSearch, setPageSearch] = useState('')
  const [savedView, setSavedView] = useState<SavedView>('all')
  const [copyState, setCopyState] = useState<'idle' | 'copied'>('idle')
  const [imagePasteState, setImagePasteState] = useState<'idle' | 'pasting' | 'ready' | 'failed'>('idle')
  const [activeBlockId, setActiveBlockId] = useState<string | null>(null)
  const blockInputRefs = useRef<Record<string, HTMLInputElement | HTMLTextAreaElement | null>>({})

  const { data: page, isLoading, isError, error, refetch } = usePage(slug)
  const { data: pagesData } = usePages({ pageSize: 100, sort: 'title' }, { enabled: leftPanelOpen || (page?.relatedPageIds?.length ?? 0) > 0 })
  const { data: collections } = useCollections()
  const assignCollection = useAssignPageCollection()
  const publishMutation = usePublishPage()
  const unpublishMutation = useUnpublishPage()
  const updateMutation = useUpdatePage()
  const generateDiagramMutation = useGenerateDiagramFromPage()
  const { data: bpmAssessment } = useAssessDiagramPage(page?.id ?? '')
  const { data: relatedDiagrams } = useDiagrams({ pageId: page?.id, pageSize: 20 })
  const { hasRole } = useAuth()
  const router = useRouter()
  const deferredPageSearch = useDeferredValue(pageSearch)
  const canEdit = hasRole('editor', 'reviewer', 'admin')
  const pageBlocks = normalizePageBlocks(page?.contentJson ?? markdownToPageBlocks(page?.contentMd))
  const renderedMarkdown = pageBlocksToMarkdown(pageBlocks)
  const editMarkdown = pageBlocksToMarkdown(editBlocks)

  useEffect(() => {
    if (!isEditing || !canEdit || !page?.id) return

    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
        event.preventDefault()
        if (!updateMutation.isPending) {
          updateMutation.mutate({ pageId: page.id, contentMd: editMarkdown, contentJson: normalizePageBlocks(editBlocks) }, { onSuccess: () => setIsEditing(false) })
        }
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [canEdit, editBlocks, editMarkdown, isEditing, page?.id, updateMutation])

  useEffect(() => {
    if (!page?.id) return
    setLeftPanelOpen(page.status !== 'draft')
  }, [page?.id, page?.status])

  useEffect(() => {
    if (!page?.id) return
    setEditBlocks(normalizePageBlocks(page.contentJson ?? markdownToPageBlocks(page.contentMd)))
  }, [page?.id, page?.contentMd, page?.contentJson])

  if (isLoading) return <LoadingSpinner label="Loading page..." />
  if (isError) return <ErrorState message={(error as Error)?.message ?? 'Failed to load page'} onRetry={() => refetch()} />
  if (!page) return <ErrorState message="Page not found" />

  const allPages = pagesData?.data ?? []
  const searchedPages = allPages.filter(navPage => {
    const matchesSearch = [navPage.title, navPage.summary, navPage.slug, ...navPage.tags]
      .join(' ')
      .toLowerCase()
      .includes(deferredPageSearch.trim().toLowerCase())
    const matchesView =
      savedView === 'all' ||
      (savedView === 'drafts' && navPage.status === 'draft') ||
      (savedView === 'review' && navPage.status === 'in_review') ||
      (savedView === 'stale' && navPage.status === 'stale') ||
      (savedView === 'source-linked' && navPage.relatedSourceIds.length > 0)
    return matchesSearch && matchesView
  })
  const pagesByType = searchedPages.reduce<Record<string, typeof allPages>>((groups, navPage) => {
    const key = navPage.pageType || 'summary'
    groups[key] = groups[key] ?? []
    groups[key].push(navPage)
    return groups
  }, {})
  const timelineEvents = page.timelineEvents ?? []
  const glossaryTerms = page.glossaryTerms ?? []
  const backlinkCount = page.backlinks?.length ?? 0
  const totalCitations = page.citations?.length ?? 0
  const collectionName = collections?.find(collection => collection.id === page.collectionId)?.name ?? 'Standalone'
  const authoringPrompts = [
    `Clarify the top 3 claims in ${page.title}.`,
    `What citations are still missing from ${page.title}?`,
    `Turn ${page.title} into a concise internal note.`,
  ]

  const copyMarkdown = async () => {
    try {
      await navigator.clipboard.writeText(isEditing ? editMarkdown : renderedMarkdown)
      setCopyState('copied')
      window.setTimeout(() => setCopyState('idle'), 1800)
    } catch {
      setCopyState('idle')
    }
  }

  const insertIntoEditor = (content: string) => {
    if (!canEdit) return
    if (!isEditing) {
      setEditBlocks(pageBlocks)
      setIsEditing(true)
    }

    const insertedBlocks = markdownToPageBlocks(content)
    setEditBlocks(current => {
      const base = normalizePageBlocks(current)
      const activeIndex = activeBlockId ? base.findIndex(block => block.id === activeBlockId) : -1
      if (activeIndex === -1) return [...base, ...insertedBlocks]
      return [...base.slice(0, activeIndex + 1), ...insertedBlocks, ...base.slice(activeIndex + 1)]
    })
  }

  const insertBlocksAfter = (blockId: string, blocks: PageBlock[]) => {
    if (blocks.length === 0) return
    setEditBlocks(current => {
      const base = normalizePageBlocks(current)
      const index = base.findIndex(block => block.id === blockId)
      if (index === -1) return [...base, ...blocks]
      const target = base[index]
      const shouldReplaceEmptyParagraph = target.type === 'paragraph' && !target.text.trim()
      if (shouldReplaceEmptyParagraph) {
        return [...base.slice(0, index), ...blocks, ...base.slice(index + 1)]
      }
      return [...base.slice(0, index + 1), ...blocks, ...base.slice(index + 1)]
    })
  }

  const uploadPageAsset = async (file: File) => {
    const formData = new FormData()
    const extension = file.type === 'image/jpeg' ? 'jpg' : file.type.split('/')[1] || 'png'
    const safeName = file.name?.trim() || `clipboard-${Date.now()}.${extension}`
    formData.append('file', file, safeName)
    return apiRequest<UploadedPageAsset>('/pages/assets', {
      method: 'POST',
      body: formData,
    })
  }

  const uploadDataImageBlock = async (block: PageBlock): Promise<PageBlock> => {
    if (block.type !== 'image' || !block.url.startsWith('data:image/')) return block
    const response = await fetch(block.url)
    const blob = await response.blob()
    const extension = blob.type === 'image/jpeg' ? 'jpg' : blob.type.split('/')[1] || 'png'
    const file = new File([blob], block.caption || `pasted-image.${extension}`, { type: blob.type || 'image/png' })
    const uploadedAsset = await uploadPageAsset(file)
    return createImageBlock(uploadedAsset.url, block.caption || uploadedAsset.filename)
  }

  const normalizePastedHtmlBlocks = async (blocks: PageBlock[]) => Promise.all(blocks.map(uploadDataImageBlock))

  const handleEditorPaste = (blockId: string) => async (event: ClipboardEvent<HTMLTextAreaElement>) => {
    const html = event.clipboardData.getData('text/html')
    if (html.trim()) {
      const htmlBlocks = htmlToPageBlocks(html)
      if (htmlBlocks.length > 0) {
        event.preventDefault()
        const hasImages = htmlBlocks.some(block => block.type === 'image')
        if (hasImages) setImagePasteState('pasting')
        try {
          const normalizedBlocks = await normalizePastedHtmlBlocks(htmlBlocks)
          insertBlocksAfter(blockId, normalizedBlocks)
          setImagePasteState(hasImages ? 'ready' : 'idle')
        } catch {
          insertBlocksAfter(blockId, htmlBlocks.filter(block => block.type !== 'image' || !block.url.startsWith('data:image/')))
          setImagePasteState('failed')
        } finally {
          window.setTimeout(() => setImagePasteState('idle'), 2200)
        }
        return
      }
    }

    const imageItem = Array.from(event.clipboardData.items).find(item => item.type.startsWith('image/'))
    if (!imageItem) return

    const file = imageItem.getAsFile()
    if (!file) return

    event.preventDefault()
    setImagePasteState('pasting')

    try {
      const uploadedAsset = await uploadPageAsset(file)

      const plainText = event.clipboardData.getData('text/plain').trim()
      setEditBlocks(current => {
        const base = normalizePageBlocks(current)
        const index = base.findIndex(block => block.id === blockId)
        if (index === -1) return [...base, createImageBlock(uploadedAsset.url, uploadedAsset.filename)]

        const next = [...base]
        const target = next[index]
        const imageBlock = createImageBlock(uploadedAsset.url, uploadedAsset.filename)
        if (isTextBlock(target)) {
          const input = blockInputRefs.current[blockId]
          const start = input instanceof HTMLTextAreaElement || input instanceof HTMLInputElement ? input.selectionStart ?? target.text.length : target.text.length
          const end = input instanceof HTMLTextAreaElement || input instanceof HTMLInputElement ? input.selectionEnd ?? start : start
          const insertedText = plainText ? `${plainText}\n` : ''
          next[index] = { ...target, text: `${target.text.slice(0, start)}${insertedText}${target.text.slice(end)}` }
          next.splice(index + 1, 0, imageBlock)
        } else if (plainText) {
          next.splice(index + 1, 0, createParagraphBlock(plainText), imageBlock)
        } else {
          next.splice(index + 1, 0, imageBlock)
        }
        return next
      })
      setImagePasteState('ready')
    } catch {
      setImagePasteState('failed')
    } finally {
      window.setTimeout(() => setImagePasteState('idle'), 2200)
    }
  }

  const handleEditorDrop = (blockId: string) => async (event: DragEvent<HTMLDivElement>) => {
    const imageFiles = Array.from(event.dataTransfer.files).filter(file => file.type.startsWith('image/'))
    if (imageFiles.length === 0) return

    event.preventDefault()
    setActiveBlockId(blockId)
    setImagePasteState('pasting')

    try {
      const uploadedAssets = await Promise.all(imageFiles.map(uploadPageAsset))
      setEditBlocks(current => {
        const base = normalizePageBlocks(current)
        const index = base.findIndex(block => block.id === blockId)
        const imageBlocks = uploadedAssets.map(asset => createImageBlock(asset.url, asset.filename))
        if (index === -1) return [...base, ...imageBlocks]
        return [...base.slice(0, index + 1), ...imageBlocks, ...base.slice(index + 1)]
      })
      setImagePasteState('ready')
    } catch {
      setImagePasteState('failed')
    } finally {
      window.setTimeout(() => setImagePasteState('idle'), 2200)
    }
  }

  const updateBlock = (blockId: string, updater: (block: PageBlock) => PageBlock) => {
    setEditBlocks(current => normalizePageBlocks(current).map(block => (block.id === blockId ? updater(block) : block)))
  }

  const removeBlock = (blockId: string) => {
    setEditBlocks(current => {
      const next = normalizePageBlocks(current).filter(block => block.id !== blockId)
      return next.length ? next : [createParagraphBlock('')]
    })
  }

  const appendBlock = (kind: AppendableBlockKind) => {
    if (kind === 'heading') {
      setEditBlocks(current => [...normalizePageBlocks(current), createHeadingBlock('New section', 2)])
      return
    }
    if (kind === 'bullet_list') {
      setEditBlocks(current => [...normalizePageBlocks(current), { id: `blk-${Date.now()}`, type: 'bullet_list', items: [''] }])
      return
    }
    if (kind === 'todo_list') {
      setEditBlocks(current => [...normalizePageBlocks(current), { id: `blk-${Date.now()}`, type: 'todo_list', items: [{ text: '', checked: false }] }])
      return
    }
    if (kind === 'quote') {
      setEditBlocks(current => [...normalizePageBlocks(current), { id: `blk-${Date.now()}`, type: 'quote', text: '' }])
      return
    }
    setEditBlocks(current => [...normalizePageBlocks(current), createParagraphBlock('')])
  }

  const statusBanner = page.status === 'stale' ? (
    <div className="flex items-center gap-2 border-b border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800">
      <AlertTriangle className="h-4 w-4" />
      <span>This page may contain outdated information. A newer source version is available.</span>
    </div>
  ) : page.status === 'in_review' ? (
    <div className="flex items-center gap-2 border-b border-blue-200 bg-blue-50 px-4 py-2 text-sm text-blue-800">
      <RefreshCw className="h-4 w-4" />
      <span>This page is currently under review.</span>
    </div>
  ) : null

  return (
    <div className="flex h-full flex-col">
      <PageHeader
        title={page.title}
        description={page.summary}
        breadcrumbs={[{ label: 'Pages', href: '/pages' }, { label: page.title }]}
        className="border-b border-border/70 bg-background/95 backdrop-blur"
        actions={
          <div className="flex flex-wrap items-center justify-end gap-2">
            <div className="mr-1 flex items-center gap-1.5">
              <StatusBadge status={page.status} type="page" />
              <StatusBadge status={page.pageType} type="pageType" />
            </div>
            <Link
              href={`/ask?pageId=${encodeURIComponent(page.id)}&pageTitle=${encodeURIComponent(page.title)}&pageSummary=${encodeURIComponent(page.summary ?? '')}`}
              className="flex items-center gap-1.5 rounded-full border border-input px-3 py-1.5 text-sm transition-colors hover:bg-accent"
            >
              <BookOpen className="h-4 w-4" />
              Ask page
            </Link>
            <button
              type="button"
              onClick={copyMarkdown}
              className="flex items-center gap-1.5 rounded-full border border-input px-3 py-1.5 text-sm transition-colors hover:bg-accent"
            >
              {copyState === 'copied' ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              {copyState === 'copied' ? 'Copied' : 'Copy markdown'}
            </button>
            {page.status === 'draft' && (
              <button
                onClick={() => publishMutation.mutate(page.id)}
                disabled={publishMutation.isPending || !canEdit}
                className="flex items-center gap-1.5 rounded-full bg-green-600 px-3 py-1.5 text-sm text-white transition-colors hover:bg-green-700 disabled:opacity-50"
              >
                <CheckCircle className="h-4 w-4" />
                {publishMutation.isPending ? 'Publishing...' : 'Publish'}
              </button>
            )}
            {page.status === 'published' && (
              <button
                onClick={() => unpublishMutation.mutate(page.id)}
                disabled={unpublishMutation.isPending || !canEdit}
                className="flex items-center gap-1.5 rounded-full bg-amber-600 px-3 py-1.5 text-sm text-white transition-colors hover:bg-amber-700 disabled:opacity-50"
              >
                <RefreshCw className="h-4 w-4" />
                {unpublishMutation.isPending ? 'Unpublishing...' : 'Unpublish'}
              </button>
            )}
            <button
              onClick={() => {
                if (!canEdit) return
                setIsEditing(!isEditing)
                if (!isEditing) setEditBlocks(pageBlocks)
              }}
              disabled={!canEdit}
              className="flex items-center gap-1.5 rounded-full border border-input px-3 py-1.5 text-sm transition-colors hover:bg-accent"
            >
              <PenSquare className="h-4 w-4" />
              {isEditing ? 'Close editor' : 'Refine note'}
            </button>
            <button
              onClick={() => {
                if (!canEdit) return
                generateDiagramMutation.mutate(
                  { pageId: page.id, payload: { title: `${page.title} BPM Flow`, objective: page.summary } },
                  { onSuccess: (diagram) => router.push(`/diagrams/${diagram.slug}`) },
                )
              }}
              disabled={generateDiagramMutation.isPending || !canEdit}
              className="flex items-center gap-1.5 rounded-full border border-input px-3 py-1.5 text-sm transition-colors hover:bg-accent disabled:opacity-50"
            >
              <Layers className="h-4 w-4" />
              {generateDiagramMutation.isPending ? 'Generating BPM...' : bpmAssessment?.classification === 'not_recommended' ? 'Generate BPM anyway' : 'Generate BPM draft'}
            </button>
          </div>
        }
      />

      {statusBanner}

      <div className="flex flex-wrap items-center gap-3 border-b border-border bg-muted/20 px-4 py-3 text-xs text-muted-foreground">
        <span className="rounded-full border border-border bg-background px-2.5 py-1">v{page.currentVersion}</span>
        <span className="rounded-full border border-border bg-background px-2.5 py-1">Updated {formatDateTime(page.lastComposedAt)}</span>
        {page.publishedAt && <span className="rounded-full border border-border bg-background px-2.5 py-1">Published {formatDate(page.publishedAt)}</span>}
        <span className="rounded-full border border-border bg-background px-2.5 py-1">{totalCitations} citations</span>
        <span className="rounded-full border border-border bg-background px-2.5 py-1">{page.relatedSourceIds.length} sources</span>
        <span className="rounded-full border border-border bg-background px-2.5 py-1">{page.relatedPageIds.length} related pages</span>
        <span className="rounded-full border border-border bg-background px-2.5 py-1">{backlinkCount} backlinks</span>
        <span className="flex items-center gap-2 rounded-full border border-border bg-background px-2.5 py-1">
          Collection
          <select
            value={page.collectionId ?? ''}
            onChange={event => assignCollection.mutate({ pageId: page.id, collectionId: event.target.value || null })}
            disabled={assignCollection.isPending || !canEdit}
            className="h-7 rounded-md border border-input bg-background px-2 text-xs text-foreground"
          >
            <option value="">Standalone</option>
            {collections?.map(collection => (
              <option key={collection.id} value={collection.id}>{collection.name}</option>
            ))}
          </select>
        </span>
        <span className="ml-auto rounded-full border border-border bg-background px-2.5 py-1">Owner: {page.owner}</span>
      </div>

      <div className="flex flex-1 min-h-0 flex-col lg:flex-row lg:overflow-hidden">
        <div className={cn(
          'border-r border-border bg-card flex-shrink-0 overflow-y-auto transition-all',
          leftPanelOpen ? 'max-h-80 w-full lg:max-h-none lg:w-72' : 'hidden lg:block lg:w-0',
        )}>
          <div className="border-b border-border p-3">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                value={pageSearch}
                onChange={event => setPageSearch(event.target.value)}
                placeholder="Search collection..."
                className="h-8 w-full rounded-md border border-input bg-background pl-8 pr-2 text-sm"
              />
            </div>
            <div className="mt-3">
              <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                <Star className="h-3.5 w-3.5" />
                Saved Views
              </div>
              <div className="flex flex-wrap gap-1.5">
                {SAVED_VIEWS.map(view => (
                  <button
                    key={view.id}
                    onClick={() => setSavedView(view.id)}
                    className={cn(
                      'rounded-full border px-2 py-1 text-xs transition-colors',
                      savedView === view.id
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-border text-muted-foreground hover:text-foreground',
                    )}
                  >
                    {view.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <div className="p-2">
            <div className="mb-2 px-2 text-xs font-medium text-muted-foreground">Collection Tree</div>
            {Object.entries(pagesByType).map(([pageType, navPages]) => (
              <div key={pageType} className="mb-3">
                <div className="flex items-center justify-between px-2 py-1 text-[11px] uppercase tracking-wide text-muted-foreground">
                  <span>{PAGE_TYPE_LABELS[pageType] ?? pageType.replaceAll('_', ' ')}</span>
                  <span>{navPages.length}</span>
                </div>
                {navPages.map(navPage => (
                  <Link
                    key={navPage.id}
                    href={`/pages/${navPage.slug}`}
                    className={cn(
                      'flex items-center gap-2 rounded-md px-2 py-1.5 text-xs transition-colors',
                      navPage.slug === slug
                        ? 'bg-primary/10 font-medium text-primary'
                        : 'text-muted-foreground hover:bg-accent',
                    )}
                  >
                    <FileText className="h-3.5 w-3.5 flex-shrink-0" />
                    <span className="truncate">{navPage.title}</span>
                    <StatusBadge status={navPage.status} type="page" />
                  </Link>
                ))}
              </div>
            ))}
            {searchedPages.length === 0 && (
              <p className="px-2 py-4 text-xs text-muted-foreground">No pages match this saved view.</p>
            )}
          </div>
        </div>

        <button
          onClick={() => setLeftPanelOpen(!leftPanelOpen)}
          className="flex h-8 flex-shrink-0 items-center justify-center border-r border-border bg-muted transition-colors hover:bg-accent lg:h-auto lg:w-4"
          title="Toggle collection tree"
        >
          <PanelLeft className="h-3 w-3 lg:hidden" />
          <span className="hidden lg:inline">{leftPanelOpen ? <ChevronLeft className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}</span>
        </button>

        <div className="min-h-0 flex-1 overflow-y-auto">
          <div className={cn('mx-auto px-5 py-6 md:px-10', isEditing ? 'max-w-4xl' : 'max-w-3xl')}>
            <div className="mb-4">
              <div className="flex flex-wrap gap-1.5">
                {page.tags.map(tag => (
                  <span
                    key={tag}
                    className="inline-flex items-center gap-1 rounded-md border border-border bg-background px-2 py-1 text-xs text-muted-foreground"
                  >
                    <Tag className="h-3 w-3" />
                    {tag}
                  </span>
                ))}
                {page.tags.length === 0 && (
                  <span className="inline-flex items-center gap-1 rounded-md border border-dashed border-border px-2 py-1 text-xs text-muted-foreground">
                    <Tag className="h-3 w-3" />
                    add note tags as the page becomes clearer
                  </span>
                )}
              </div>
            </div>

            {isEditing ? (
              <div className="space-y-6">
                <div className="space-y-3 pb-2">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <span>{collectionName}</span>
                    <span>v{page.currentVersion}</span>
                    <Link
                      href={`/ask?pageId=${encodeURIComponent(page.id)}&pageTitle=${encodeURIComponent(page.title)}&pageSummary=${encodeURIComponent(page.summary ?? '')}`}
                      className="text-primary hover:underline"
                    >
                      Ask AI
                    </Link>
                  </div>
                  <h1 className="text-5xl font-semibold leading-tight tracking-normal">{page.title}</h1>
                </div>

                <div className="sticky top-0 z-10 -mx-2 flex flex-wrap items-center gap-1 border-b border-border/60 bg-background/95 px-2 py-2 backdrop-blur">
                  <button
                    type="button"
                    onClick={() => appendBlock('paragraph')}
                    className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
                    title="Paragraph"
                  >
                    <Plus className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => appendBlock('heading')}
                    className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
                    title="Heading"
                  >
                    <Heading2 className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => appendBlock('bullet_list')}
                    className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
                    title="Bullet list"
                  >
                    <List className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => appendBlock('todo_list')}
                    className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
                    title="Todo list"
                  >
                    <ListTodo className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => appendBlock('quote')}
                    className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
                    title="Quote"
                  >
                    <Quote className="h-4 w-4" />
                  </button>
                  <div className="mx-1 h-5 w-px bg-border" />
                  {WORKSPACE_INSERTS.map(block => (
                    <button
                      key={block.label}
                      type="button"
                      onClick={() => insertIntoEditor(block.content)}
                      className="inline-flex h-8 items-center gap-1 rounded-md px-2 text-xs text-muted-foreground hover:bg-accent hover:text-foreground"
                    >
                      <Wand2 className="h-3.5 w-3.5" />
                      {block.label}
                    </button>
                  ))}
                  <div className="ml-auto flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => setIsEditing(false)}
                      className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
                      title="Cancel"
                    >
                      <X className="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => updateMutation.mutate({ pageId: page.id, contentMd: editMarkdown, contentJson: normalizePageBlocks(editBlocks) }, { onSuccess: () => setIsEditing(false) })}
                      disabled={updateMutation.isPending || !canEdit}
                      className="inline-flex h-8 items-center gap-1.5 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground disabled:opacity-50"
                    >
                      {updateMutation.isPending ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                      Save
                    </button>
                  </div>
                </div>

                <div className="space-y-1 pb-24">
                  <div className="space-y-1">
                    {editBlocks.map(block => (
                      <div
                        key={block.id}
                        onDrop={handleEditorDrop(block.id)}
                        onDragOver={event => event.preventDefault()}
                        className={cn(
                          'group relative -mx-8 rounded-md px-8 py-1 transition-colors hover:bg-muted/30',
                          activeBlockId === block.id && 'bg-muted/20',
                        )}
                      >
                        <div className="absolute -left-1 top-2 hidden items-center gap-1 text-muted-foreground group-hover:flex">
                          <button type="button" onClick={() => removeBlock(block.id)} className="inline-flex h-7 w-7 items-center justify-center rounded-md hover:bg-accent hover:text-foreground" title="Remove block">
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>

                        {block.type === 'heading' && (
                          <div className="flex items-start gap-3">
                            <select
                              value={block.level}
                              onChange={event => updateBlock(block.id, current => current.type === 'heading' ? { ...current, level: Number(event.target.value) } : current)}
                              className="mt-2 h-7 rounded-md border border-transparent bg-transparent px-1 text-xs text-muted-foreground hover:border-input hover:bg-background"
                            >
                              {[1, 2, 3, 4].map(level => <option key={level} value={level}>Heading {level}</option>)}
                            </select>
                            <input
                              ref={node => { blockInputRefs.current[block.id] = node }}
                              value={block.text}
                              onFocus={() => setActiveBlockId(block.id)}
                              onChange={event => updateBlock(block.id, current => current.type === 'heading' ? { ...current, text: event.target.value } : current)}
                              className={cn(
                                'w-full border-0 bg-transparent p-0 font-semibold tracking-normal outline-none placeholder:text-muted-foreground/50',
                                block.level === 1 ? 'text-4xl leading-tight' : block.level === 2 ? 'text-3xl leading-tight' : 'text-2xl leading-snug',
                              )}
                              placeholder="Section title"
                            />
                          </div>
                        )}

                        {block.type === 'paragraph' && (
                          <textarea
                            ref={node => { blockInputRefs.current[block.id] = node }}
                            value={block.text}
                            onFocus={() => setActiveBlockId(block.id)}
                            onChange={event => updateBlock(block.id, current => current.type === 'paragraph' ? { ...current, text: event.target.value } : current)}
                            onPaste={handleEditorPaste(block.id)}
                            className="min-h-9 w-full resize-none overflow-hidden border-0 bg-transparent p-0 text-base leading-7 outline-none placeholder:text-muted-foreground/50"
                            placeholder="Write, paste, or drop an image..."
                          />
                        )}

                        {block.type === 'quote' && (
                          <textarea
                            ref={node => { blockInputRefs.current[block.id] = node }}
                            value={block.text}
                            onFocus={() => setActiveBlockId(block.id)}
                            onChange={event => updateBlock(block.id, current => current.type === 'quote' ? { ...current, text: event.target.value } : current)}
                            onPaste={handleEditorPaste(block.id)}
                            className="min-h-9 w-full resize-none overflow-hidden border-l-2 border-primary/40 bg-transparent pl-4 text-base italic leading-7 outline-none placeholder:text-muted-foreground/50"
                            placeholder="Quoted note..."
                          />
                        )}

                        {block.type === 'bullet_list' && (
                          <textarea
                            value={listValueToLines(block.items)}
                            onFocus={() => setActiveBlockId(block.id)}
                            onChange={event => updateBlock(block.id, current => current.type === 'bullet_list' ? { ...current, items: linesToListValue(event.target.value) } : current)}
                            className="min-h-9 w-full resize-none overflow-hidden border-0 bg-transparent p-0 text-base leading-7 outline-none placeholder:text-muted-foreground/50"
                            placeholder="- One bullet per line"
                          />
                        )}

                        {block.type === 'todo_list' && (
                          <textarea
                            value={todoItemsToText(block.items)}
                            onFocus={() => setActiveBlockId(block.id)}
                            onChange={event => updateBlock(block.id, current => current.type === 'todo_list' ? { ...current, items: textToTodoItems(event.target.value) } : current)}
                            className="min-h-9 w-full resize-none overflow-hidden border-0 bg-transparent p-0 text-base leading-7 outline-none placeholder:text-muted-foreground/50"
                            placeholder="- [ ] Follow up"
                          />
                        )}

                        {block.type === 'image' && (
                          <figure className="my-4 space-y-2">
                            <div className="relative h-[28rem] w-full overflow-hidden rounded-md bg-muted/20">
                              {/* eslint-disable-next-line @next/next/no-img-element */}
                              <img src={displayPageAssetUrl(block.url)} alt={block.caption || block.alt || 'Note image'} className="h-full w-full object-contain" />
                            </div>
                            <input
                              value={block.caption || ''}
                              onChange={event => updateBlock(block.id, current => current.type === 'image' ? { ...current, caption: event.target.value, alt: event.target.value } : current)}
                              className="w-full border-0 bg-transparent px-1 text-center text-sm text-muted-foreground outline-none placeholder:text-muted-foreground/50"
                              placeholder="Caption"
                            />
                          </figure>
                        )}
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
                    <ImagePlus className="h-3.5 w-3.5 text-primary" />
                    {imagePasteState === 'pasting' && <span>Uploading clipboard image...</span>}
                    {imagePasteState === 'ready' && <span>Clipboard text and image were inserted into the draft.</span>}
                    {imagePasteState === 'failed' && <span>Could not upload the clipboard image.</span>}
                    {imagePasteState === 'idle' && <span>Paste or drop images into the note.</span>}
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-8">
                <div className="space-y-4 border-b border-border/70 pb-5">
                  <div className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">Page</div>
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <h2 className="text-4xl font-semibold tracking-tight">{page.title}</h2>
                      {page.summary && <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground">{page.summary}</p>}
                    </div>
                    {canEdit && (
                      <button
                        type="button"
                        onClick={() => {
                          setEditBlocks(pageBlocks)
                          setIsEditing(true)
                        }}
                        className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-xs hover:bg-accent"
                      >
                        <Edit3 className="h-3.5 w-3.5" />
                        Refine this draft
                      </button>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                    <span>In {collectionName}</span>
                    <span>Updated {formatDateTime(page.lastComposedAt)}</span>
                    {page.publishedAt && <span>Published {formatDate(page.publishedAt)}</span>}
                  </div>
                </div>

                <div className="rounded-lg border border-border bg-card px-8 py-8">
                  <MarkdownRenderer content={renderedMarkdown} className="prose-headings:tracking-tight prose-p:text-[15px] prose-p:leading-7" />
                </div>

                {(relatedDiagrams?.data?.length ?? 0) > 0 && (
                  <div className="rounded-lg border border-border bg-card p-5">
                    <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold">
                      <Layers className="h-4 w-4 text-primary" />
                      Linked Process Diagrams
                    </h3>
                    <div className="space-y-2">
                      {relatedDiagrams?.data.map(diagram => (
                        <Link key={diagram.id} href={`/diagrams/${diagram.slug}`} className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm hover:bg-accent">
                          <span>{diagram.title}</span>
                          <StatusBadge status={diagram.status} type="page" />
                        </Link>
                      ))}
                    </div>
                  </div>
                )}

                {bpmAssessment && (
                  <div className="rounded-lg border border-border bg-card p-5">
                    <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
                      <Layers className="h-4 w-4 text-primary" />
                      BPM Suitability
                    </h3>
                    <div className="mb-2 flex items-center gap-2 text-xs">
                      <StatusBadge status={bpmAssessment.classification} type="page" />
                      <span className="text-muted-foreground">Score {Math.round(bpmAssessment.score * 100)}%</span>
                    </div>
                    <p className="mb-3 text-xs text-muted-foreground">
                      Recommended action: {bpmAssessment.recommendedAction.replaceAll('_', ' ')}
                    </p>
                    <ul className="space-y-1 text-xs text-muted-foreground">
                      {bpmAssessment.reasons.map((reason, index) => <li key={index}>- {reason}</li>)}
                    </ul>
                  </div>
                )}

                {timelineEvents.length > 0 && (
                  <div className="rounded-lg border border-border bg-card p-5">
                    <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold">
                      <CalendarDays className="h-4 w-4 text-primary" />
                      Structured Timeline
                    </h3>
                    <div className="space-y-3">
                      {timelineEvents.slice(0, 12).map(event => (
                        <div key={event.id} className="grid grid-cols-[96px_1fr] gap-3 border-l-2 border-primary/30 pl-3">
                          <div className="text-xs font-semibold text-primary">{event.eventDate}</div>
                          <div>
                            <div className="text-sm font-medium">{event.title}</div>
                            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{event.description}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {glossaryTerms.length > 0 && (
                  <div className="rounded-lg border border-border bg-card p-5">
                    <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold">
                      <ListChecks className="h-4 w-4 text-primary" />
                      Structured Glossary
                    </h3>
                    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                      {glossaryTerms.slice(0, 12).map(term => (
                        <div key={term.id} className="rounded-lg border border-border bg-background p-3">
                          <div className="text-sm font-semibold">{term.term}</div>
                          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{term.definition}</p>
                          {term.aliases.length > 0 && (
                            <div className="mt-2 text-[11px] text-muted-foreground">Aliases: {term.aliases.join(', ')}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {page.keyFacts.length > 0 && (
                  <div className="rounded-lg border border-green-200 bg-green-50 p-5">
                    <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      Key Facts
                    </h3>
                    <ul className="space-y-2">
                      {page.keyFacts.map((fact, index) => (
                        <li key={index} className="flex items-start gap-2 text-sm">
                          <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-green-500" />
                          <span>{fact}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {page.relatedPageIds.length > 0 && (
                  <div className="border-t border-border pt-6">
                    <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
                      <Link2 className="h-4 w-4" />
                      Related Pages
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {page.relatedPageIds.map(id => {
                        const relatedPage = allPages.find(candidate => candidate.id === id)
                        return (
                          <Link
                            key={id}
                            href={`/pages/${relatedPage?.slug ?? slug}`}
                            className="rounded-md border border-border px-2.5 py-1 text-xs transition-colors hover:border-primary/50"
                          >
                            {relatedPage?.title ?? id}
                          </Link>
                        )
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
