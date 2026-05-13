'use client'
import { useEffect, useState } from 'react'
import { PageHeader } from '@/components/layout/page-header'
import { StatusBadge } from '@/components/data-display/status-badge'
import { EmptyState } from '@/components/data-display/empty-state'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { ErrorState } from '@/components/data-display/error-state'
import { formatRelativeTime } from '@/lib/utils'
import { useArchiveSourceAction, useIngestTextSource, useIngestUrlSource, useRestoreSourceAction, useSources, useUploadSource } from '@/hooks/use-sources'
import { useCollections } from '@/hooks/use-collections'
import { SOURCE_TYPE_CONFIG } from '@/lib/constants'
import type { SourceType } from '@/lib/constants'
import Link from 'next/link'
import { Upload, Search, Eye, Link as LinkIcon, FileText, RefreshCw, Trash2 } from 'lucide-react'
import { Input } from '@/components/ui/input'

export default function SourcesPage() {
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<SourceType | ''>('')
  const [statusFilter, setStatusFilter] = useState('')
  const [collectionFilter, setCollectionFilter] = useState('')
  const [uploadCollectionId, setUploadCollectionId] = useState('')
  const [inputMode, setInputMode] = useState<'file' | 'url' | 'text'>('file')
  const [urlValue, setUrlValue] = useState('')
  const [urlTitle, setUrlTitle] = useState('')
  const [textTitle, setTextTitle] = useState('')
  const [textContent, setTextContent] = useState('')
  const [textSourceType, setTextSourceType] = useState<'txt' | 'transcript'>('txt')
  const { data: collections } = useCollections()
  const { data, isLoading, isError, error, refetch } = useSources({
    search: search || undefined,
    type: typeFilter || undefined,
    status: (statusFilter as any) || undefined,
    collectionId: collectionFilter || undefined,
  })
  const uploadMutation = useUploadSource()
  const urlMutation = useIngestUrlSource()
  const textMutation = useIngestTextSource()
  const archiveMutation = useArchiveSourceAction()
  const restoreMutation = useRestoreSourceAction()

  useEffect(() => {
    const collectionId = new URLSearchParams(window.location.search).get('collectionId') ?? ''
    setCollectionFilter(collectionId)
    setUploadCollectionId(collectionId)
  }, [])

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      try {
        await uploadMutation.mutateAsync({ file, collectionId: uploadCollectionId || undefined })
      } catch (err) {
        // Error handled by mutation state
      }
      e.target.value = ''
    }
  }

  const handleUrlSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    await urlMutation.mutateAsync({
      url: urlValue,
      title: urlTitle || undefined,
      collectionId: uploadCollectionId || undefined,
    })
    setUrlValue('')
    setUrlTitle('')
  }

  const handleTextSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    await textMutation.mutateAsync({
      title: textTitle,
      content: textContent,
      sourceType: textSourceType,
      collectionId: uploadCollectionId || undefined,
    })
    setTextTitle('')
    setTextContent('')
  }

  const sources = data?.data ?? []

  const handleSourceTrashToggle = async (sourceId: string, archived: boolean) => {
    if (archived) {
      await restoreMutation.mutateAsync(sourceId)
      return
    }
    await archiveMutation.mutateAsync(sourceId)
  }

  return (
    <div>
      <PageHeader
        title="Sources"
        description="Manage your knowledge base source documents"
        actions={
          <div className="flex items-center gap-2">
            <Link
              href="/ask"
              className="flex items-center gap-2 px-3 py-1.5 text-sm border border-border rounded-md hover:bg-accent transition-colors"
            >
              Ask AI
            </Link>
            <select
              value={uploadCollectionId}
              onChange={event => setUploadCollectionId(event.target.value)}
              className="h-8 px-2 text-sm border border-input bg-background rounded-md"
            >
              <option value="">Upload standalone</option>
              {collections?.map(collection => (
                <option key={collection.id} value={collection.id}>{collection.name}</option>
              ))}
            </select>
          </div>
        }
      />

      <div className="p-6 space-y-4">
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="mb-4 flex flex-wrap items-center gap-2">
            {[
              { key: 'file', label: 'File', icon: Upload },
              { key: 'url', label: 'URL', icon: LinkIcon },
              { key: 'text', label: 'Text', icon: FileText },
            ].map(item => {
              const Icon = item.icon
              return (
                <button
                  key={item.key}
                  onClick={() => setInputMode(item.key as typeof inputMode)}
                  className={`flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm transition-colors ${inputMode === item.key ? 'border-primary bg-primary text-primary-foreground' : 'border-border hover:bg-accent'}`}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </button>
              )
            })}
          </div>

          {inputMode === 'file' && (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-muted-foreground">
                Supported: <span className="font-medium text-foreground">.md, .txt, .pdf, .docx, .png, .jpg, .jpeg, .webp, .tif, .tiff</span>. Image files are parsed through Docling OCR with Tesseract `eng+vie` in the Docker stack.
              </p>
              <label className="flex items-center gap-2 px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md cursor-pointer hover:bg-primary/90 transition-colors">
                <Upload className="w-4 h-4" />
                {uploadMutation.isPending ? 'Uploading...' : 'Upload File'}
                <input type="file" className="hidden" accept=".pdf,.md,.txt,.docx,.png,.jpg,.jpeg,.webp,.tif,.tiff" onChange={handleFileChange} />
              </label>
            </div>
          )}

          {inputMode === 'url' && (
            <form onSubmit={handleUrlSubmit} className="grid gap-3 md:grid-cols-[1fr_240px_auto]">
              <Input value={urlValue} onChange={event => setUrlValue(event.target.value)} placeholder="https://example.com/article" className="h-9" />
              <Input value={urlTitle} onChange={event => setUrlTitle(event.target.value)} placeholder="Optional title" className="h-9" />
              <button disabled={urlMutation.isPending || !urlValue.trim()} className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
                {urlMutation.isPending ? 'Fetching...' : 'Ingest URL'}
              </button>
            </form>
          )}

          {inputMode === 'text' && (
            <form onSubmit={handleTextSubmit} className="space-y-3">
              <div className="grid gap-3 md:grid-cols-[1fr_180px]">
                <Input value={textTitle} onChange={event => setTextTitle(event.target.value)} placeholder="Source title" className="h-9" />
                <select value={textSourceType} onChange={event => setTextSourceType(event.target.value as 'txt' | 'transcript')} className="h-9 rounded-md border border-input bg-background px-3 text-sm">
                  <option value="txt">Text paste</option>
                  <option value="transcript">Transcript</option>
                </select>
              </div>
              <textarea
                value={textContent}
                onChange={event => setTextContent(event.target.value)}
                placeholder="Paste text or transcript content..."
                className="min-h-32 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
              <div className="flex items-center justify-between gap-3">
                <span className="text-xs text-muted-foreground">{textContent.length} characters</span>
                <button disabled={textMutation.isPending || !textTitle.trim() || textContent.trim().length < 20} className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
                  {textMutation.isPending ? 'Queueing...' : 'Ingest Text'}
                </button>
              </div>
            </form>
          )}

          {(uploadMutation.isError || urlMutation.isError || textMutation.isError) && (
            <p className="mt-3 text-sm text-red-600">
              {((uploadMutation.error || urlMutation.error || textMutation.error) as Error)?.message ?? 'Source ingest failed'}
            </p>
          )}
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
            <Input
              placeholder="Search sources..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="pl-8 h-9"
            />
          </div>
          <select
            value={typeFilter}
            onChange={e => setTypeFilter(e.target.value as SourceType | '')}
            className="h-9 px-3 text-sm border border-input bg-background rounded-md"
          >
            <option value="">All Types</option>
            {Object.entries(SOURCE_TYPE_CONFIG).map(([k, v]) => (
              <option key={k} value={k}>{v.label}</option>
            ))}
          </select>
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="h-9 px-3 text-sm border border-input bg-background rounded-md"
          >
            <option value="">All Statuses</option>
            <option value="indexed">Indexed</option>
            <option value="extracted">Extracted</option>
            <option value="failed">Failed</option>
          </select>
          <select
            value={collectionFilter}
            onChange={e => setCollectionFilter(e.target.value)}
            className="h-9 px-3 text-sm border border-input bg-background rounded-md"
          >
            <option value="">All Collections</option>
            <option value="standalone">Standalone</option>
            {collections?.map(collection => (
              <option key={collection.id} value={collection.id}>{collection.name}</option>
            ))}
          </select>
          <span className="text-xs text-muted-foreground">{sources.length} source{sources.length !== 1 ? 's' : ''}</span>
        </div>

        {/* Table */}
        {isLoading ? <LoadingSpinner /> :
         isError ? <ErrorState message={(error as Error)?.message ?? 'Failed to load sources'} onRetry={() => refetch()} /> :
         sources.length === 0 ? <EmptyState icon="database" title="No sources found" description={search ? "Try adjusting your search or filters." : "Upload your first source document to get started."} /> :
         (
          <div className="bg-card border border-border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Title</th>
                  <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Type</th>
                  <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Status</th>
                  <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Trust</th>
                  <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Collection</th>
                  <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Uploaded</th>
                  <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">By</th>
                  <th className="px-4 py-2.5"></th>
                </tr>
              </thead>
              <tbody>
                {sources.map(source => (
                  <tr key={source.id} className="border-b border-border last:border-0 hover:bg-accent/50 transition-colors">
                    <td className="px-4 py-3">
                      <div className="font-medium">{source.title}</div>
                      {source.description && <div className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{source.description}</div>}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={source.sourceType} type="source" />
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={source.parseStatus} type="source" />
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={source.trustLevel} type="trust" />
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {collections?.find(collection => collection.id === source.collectionId)?.name ?? 'Standalone'}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {formatRelativeTime(source.uploadedAt)}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {source.createdBy}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => handleSourceTrashToggle(source.id, Boolean(source.metadataJson?.archived))}
                          disabled={archiveMutation.isPending || restoreMutation.isPending}
                          className="inline-flex items-center gap-1 rounded-full border border-border px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-50"
                        >
                          {Boolean(source.metadataJson?.archived) ? <RefreshCw className="h-3.5 w-3.5" /> : <Trash2 className="h-3.5 w-3.5" />}
                          {Boolean(source.metadataJson?.archived) ? 'Restore' : 'Trash'}
                        </button>
                        <Link href={`/sources/${source.id}`} className="flex items-center gap-1 text-xs text-primary hover:underline">
                          <Eye className="w-3.5 h-3.5" /> View
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
         )}
      </div>
    </div>
  )
}
