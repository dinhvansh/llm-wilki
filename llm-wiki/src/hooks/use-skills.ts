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

  const createSkill = useMutation({
    mutationFn: (payload: {
      id?: string
      name: string
      version?: string
      scope?: string
      status?: string
      reviewStatus?: string
      summary?: string
      description?: string
      instructions?: string
      capabilities?: string[]
      tags?: string[]
      entryPoints?: string[]
      owner?: string | null
      taskProfile?: string
      metadataJson?: Record<string, unknown>
      changeComment?: string
    }) => skillService.create(payload),
    onSuccess: refresh,
  })

  const updateSkill = useMutation({
    mutationFn: ({ id, payload }: {
      id: string
      payload: {
        name: string
        version?: string
        scope?: string
        status?: string
        reviewStatus?: string
        summary?: string
        description?: string
        instructions?: string
        capabilities?: string[]
        tags?: string[]
        entryPoints?: string[]
        owner?: string | null
        taskProfile?: string
        metadataJson?: Record<string, unknown>
        changeComment?: string
      }
    }) => skillService.update(id, payload),
    onSuccess: refresh,
  })

  const testSkill = useMutation({
    mutationFn: ({ id, input }: { id: string; input: string }) => skillService.test(id, input),
    onSuccess: refresh,
  })

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

  return { createSkill, updateSkill, testSkill, addComment, submitReview, approve, release }
}
