'use client'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { diagramService } from '@/services'

export function useDiagrams(params?: { page?: number; pageSize?: number; status?: string; search?: string; collectionId?: string; pageId?: string; sourceId?: string }, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['diagrams', params],
    queryFn: () => diagramService.list(params),
    enabled: options?.enabled ?? true,
  })
}

export function useDiagram(slug: string) {
  return useQuery({
    queryKey: ['diagram', slug],
    queryFn: () => diagramService.getBySlug(slug),
    enabled: !!slug,
  })
}

export function useAssessDiagramPage(pageId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['diagram-assess-page', pageId],
    queryFn: () => diagramService.assessPage(pageId),
    enabled: (options?.enabled ?? true) && !!pageId,
  })
}

export function useAssessDiagramSource(sourceId: string) {
  return useQuery({
    queryKey: ['diagram-assess-source', sourceId],
    queryFn: () => diagramService.assessSource(sourceId),
    enabled: !!sourceId,
  })
}

export function useDiagramVersions(diagramId: string) {
  return useQuery({
    queryKey: ['diagram-versions', diagramId],
    queryFn: () => diagramService.getVersions(diagramId),
    enabled: !!diagramId,
  })
}

export function useDiagramAudit(diagramId: string) {
  return useQuery({
    queryKey: ['diagram-audit', diagramId],
    queryFn: () => diagramService.getAudit(diagramId),
    enabled: !!diagramId,
  })
}

export function useCreateDiagram() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: diagramService.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['diagrams'] })
    },
  })
}

export function useGenerateDiagramFromPage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ pageId, payload }: { pageId: string; payload?: { title?: string; objective?: string } }) =>
      diagramService.generateFromPage(pageId, payload),
    onSuccess: (diagram) => {
      qc.invalidateQueries({ queryKey: ['diagrams'] })
      qc.invalidateQueries({ queryKey: ['diagram', diagram.slug] })
    },
  })
}

export function useGenerateDiagramFromSource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ sourceId, payload }: { sourceId: string; payload?: { title?: string; objective?: string } }) =>
      diagramService.generateFromSource(sourceId, payload),
    onSuccess: (diagram) => {
      qc.invalidateQueries({ queryKey: ['diagrams'] })
      qc.invalidateQueries({ queryKey: ['diagram', diagram.slug] })
    },
  })
}

export function useUpdateDiagram() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ diagramId, payload }: { diagramId: string; payload: Parameters<typeof diagramService.update>[1] }) =>
      diagramService.update(diagramId, payload),
    onSuccess: (diagram) => {
      qc.invalidateQueries({ queryKey: ['diagrams'] })
      qc.invalidateQueries({ queryKey: ['diagram', diagram.slug] })
      qc.invalidateQueries({ queryKey: ['diagram-versions', diagram.id] })
      qc.invalidateQueries({ queryKey: ['diagram-audit', diagram.id] })
    },
  })
}

export function usePublishDiagram() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (diagramId: string) => diagramService.publish(diagramId),
    onSuccess: (diagram) => {
      qc.invalidateQueries({ queryKey: ['diagrams'] })
      qc.invalidateQueries({ queryKey: ['diagram', diagram.slug] })
      qc.invalidateQueries({ queryKey: ['diagram-audit', diagram.id] })
    },
  })
}

export function useUnpublishDiagram() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (diagramId: string) => diagramService.unpublish(diagramId),
    onSuccess: (diagram) => {
      qc.invalidateQueries({ queryKey: ['diagrams'] })
      qc.invalidateQueries({ queryKey: ['diagram', diagram.slug] })
      qc.invalidateQueries({ queryKey: ['diagram-audit', diagram.id] })
    },
  })
}

export function useSubmitDiagramReview() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (diagramId: string) => diagramService.submitReview(diagramId),
    onSuccess: (diagram) => {
      qc.invalidateQueries({ queryKey: ['diagrams'] })
      qc.invalidateQueries({ queryKey: ['diagram', diagram.slug] })
      qc.invalidateQueries({ queryKey: ['diagram-audit', diagram.id] })
    },
  })
}

export function useApproveDiagramReview() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ diagramId, comment }: { diagramId: string; comment?: string }) => diagramService.approveReview(diagramId, { comment }),
    onSuccess: (diagram) => {
      qc.invalidateQueries({ queryKey: ['diagrams'] })
      qc.invalidateQueries({ queryKey: ['diagram', diagram.slug] })
      qc.invalidateQueries({ queryKey: ['diagram-audit', diagram.id] })
    },
  })
}

export function useRequestDiagramChanges() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ diagramId, comment }: { diagramId: string; comment?: string }) => diagramService.requestChanges(diagramId, { comment }),
    onSuccess: (diagram) => {
      qc.invalidateQueries({ queryKey: ['diagrams'] })
      qc.invalidateQueries({ queryKey: ['diagram', diagram.slug] })
      qc.invalidateQueries({ queryKey: ['diagram-audit', diagram.id] })
    },
  })
}
