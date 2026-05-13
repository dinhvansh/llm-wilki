'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { pageService } from '@/services'
import type { PageStatus, PageType } from '@/lib/constants'
import type { PageBlock } from '@/lib/page-blocks'

export function usePages(params?: {
  page?: number
  pageSize?: number
  status?: PageStatus
  type?: PageType
  search?: string
  sort?: string
  collectionId?: string
}, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['pages', params],
    queryFn: () => pageService.list(params),
    enabled: options?.enabled ?? true,
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

export function useEntity(entityId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['entity', entityId],
    queryFn: () => pageService.getEntityById(entityId),
    enabled: (options?.enabled ?? true) && !!entityId,
  })
}

export function useUpdateEntity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ entityId, payload }: { entityId: string; payload: { name: string; entityType: string; description: string; aliases: string[] } }) =>
      pageService.updateEntity(entityId, payload),
    onSuccess: (entity) => {
      qc.invalidateQueries({ queryKey: ['entity-explorer'] })
      qc.invalidateQueries({ queryKey: ['entity', entity.id] })
    },
  })
}

export function useVerifyEntity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ entityId, verificationStatus }: { entityId: string; verificationStatus: string }) =>
      pageService.verifyEntity(entityId, { verificationStatus }),
    onSuccess: (entity) => {
      qc.invalidateQueries({ queryKey: ['entity-explorer'] })
      qc.invalidateQueries({ queryKey: ['entity', entity.id] })
    },
  })
}

export function useArchiveEntity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (entityId: string) => pageService.archiveEntity(entityId),
    onSuccess: (entity) => {
      qc.invalidateQueries({ queryKey: ['entity-explorer'] })
      qc.invalidateQueries({ queryKey: ['entity', entity.id] })
    },
  })
}

export function useRestoreEntity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (entityId: string) => pageService.restoreEntity(entityId),
    onSuccess: (entity) => {
      qc.invalidateQueries({ queryKey: ['entity-explorer'] })
      qc.invalidateQueries({ queryKey: ['entity', entity.id] })
    },
  })
}

export function useMergeEntity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ entityId, targetEntityId }: { entityId: string; targetEntityId: string }) =>
      pageService.mergeEntity(entityId, { targetEntityId }),
    onSuccess: (entity) => {
      qc.invalidateQueries({ queryKey: ['entity-explorer'] })
      qc.invalidateQueries({ queryKey: ['entity', entity.id] })
    },
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

export function usePageVersions(pageId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['page-versions', pageId],
    queryFn: () => pageService.getVersions(pageId),
    enabled: (options?.enabled ?? true) && !!pageId,
  })
}

export function usePageAudit(pageId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['page-audit', pageId],
    queryFn: () => pageService.getAudit(pageId),
    enabled: (options?.enabled ?? true) && !!pageId,
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

export function useArchivePage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (pageId: string) => pageService.archive(pageId),
    onSuccess: (page) => {
      qc.invalidateQueries({ queryKey: ['pages'] })
      qc.invalidateQueries({ queryKey: ['page', page.slug] })
      qc.invalidateQueries({ queryKey: ['page-audit', page.id] })
      qc.invalidateQueries({ queryKey: ['review-queue'] })
    },
  })
}

export function useRestorePage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (pageId: string) => pageService.restore(pageId),
    onSuccess: (page) => {
      qc.invalidateQueries({ queryKey: ['pages'] })
      qc.invalidateQueries({ queryKey: ['page', page.slug] })
      qc.invalidateQueries({ queryKey: ['page-audit', page.id] })
      qc.invalidateQueries({ queryKey: ['review-queue'] })
    },
  })
}

export function useUpdatePage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ pageId, contentMd, contentJson }: { pageId: string; contentMd: string; contentJson?: PageBlock[] }) => pageService.update(pageId, { contentMd, contentJson }),
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
    mutationFn: (payload: { topic: string; sourceIds?: string[]; contentMd?: string; contentJson?: PageBlock[]; collectionId?: string; pageType?: string }) => pageService.compose(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pages'] })
    },
  })
}
