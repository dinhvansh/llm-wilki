import type { AskResponse, SearchResult } from '@/lib/types'
import type { IQueryService } from '../types'
import { MOCK_ASK_RESPONSES, MOCK_SEARCH_RESULTS } from './mock-data'

const delay = (ms = 600) => new Promise(resolve => setTimeout(resolve, ms))

export function createMockQueryService(): IQueryService {
  return {
    async ask(question, sessionId) {
      await delay(800)
      // Find matching response or generate a fallback
      const key = Object.keys(MOCK_ASK_RESPONSES).find(k =>
        k.toLowerCase().includes(question.toLowerCase().split(' ')[0]) ||
        question.toLowerCase().includes(k.toLowerCase().split(' ')[0])
      )
      if (key && MOCK_ASK_RESPONSES[key]) {
        return { ...MOCK_ASK_RESPONSES[key], id: `ask-${Date.now()}`, sessionId: sessionId ?? `chat-${Date.now()}`, answeredAt: new Date().toISOString() }
      }
      // Fallback for any question
      return {
        id: `ask-${Date.now()}`,
        sessionId: sessionId ?? `chat-${Date.now()}`,
        question,
        answer: `Based on the available knowledge base, here's what I found regarding "${question}":\n\nThe knowledge base contains information about AI governance, RAG architecture, document processing pipelines, and safety evaluation frameworks. To get a specific answer, please try asking about one of these topics in more detail.\n\n**Suggested follow-up questions:**\n- What is RAG and how does it work?\n- What are the safety requirements for deploying an LLM?\n- How does the document processing pipeline work?`,
        answerType: 'direct_answer',
        interpretedQuery: {
          standaloneQuery: question,
          intent: 'fact_lookup',
          answerType: 'direct_answer',
          targetEntities: [],
          filters: {},
          needsClarification: false,
          clarificationQuestion: null,
          conversationSummary: null,
        },
        citations: [],
        relatedPages: [],
        relatedSources: [],
        confidence: 65,
        isInference: true,
        uncertainty: null,
        conflicts: [],
        retrievalDebugId: null,
        diagnostics: null,
        answeredAt: new Date().toISOString(),
      }
    },

    async listChatSessions(limit = 30) {
      await delay(200)
      return [
        {
          id: 'chat-demo',
          title: 'RAG architecture questions',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          messageCount: 2,
          lastMessagePreview: 'What is RAG and how does it work?',
        },
      ].slice(0, limit)
    },

    async getChatSession(sessionId) {
      await delay(200)
      const response = await this.ask('What is RAG and how does it work?', sessionId)
      return {
        id: sessionId,
        title: 'RAG architecture questions',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        messageCount: 2,
        lastMessagePreview: response.question,
        messages: [
          { id: 'msg-user-demo', sessionId, role: 'user', content: response.question, createdAt: response.answeredAt },
          { id: response.id, sessionId, role: 'assistant', content: response.answer, response, createdAt: response.answeredAt },
        ],
      }
    },

    async deleteChatSession() {
      await delay(150)
      return { success: true }
    },

    async search(query, params) {
      await delay(400)
      const q = query.toLowerCase()
      // Find direct matches in search results
      for (const [key, results] of Object.entries(MOCK_SEARCH_RESULTS)) {
        if (q.includes(key.toLowerCase())) return results.slice(0, params?.limit ?? 10)
      }
      // General search across all content
      const results: SearchResult[] = []
      const term = query.split(' ')[0]
      if ('rag'.includes(term)) results.push(...MOCK_SEARCH_RESULTS['RAG'])
      if ('safety'.includes(term)) results.push(...MOCK_SEARCH_RESULTS['safety'])
      return results.slice(0, params?.limit ?? 10)
    },
  }
}
