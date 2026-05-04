'use client'
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { queryService } from '@/services'
import type { AskResponse } from '@/lib/types'

export function useChatSessions() {
  return useQuery({
    queryKey: ['ask-sessions'],
    queryFn: () => queryService.listChatSessions(),
  })
}

export function useChatSession(sessionId: string | null) {
  return useQuery({
    queryKey: ['ask-session', sessionId],
    queryFn: () => queryService.getChatSession(sessionId as string),
    enabled: !!sessionId,
  })
}

export function useDeleteChatSession() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (sessionId: string) => queryService.deleteChatSession(sessionId),
    onSuccess: (_, sessionId) => {
      qc.invalidateQueries({ queryKey: ['ask-sessions'] })
      qc.removeQueries({ queryKey: ['ask-session', sessionId] })
    },
  })
}

export function useAskConversation(sessionId?: string | null) {
  const qc = useQueryClient()
  const [history, setHistory] = useState<AskResponse[]>([])
  const [currentAnswer, setCurrentAnswer] = useState<AskResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const ask = async (question: string) => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await queryService.ask(question, sessionId)
      setCurrentAnswer(response)
      setHistory(prev => [...prev, response])
      qc.invalidateQueries({ queryKey: ['ask-sessions'] })
      qc.invalidateQueries({ queryKey: ['ask-session', response.sessionId] })
      return response
    } catch (e) {
      setError(e as Error)
      throw e
    } finally {
      setIsLoading(false)
    }
  }

  return {
    history,
    currentAnswer,
    isLoading,
    error,
    ask,
    clear: () => { setCurrentAnswer(null); setHistory([]); setError(null) },
  }
}
