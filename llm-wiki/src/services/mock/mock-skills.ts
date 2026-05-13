import type { SkillPackage } from '@/lib/types'

import type { ISkillService } from '../types'

const MOCK_SKILLS: SkillPackage[] = [
  {
    id: 'multimodal-review-assistant',
    name: 'Multimodal Review Assistant',
    version: '0.1.0',
    scope: 'workspace',
    status: 'draft',
    reviewStatus: 'internal_preview',
    owner: 'Knowledge Ops',
    summary: 'Reusable review helper that inspects page deltas, source artifacts, and authority conflicts before approval.',
    description: 'Minimal internal registry entry for a reusable review workflow package.',
    capabilities: ['review evidence triage', 'artifact-aware source inspection', 'authority conflict summarization'],
    tags: ['review', 'artifact', 'governance'],
    entryPoints: ['review queue', 'page citation inspector', 'source artifact inspector'],
    reviewHistory: [],
    metadataJson: { packageType: 'workflow_pack', distribution: 'file_registry' },
  },
]

export function createMockSkillService(): ISkillService {
  return {
    async list() {
      return MOCK_SKILLS
    },
    async get(id) {
      return MOCK_SKILLS.find(item => item.id === id) ?? MOCK_SKILLS[0]
    },
    async create(payload) {
      const skill: SkillPackage = {
        id: payload.id ?? payload.name.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
        name: payload.name,
        version: payload.version ?? '0.1.0',
        scope: payload.scope ?? 'workspace',
        status: payload.status ?? 'draft',
        reviewStatus: payload.reviewStatus ?? 'draft',
        owner: payload.owner ?? 'Mock Author',
        summary: payload.summary ?? '',
        description: payload.description ?? '',
        instructions: payload.instructions ?? '',
        capabilities: payload.capabilities ?? [],
        tags: payload.tags ?? [],
        entryPoints: payload.entryPoints ?? [],
        taskProfile: payload.taskProfile ?? 'ask_answer',
        reviewHistory: [],
        metadataJson: payload.metadataJson ?? {},
      }
      MOCK_SKILLS.unshift(skill)
      return skill
    },
    async update(id, payload) {
      const skill = MOCK_SKILLS.find(item => item.id === id) ?? MOCK_SKILLS[0]
      Object.assign(skill, payload)
      return skill
    },
    async test(id, input) {
      const skill = MOCK_SKILLS.find(item => item.id === id) ?? MOCK_SKILLS[0]
      const result = {
        id: `test-${Date.now()}`,
        input,
        output: `Mock skill output for "${skill.name}": ${input}`,
        taskProfile: skill.taskProfile ?? 'ask_answer',
        provider: 'mock',
        model: 'mock-skill-runner',
        success: true,
        actor: 'Mock Reviewer',
        createdAt: new Date().toISOString(),
        latencyMs: 12,
      }
      skill.latestTest = result
      return { skill, result }
    },
    async addComment(id, comment) {
      const skill = MOCK_SKILLS.find(item => item.id === id) ?? MOCK_SKILLS[0]
      skill.reviewHistory = [
        ...(skill.reviewHistory ?? []),
        { id: `comment-${Date.now()}`, type: 'comment', actor: 'Mock Reviewer', comment, createdAt: new Date().toISOString() },
      ]
      return skill
    },
    async submitReview(id, comment) {
      const skill = MOCK_SKILLS.find(item => item.id === id) ?? MOCK_SKILLS[0]
      skill.reviewStatus = 'in_review'
      skill.reviewHistory = [
        ...(skill.reviewHistory ?? []),
        { id: `submit-${Date.now()}`, type: 'submit_review', actor: 'Mock Reviewer', comment: comment ?? null, createdAt: new Date().toISOString() },
      ]
      return skill
    },
    async approve(id, comment) {
      const skill = MOCK_SKILLS.find(item => item.id === id) ?? MOCK_SKILLS[0]
      skill.reviewStatus = 'approved'
      skill.status = 'ready'
      skill.reviewHistory = [
        ...(skill.reviewHistory ?? []),
        { id: `approve-${Date.now()}`, type: 'approve', actor: 'Mock Reviewer', comment: comment ?? null, createdAt: new Date().toISOString() },
      ]
      return skill
    },
    async release(id, comment) {
      const skill = MOCK_SKILLS.find(item => item.id === id) ?? MOCK_SKILLS[0]
      skill.reviewStatus = 'released'
      skill.status = 'released'
      skill.reviewHistory = [
        ...(skill.reviewHistory ?? []),
        { id: `release-${Date.now()}`, type: 'release', actor: 'Mock Reviewer', comment: comment ?? null, createdAt: new Date().toISOString() },
      ]
      return skill
    },
  }
}
