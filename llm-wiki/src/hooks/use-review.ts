'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { reviewService } from '@/services'
import type { SeverityLevel, ReviewIssueType } from '@/lib/constants'

export function useReviewQueue(params?: { severity?: SeverityLevel; issueType?: ReviewIssueType; page?: number }) {
  return useQuery({
    queryKey: ['review-queue', params],
    queryFn: () => reviewService.getQueue(params),
  })
}

export function useReviewItem(id: string) {
  return useQuery({
    queryKey: ['review-item', id],
    queryFn: () => reviewService.getItem(id),
    enabled: !!id,
  })
}

export function useApproveReview() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, comment }: { id: string; comment?: string }) => reviewService.approve(id, comment),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['review-queue'] })
      qc.invalidateQueries({ queryKey: ['pages'] })
    },
  })
}

export function useAddReviewComment() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, comment }: { id: string; comment: string }) => reviewService.addComment(id, comment),
    onSuccess: (_result, variables) => {
      qc.invalidateQueries({ queryKey: ['review-queue'] })
      qc.invalidateQueries({ queryKey: ['review-item', variables.id] })
    },
  })
}

export function useRejectReview() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => reviewService.reject(id, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['review-queue'] })
      qc.invalidateQueries({ queryKey: ['pages'] })
    },
  })
}

export function useMergeReview() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, targetPageId, comment }: { id: string; targetPageId?: string; comment?: string }) =>
      reviewService.merge(id, { targetPageId, comment }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['review-queue'] })
      qc.invalidateQueries({ queryKey: ['pages'] })
      qc.invalidateQueries({ queryKey: ['graph'] })
    },
  })
}

export function useCreateIssuePageFromReview() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => reviewService.createIssuePage(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['review-queue'] })
      qc.invalidateQueries({ queryKey: ['pages'] })
      qc.invalidateQueries({ queryKey: ['graph'] })
    },
  })
}

export function useRequestReviewRebuild() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (sourceId: string) => reviewService.requestRebuild(sourceId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sources'] })
      qc.invalidateQueries({ queryKey: ['review-queue'] })
    },
  })
}
