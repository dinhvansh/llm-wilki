import type { RuntimeConnectionTestResult, RuntimeModelListResult, RuntimeSettings } from '@/lib/types'
import type { ISettingsService } from '@/services/types'

let settingsState: RuntimeSettings = {
  answerProvider: 'none',
  answerModel: '',
  answerApiKey: '',
  answerBaseUrl: 'http://host.docker.internal:11434',
  answerTimeoutSeconds: 90,
  ingestProvider: 'none',
  ingestModel: '',
  ingestApiKey: '',
  ingestBaseUrl: 'http://host.docker.internal:11434',
  ingestTimeoutSeconds: 90,
  embeddingProvider: 'none',
  embeddingModel: '',
  embeddingApiKey: '',
  embeddingBaseUrl: '',
  aiTaskProfiles: {
    ingest_summary: { provider: 'none', model: '', apiKey: '', baseUrl: 'http://host.docker.internal:11434', timeoutSeconds: 90 },
    claim_extraction: { provider: 'none', model: '', apiKey: '', baseUrl: 'http://host.docker.internal:11434', timeoutSeconds: 90 },
    entity_glossary_timeline: { provider: 'none', model: '', apiKey: '', baseUrl: 'http://host.docker.internal:11434', timeoutSeconds: 90 },
    bpm_generation: { provider: 'none', model: '', apiKey: '', baseUrl: 'http://host.docker.internal:11434', timeoutSeconds: 90 },
    ask_answer: { provider: 'none', model: '', apiKey: '', baseUrl: 'http://host.docker.internal:11434', timeoutSeconds: 90 },
    review_assist: { provider: 'none', model: '', apiKey: '', baseUrl: 'http://host.docker.internal:11434', timeoutSeconds: 90 },
    embeddings: { provider: 'none', model: '', apiKey: '', baseUrl: '', timeoutSeconds: 90 },
  },
  chunkMode: 'structured',
  chunkSizeWords: 180,
  chunkOverlapWords: 30,
  retrievalLimit: 4,
  hybridSemanticWeight: 0.35,
  searchResultLimit: 20,
  graphNodeLimit: 250,
  lintPageLimit: 500,
  autoReviewThreshold: 0.76,
  askPolicy: {
    minimumTopScore: 0.45,
    minimumTermCoverage: 0.35,
    allowPartialAnswers: true,
    allowGeneralFallback: false,
    crossLingualRewriteEnabled: true,
  },
  updatedAt: new Date().toISOString(),
}

export function createMockSettingsService(): ISettingsService {
  return {
    async get(): Promise<RuntimeSettings> {
      return settingsState
    },
    async update(payload: Omit<RuntimeSettings, 'updatedAt'>): Promise<RuntimeSettings> {
      settingsState = { ...payload, updatedAt: new Date().toISOString() }
      return settingsState
    },
    async testConnection(payload): Promise<RuntimeConnectionTestResult> {
      const success = payload.provider !== 'none' && Boolean(payload.model)
      return {
        success,
        provider: payload.provider,
        model: payload.model,
        purpose: payload.purpose,
        message: success ? 'Mock connection succeeded.' : "Choose a provider other than 'none' and set a model before testing.",
        latencyMs: success ? 120 : undefined,
      }
    },
    async loadModels(payload): Promise<RuntimeModelListResult> {
      const models = payload.provider === 'gemini'
        ? ['gemini-2.5-flash', 'gemini-2.5-pro']
        : payload.provider === 'openai'
          ? ['gpt-5-mini', 'gpt-5.1', 'gpt-4.1-mini']
          : payload.provider === 'ollama'
            ? ['llama3.2:latest', 'qwen2.5:latest']
            : ['claude-sonnet-4-5']
      return {
        success: payload.provider !== 'none',
        provider: payload.provider,
        models,
        message: `Mock loaded ${models.length} models.`,
        latencyMs: 80,
      }
    },
  }
}
