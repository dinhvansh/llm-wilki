'use client'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { noteService } from '@/services'

export function useNotes(params?: Parameters<typeof noteService.list>[0]) {
  return useQuery({
    queryKey: ['notes', params],
    queryFn: () => noteService.list(params),
  })
}

export function useCreateNote() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Parameters<typeof noteService.create>[0]) => noteService.create(payload),
    onSuccess: note => {
      qc.invalidateQueries({ queryKey: ['notes'] })
      note.anchors.forEach(anchor => {
        if (anchor.sourceId) qc.invalidateQueries({ queryKey: ['notes', { sourceId: anchor.sourceId }] })
        if (anchor.pageId) qc.invalidateQueries({ queryKey: ['notes', { pageId: anchor.pageId }] })
      })
    },
  })
}

export function useUpdateNote() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof noteService.update>[1] }) => noteService.update(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notes'] }),
  })
}

export function useArchiveNote() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => noteService.archive(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notes'] }),
  })
}

export function useCreatePageDraftFromNote() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => noteService.createPageDraft(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notes'] }),
  })
}

export function useCreateReviewItemFromNote() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => noteService.createReviewItem(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notes'] })
      qc.invalidateQueries({ queryKey: ['review'] })
    },
  })
}
