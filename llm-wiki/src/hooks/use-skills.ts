'use client'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { skillService } from '@/services'

export function useSkills() {
  return useQuery({
    queryKey: ['skills'],
    queryFn: () => skillService.list(),
  })
}

export function useSkillActions() {
  const queryClient = useQueryClient()

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ['skills'] })
  }

  const addComment = useMutation({
    mutationFn: ({ id, comment }: { id: string; comment: string }) => skillService.addComment(id, comment),
    onSuccess: refresh,
  })

  const submitReview = useMutation({
    mutationFn: ({ id, comment }: { id: string; comment?: string }) => skillService.submitReview(id, comment),
    onSuccess: refresh,
  })

  const approve = useMutation({
    mutationFn: ({ id, comment }: { id: string; comment?: string }) => skillService.approve(id, comment),
    onSuccess: refresh,
  })

  const release = useMutation({
    mutationFn: ({ id, comment }: { id: string; comment?: string }) => skillService.release(id, comment),
    onSuccess: refresh,
  })

  return { addComment, submitReview, approve, release }
}
