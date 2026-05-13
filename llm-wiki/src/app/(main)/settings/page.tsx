'use client'
import { useEffect, useState } from 'react'
import { PageHeader } from '@/components/layout/page-header'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { ErrorState } from '@/components/data-display/error-state'
import { useSettings, useTestSettingsConnection, useUpdateSettings } from '@/hooks/use-settings'
import type { AIModelProfile, AITaskKey, RuntimeConnectionTestResult, RuntimeSettings } from '@/lib/types'
import { ChevronDown, Clock3, SlidersHorizontal } from 'lucide-react'

const PROVIDERS = ['none', 'ollama', 'openai', 'anthropic', 'openai_compatible']
const DEFAULT_BASE_URL = 'http://host.docker.internal:11434'

const TASK_CONFIG: Array<{ key: AITaskKey; title: string; description: string; defaultBaseUrl?: string }> = [
  { key: 'ingest_summary', title: 'Ingest Summary', description: 'Tom tat va key facts trong qua trinh ingest.', defaultBaseUrl: DEFAULT_BASE_URL },
  { key: 'claim_extraction', title: 'Claim Extraction', description: 'Task semantic cho claim/knowledge extraction ve sau.', defaultBaseUrl: DEFAULT_BASE_URL },
  { key: 'entity_glossary_timeline', title: 'Entity / Glossary / Timeline', description: 'Task trich thuc the, glossary, timeline.', defaultBaseUrl: DEFAULT_BASE_URL },
  { key: 'bpm_generation', title: 'BPM Generation', description: 'Task sinh BPM flow tu page/source.', defaultBaseUrl: DEFAULT_BASE_URL },
  { key: 'ask_answer', title: 'Ask AI', description: 'Task tra loi grounded cho nguoi dung.', defaultBaseUrl: DEFAULT_BASE_URL },
  { key: 'review_assist', title: 'Review Assist', description: 'Task goi y review/lint/quick-fix ve sau.', defaultBaseUrl: DEFAULT_BASE_URL },
  { key: 'embeddings', title: 'Embeddings', description: 'Task embeddings cho retrieval va indexing.', defaultBaseUrl: '' },
]

const EMPTY_FORM: Omit<RuntimeSettings, 'updatedAt'> = {
  answerProvider: 'none',
  answerModel: '',
  answerApiKey: '',
  answerBaseUrl: DEFAULT_BASE_URL,
  answerTimeoutSeconds: 90,
  ingestProvider: 'none',
  ingestModel: '',
  ingestApiKey: '',
  ingestBaseUrl: DEFAULT_BASE_URL,
  ingestTimeoutSeconds: 90,
  embeddingProvider: 'none',
  embeddingModel: '',
  embeddingApiKey: '',
  embeddingBaseUrl: '',
  aiTaskProfiles: {
    ingest_summary: { provider: 'none', model: '', apiKey: '', baseUrl: DEFAULT_BASE_URL, timeoutSeconds: 90 },
    claim_extraction: { provider: 'none', model: '', apiKey: '', baseUrl: DEFAULT_BASE_URL, timeoutSeconds: 90 },
    entity_glossary_timeline: { provider: 'none', model: '', apiKey: '', baseUrl: DEFAULT_BASE_URL, timeoutSeconds: 90 },
    bpm_generation: { provider: 'none', model: '', apiKey: '', baseUrl: DEFAULT_BASE_URL, timeoutSeconds: 90 },
    ask_answer: { provider: 'none', model: '', apiKey: '', baseUrl: DEFAULT_BASE_URL, timeoutSeconds: 90 },
    review_assist: { provider: 'none', model: '', apiKey: '', baseUrl: DEFAULT_BASE_URL, timeoutSeconds: 90 },
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
}

function Section({
  title,
  description,
  children,
}: {
  title: string
  description: string
  children: React.ReactNode
}) {
  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <div className="mb-4">
        <h2 className="text-base font-semibold">{title}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">{children}</div>
    </section>
  )
}

function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <label className="block">
      <div className="mb-1 text-sm font-medium">{label}</div>
      {children}
      {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
    </label>
  )
}

function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`h-10 w-full rounded-md border border-input bg-background px-3 text-sm ${props.className ?? ''}`} />
}

function SelectInput(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={`h-10 w-full rounded-md border border-input bg-background px-3 text-sm ${props.className ?? ''}`} />
}

function deriveLegacyFields(form: Omit<RuntimeSettings, 'updatedAt'>): Omit<RuntimeSettings, 'updatedAt'> {
  const ask = form.aiTaskProfiles.ask_answer
  const ingest = form.aiTaskProfiles.ingest_summary
  const embeddings = form.aiTaskProfiles.embeddings
  return {
    ...form,
    answerProvider: ask.provider,
    answerModel: ask.model,
    answerApiKey: ask.apiKey,
    answerBaseUrl: ask.baseUrl,
    answerTimeoutSeconds: Number(ask.timeoutSeconds),
    ingestProvider: ingest.provider,
    ingestModel: ingest.model,
    ingestApiKey: ingest.apiKey,
    ingestBaseUrl: ingest.baseUrl,
    ingestTimeoutSeconds: Number(ingest.timeoutSeconds),
    embeddingProvider: embeddings.provider,
    embeddingModel: embeddings.model,
    embeddingApiKey: embeddings.apiKey,
    embeddingBaseUrl: embeddings.baseUrl,
  }
}

export default function SettingsPage() {
  const { data, isLoading, isError, error, refetch } = useSettings()
  const updateMutation = useUpdateSettings()
  const testConnectionMutation = useTestSettingsConnection()
  const [form, setForm] = useState<Omit<RuntimeSettings, 'updatedAt'>>(EMPTY_FORM)
  const [taskTestResults, setTaskTestResults] = useState<Partial<Record<AITaskKey, RuntimeConnectionTestResult>>>({})
  const [expandedTask, setExpandedTask] = useState<AITaskKey | null>(null)

  useEffect(() => {
    if (!data) return
    const { updatedAt: _updatedAt, ...rest } = data
    setForm(rest)
  }, [data])

  if (isLoading) return <LoadingSpinner label="Loading settings..." />
  if (isError) {
    return (
      <div>
        <PageHeader title="Settings" />
        <ErrorState message={(error as Error)?.message ?? 'Failed to load settings'} onRetry={() => refetch()} />
      </div>
    )
  }

  const updateTaskProfile = <K extends keyof AIModelProfile>(task: AITaskKey, field: K, value: AIModelProfile[K]) => {
    setForm(prev => ({
      ...prev,
      aiTaskProfiles: {
        ...prev.aiTaskProfiles,
        [task]: {
          ...prev.aiTaskProfiles[task],
          [field]: value,
        },
      },
    }))
  }

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const normalized = deriveLegacyFields({
      ...form,
      chunkSizeWords: Number(form.chunkSizeWords),
      chunkOverlapWords: Number(form.chunkOverlapWords),
      retrievalLimit: Number(form.retrievalLimit),
      hybridSemanticWeight: Number(form.hybridSemanticWeight),
      searchResultLimit: Number(form.searchResultLimit),
      graphNodeLimit: Number(form.graphNodeLimit),
      lintPageLimit: Number(form.lintPageLimit),
      autoReviewThreshold: Number(form.autoReviewThreshold),
      aiTaskProfiles: Object.fromEntries(
        Object.entries(form.aiTaskProfiles).map(([task, profile]) => [
          task,
          {
            ...profile,
            timeoutSeconds: Number(profile.timeoutSeconds),
          },
        ]),
      ) as RuntimeSettings['aiTaskProfiles'],
    })
    await updateMutation.mutateAsync(normalized)
  }

  const testConnection = async (task: AITaskKey) => {
    const profile = form.aiTaskProfiles[task]
    try {
      const result = await testConnectionMutation.mutateAsync({
        provider: profile.provider,
        model: profile.model,
        apiKey: profile.apiKey,
        baseUrl: profile.baseUrl,
        timeoutSeconds: Number(profile.timeoutSeconds),
        purpose: task,
      })
      setTaskTestResults(prev => ({ ...prev, [task]: result }))
    } catch (mutationError) {
      setTaskTestResults(prev => ({
        ...prev,
        [task]: {
          success: false,
          provider: profile.provider,
          model: profile.model,
          purpose: task,
          message: (mutationError as Error).message || 'Connection test failed.',
        },
      }))
    }
  }

  return (
    <div>
      <PageHeader
        title="Settings"
        description="Task-scoped AI settings for product runtime. Each task can use a different model, provider, timeout, and endpoint."
        actions={
          <button
            type="submit"
            form="settings-form"
            disabled={updateMutation.isPending}
            className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {updateMutation.isPending ? 'Saving...' : 'Save Settings'}
          </button>
        }
      />

      <form id="settings-form" onSubmit={onSubmit} className="space-y-5 p-6">
        <Section
          title="Task-Scoped AI Profiles"
          description="Model selection is separated by business task so Ask AI, BPM generation, extraction, and embeddings can evolve independently."
        >
          <div className="md:col-span-2 grid gap-5">
            {TASK_CONFIG.map(task => {
              const profile = form.aiTaskProfiles[task.key]
              const result = taskTestResults[task.key]
              const isTesting = testConnectionMutation.isPending && testConnectionMutation.variables?.purpose === task.key
              const isExpanded = expandedTask === task.key
              return (
                <div key={task.key} className="overflow-hidden rounded-xl border border-border bg-background">
                  <button
                    type="button"
                    onClick={() => setExpandedTask(current => current === task.key ? null : task.key)}
                    className="flex w-full items-start justify-between gap-4 px-4 py-4 text-left transition-colors hover:bg-accent/40"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-sm font-semibold">{task.title}</h3>
                        <span className="rounded-md border border-border px-2 py-0.5 text-[11px] text-muted-foreground">{task.key}</span>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">{task.description}</p>
                      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-1">
                          <SlidersHorizontal className="h-3 w-3" />
                          {profile.provider || 'none'}
                        </span>
                        <span className="rounded-full bg-muted px-2.5 py-1">{profile.model || 'No model selected'}</span>
                        <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-1">
                          <Clock3 className="h-3 w-3" />
                          {Number(profile.timeoutSeconds)}s
                        </span>
                      </div>
                    </div>
                    <ChevronDown className={`mt-1 h-4 w-4 flex-shrink-0 text-muted-foreground transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                  </button>

                  {isExpanded && (
                    <div className="border-t border-border px-4 py-4">
                      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                        <Field label="Provider">
                          <SelectInput value={profile.provider} onChange={e => updateTaskProfile(task.key, 'provider', e.target.value)}>
                            {PROVIDERS.map(provider => <option key={provider} value={provider}>{provider}</option>)}
                          </SelectInput>
                        </Field>
                        <Field label="Model">
                          <TextInput value={profile.model} onChange={e => updateTaskProfile(task.key, 'model', e.target.value)} placeholder={task.key === 'embeddings' ? 'nomic-embed-text' : 'gemma3:4b'} />
                        </Field>
                        <Field label="API Key">
                          <TextInput value={profile.apiKey} onChange={e => updateTaskProfile(task.key, 'apiKey', e.target.value)} placeholder="optional" type="password" />
                        </Field>
                        <Field label="Base URL" hint="For Ollama in Docker use http://host.docker.internal:11434.">
                          <TextInput value={profile.baseUrl} onChange={e => updateTaskProfile(task.key, 'baseUrl', e.target.value)} placeholder={task.defaultBaseUrl ?? ''} />
                        </Field>
                        <Field label="Timeout (seconds)">
                          <TextInput value={profile.timeoutSeconds} onChange={e => updateTaskProfile(task.key, 'timeoutSeconds', Number(e.target.value))} type="number" min={5} max={600} />
                        </Field>
                        <div className="flex items-end">
                          <button
                            type="button"
                            onClick={() => testConnection(task.key)}
                            disabled={testConnectionMutation.isPending}
                            className="rounded-md border border-border px-3 py-2 text-sm hover:bg-accent disabled:opacity-50"
                          >
                            {isTesting ? 'Testing...' : 'Test Connection'}
                          </button>
                        </div>
                      </div>
                      {result && (
                        <div className={`mt-3 rounded-md border px-3 py-2 text-sm ${result.success ? 'border-green-200 bg-green-50 text-green-700' : 'border-red-200 bg-red-50 text-red-700'}`}>
                          {result.message}
                          {typeof result.latencyMs === 'number' ? ` (${result.latencyMs} ms)` : ''}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </Section>

        <Section
          title="Chunking And Retrieval"
          description="These settings affect parse/chunk/retrieval behavior independently from the AI task profiles."
        >
          <Field label="Chunk Mode" hint="Structured uses Docling-aware boundaries. Window keeps the older word-window splitter for rollback or comparison.">
            <SelectInput value={form.chunkMode} onChange={e => setForm(prev => ({ ...prev, chunkMode: e.target.value as 'structured' | 'window' }))}>
              <option value="structured">structured</option>
              <option value="window">window</option>
            </SelectInput>
          </Field>
          <Field label="Chunk Size (words)">
            <TextInput value={form.chunkSizeWords} onChange={e => setForm(prev => ({ ...prev, chunkSizeWords: Number(e.target.value) }))} type="number" min={50} max={2000} />
          </Field>
          <Field label="Chunk Overlap (words)">
            <TextInput value={form.chunkOverlapWords} onChange={e => setForm(prev => ({ ...prev, chunkOverlapWords: Number(e.target.value) }))} type="number" min={0} max={500} />
          </Field>
          <Field label="Retrieval Top K">
            <TextInput value={form.retrievalLimit} onChange={e => setForm(prev => ({ ...prev, retrievalLimit: Number(e.target.value) }))} type="number" min={1} max={20} />
          </Field>
          <Field label="Semantic Weight">
            <TextInput value={form.hybridSemanticWeight} onChange={e => setForm(prev => ({ ...prev, hybridSemanticWeight: Number(e.target.value) }))} type="number" min={0} max={1} step="0.05" />
          </Field>
          <Field label="Search Result Limit">
            <TextInput value={form.searchResultLimit} onChange={e => setForm(prev => ({ ...prev, searchResultLimit: Number(e.target.value) }))} type="number" min={1} max={100} />
          </Field>
          <Field label="Graph Node Limit">
            <TextInput value={form.graphNodeLimit} onChange={e => setForm(prev => ({ ...prev, graphNodeLimit: Number(e.target.value) }))} type="number" min={25} max={2000} />
          </Field>
          <Field label="Lint Scan Limit">
            <TextInput value={form.lintPageLimit} onChange={e => setForm(prev => ({ ...prev, lintPageLimit: Number(e.target.value) }))} type="number" min={50} max={5000} />
          </Field>
          <Field label="Auto Review Threshold">
            <TextInput value={form.autoReviewThreshold} onChange={e => setForm(prev => ({ ...prev, autoReviewThreshold: Number(e.target.value) }))} type="number" min={0} max={1} step="0.01" />
          </Field>
        </Section>

        <div className="rounded-lg border border-border bg-card px-4 py-3 text-sm text-muted-foreground">
          Last updated: <span className="font-medium text-foreground">{data?.updatedAt ?? 'unknown'}</span>
          {updateMutation.isSuccess && <span className="ml-3 text-primary">Saved.</span>}
          {updateMutation.isError && <span className="ml-3 text-destructive">{(updateMutation.error as Error).message}</span>}
        </div>
      </form>
    </div>
  )
}
