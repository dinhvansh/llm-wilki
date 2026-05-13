'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { pageService } from '@/services'
import type { PageStatus, PageType } from '@/lib/constants'

export function usePages(params?: {
  page?: number
  pageSize?: number
  status?: PageStatus
  type?: PageType
  search?: string
  sort?: string
  collectionId?: string
}) {
  return useQuery({
    queryKey: ['pages', params],
    queryFn: () => pageService.list(params),
  })
}

export function usePage(slug: string) {
  return useQuery({
    queryKey: ['page', slug],
    queryFn: () => pageService.getBySlug(slug),
    enabled: !!slug,
  })
}

export function useEntityExplorer(params?: { page?: number; pageSize?: number; search?: string; entityType?: string }) {
  return useQuery({
    queryKey: ['entity-explorer', params],
    queryFn: () => pageService.getEntityExplorer(params),
  })
}

export function useTimelineExplorer(params?: { page?: number; pageSize?: number; search?: string }) {
  return useQuery({
    queryKey: ['timeline-explorer', params],
    queryFn: () => pageService.getTimelineExplorer(params),
  })
}

export function useGlossary(params?: { page?: number; pageSize?: number; search?: string }) {
  return useQuery({
    queryKey: ['glossary', params],
    queryFn: () => pageService.getGlossary(params),
  })
}

export function usePageVersions(pageId: string) {
  return useQuery({
    queryKey: ['page-versions', pageId],
    queryFn: () => pageService.getVersions(pageId),
    enabled: !!pageId,
  })
}

export function usePageAudit(pageId: string) {
  return useQuery({
    queryKey: ['page-audit', pageId],
    queryFn: () => pageService.getAudit(pageId),
    enabled: !!pageId,
  })
}

export function usePublishPage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (pageId: string) => pageService.publish(pageId),
    onSuccess: (page) => {
      qc.invalidateQueries({ queryKey: ['pages'] })
      qc.invalidateQueries({ queryKey: ['page', page.slug] })
      qc.invalidateQueries({ queryKey: ['page-audit', page.id] })
    },
  })
}

export function useUnpublishPage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (pageId: string) => pageService.unpublish(pageId),
    onSuccess: (page) => {
      qc.invalidateQueries({ queryKey: ['pages'] })
      qc.invalidateQueries({ queryKey: ['page', page.slug] })
      qc.invalidateQueries({ queryKey: ['page-audit', page.id] })
    },
  })
}

export function useUpdatePage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ pageId, contentMd }: { pageId: string; contentMd: string }) => pageService.update(pageId, contentMd),
    onSuccess: (page) => {
      qc.invalidateQueries({ queryKey: ['pages'] })
      qc.invalidateQueries({ queryKey: ['page', page.slug] })
      qc.invalidateQueries({ queryKey: ['page-versions', page.id] })
      qc.invalidateQueries({ queryKey: ['page-audit', page.id] })
      qc.invalidateQueries({ queryKey: ['review-queue'] })
    },
  })
}

export function useComposePage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: { topic: string; sourceIds?: string[]; contentMd?: string; collectionId?: string; pageType?: string }) => pageService.compose(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pages'] })
    },
  })
}
