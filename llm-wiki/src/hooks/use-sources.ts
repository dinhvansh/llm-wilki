'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { sourceService } from '@/services'

export function useSources(params?: Parameters<typeof sourceService.list>[0]) {
  return useQuery({
    queryKey: ['sources', params],
    queryFn: () => sourceService.list(params),
  })
}

export function useSource(id: string) {
  return useQuery({
    queryKey: ['source', id],
    queryFn: () => sourceService.getById(id),
    enabled: !!id,
  })
}

export function useSourceChunks(sourceId: string, params?: Parameters<typeof sourceService.getChunks>[1]) {
  return useQuery({
    queryKey: ['source-chunks', sourceId, params],
    queryFn: () => sourceService.getChunks(sourceId, params),
    enabled: !!sourceId,
  })
}

export function useSourceArtifacts(sourceId: string) {
  return useQuery({
    queryKey: ['source-artifacts', sourceId],
    queryFn: () => sourceService.getArtifacts(sourceId),
    enabled: !!sourceId,
  })
}

export function useSourceClaims(sourceId: string) {
  return useQuery({
    queryKey: ['source-claims', sourceId],
    queryFn: () => sourceService.getClaims(sourceId),
    enabled: !!sourceId,
  })
}

export function useSourceKnowledgeUnits(sourceId: string) {
  return useQuery({
    queryKey: ['source-knowledge-units', sourceId],
    queryFn: () => sourceService.getKnowledgeUnits(sourceId),
    enabled: !!sourceId,
  })
}

export function useSourceExtractionRuns(sourceId: string) {
  return useQuery({
    queryKey: ['source-extraction-runs', sourceId],
    queryFn: () => sourceService.getExtractionRuns(sourceId),
    enabled: !!sourceId,
  })
}

export function useSourceEntities(sourceId: string) {
  return useQuery({
    queryKey: ['source-entities', sourceId],
    queryFn: () => sourceService.getEntities(sourceId),
    enabled: !!sourceId,
  })
}

export function useAffectedPages(sourceId: string) {
  return useQuery({
    queryKey: ['affected-pages', sourceId],
    queryFn: () => sourceService.getAffectedPages(sourceId),
    enabled: !!sourceId,
  })
}

export function useSourceSuggestions(sourceId: string) {
  return useQuery({
    queryKey: ['source-suggestions', sourceId],
    queryFn: () => sourceService.getSuggestions(sourceId),
    enabled: !!sourceId,
  })
}

export function useSourceJobs(sourceId: string) {
  return useQuery({
    queryKey: ['source-jobs', sourceId],
    queryFn: () => sourceService.getJobs(sourceId),
    enabled: !!sourceId,
    refetchInterval: 5000,
  })
}

export function useRetrySourceJob(sourceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (jobId: string) => sourceService.retryJob(jobId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['source-jobs', sourceId] })
      qc.invalidateQueries({ queryKey: ['source', sourceId] })
    },
  })
}

export function useRebuildSource(sourceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => sourceService.rebuild(sourceId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['source-jobs', sourceId] })
      qc.invalidateQueries({ queryKey: ['source', sourceId] })
      qc.invalidateQueries({ queryKey: ['source-chunks', sourceId] })
      qc.invalidateQueries({ queryKey: ['source-claims', sourceId] })
      qc.invalidateQueries({ queryKey: ['source-knowledge-units', sourceId] })
      qc.invalidateQueries({ queryKey: ['source-extraction-runs', sourceId] })
    },
  })
}

export function useCancelSourceJob(sourceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (jobId: string) => sourceService.cancelJob(jobId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['source-jobs', sourceId] }),
  })
}

export function useArchiveSource(sourceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => sourceService.archive(sourceId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['source', sourceId] })
      qc.invalidateQueries({ queryKey: ['sources'] })
    },
  })
}

export function useRestoreSource(sourceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => sourceService.restore(sourceId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['source', sourceId] })
      qc.invalidateQueries({ queryKey: ['sources'] })
    },
  })
}

export function useUpdateSourceMetadata(sourceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: {
      description?: string | null
      tags?: string[]
      trustLevel?: string | null
      documentType?: string | null
      sourceStatus?: string | null
      authorityLevel?: string | null
      effectiveDate?: string | null
      version?: string | null
      owner?: string | null
    }) => sourceService.updateMetadata(sourceId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['source', sourceId] })
      qc.invalidateQueries({ queryKey: ['sources'] })
    },
  })
}

export function useAcceptSourceSuggestion(sourceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (suggestionId: string) => sourceService.acceptSuggestion(suggestionId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['source-suggestions', sourceId] })
      qc.invalidateQueries({ queryKey: ['source', sourceId] })
      qc.invalidateQueries({ queryKey: ['affected-pages', sourceId] })
      qc.invalidateQueries({ queryKey: ['sources'] })
    },
  })
}

export function useRejectSourceSuggestion(sourceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (suggestionId: string) => sourceService.rejectSuggestion(suggestionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['source-suggestions', sourceId] }),
  })
}

export function useAcceptAllSourceSuggestions(sourceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => sourceService.acceptAllSuggestions(sourceId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['source-suggestions', sourceId] })
      qc.invalidateQueries({ queryKey: ['source', sourceId] })
      qc.invalidateQueries({ queryKey: ['affected-pages', sourceId] })
      qc.invalidateQueries({ queryKey: ['sources'] })
    },
  })
}

export function useRejectAllSourceSuggestions(sourceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => sourceService.rejectAllSuggestions(sourceId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['source-suggestions', sourceId] }),
  })
}

export function useChangeSourceSuggestionTarget(sourceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ suggestionId, targetId }: { suggestionId: string; targetId?: string | null }) => sourceService.changeSuggestionTarget(suggestionId, targetId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['source-suggestions', sourceId] }),
  })
}

export function useMarkSourceStandalone(sourceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => sourceService.markStandalone(sourceId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['source-suggestions', sourceId] })
      qc.invalidateQueries({ queryKey: ['source', sourceId] })
      qc.invalidateQueries({ queryKey: ['sources'] })
    },
  })
}

export function useUploadSource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: File | { file: File; collectionId?: string }) => {
      if (payload instanceof File) return sourceService.upload(payload)
      return sourceService.upload(payload.file, payload.collectionId)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sources'] }),
  })
}

export function useIngestUrlSource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: { url: string; title?: string; collectionId?: string }) => sourceService.ingestUrl(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sources'] }),
  })
}

export function useIngestTextSource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: { title: string; content: string; sourceType?: 'txt' | 'transcript'; collectionId?: string }) => sourceService.ingestText(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sources'] }),
  })
}
