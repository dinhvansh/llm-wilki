import {
  FILE_EXTENSION_TO_LANGUAGE,
  type SupportedLanguage,
} from '@/hooks/ai-generation/codeToArchitecture';
import type { InfraFormat } from '@/services/infraSync/types';
import { z } from 'zod';

export type ImportCategory = 'sql' | 'infra' | 'openapi' | 'code' | 'codebase' | 'mermaid';

export const MAX_INPUT_BYTES = 200_000;
export const MAX_FILE_BYTES = 1_000_000;

const EXT_TO_CATEGORY: Record<string, ImportCategory> = {
  sql: 'sql',
  tfstate: 'infra',
  tf: 'infra',
  hcl: 'infra',
  mmd: 'mermaid',
  mermaid: 'mermaid',
};

function sniffJsonCategory(content: string): ImportCategory | null {
  try {
    const obj = JSON.parse(content) as Record<string, unknown>;
    if (typeof obj !== 'object' || obj === null) return null;
    if ('openapi' in obj || 'swagger' in obj) return 'openapi';
    if ('resources' in obj && 'version' in obj) return 'infra';
    if ('nodes' in obj && 'edges' in obj) return null; // JSON document — no category match
    return 'openapi'; // fallback for generic JSON
  } catch {
    return null;
  }
}

function sniffYamlCategory(content: string): ImportCategory | null {
  if (content.includes('openapi:') || content.includes('swagger:')) return 'openapi';
  if (
    content.includes('kind:') &&
    (content.includes('apiVersion:') || content.includes('metadata:'))
  )
    return 'infra';
  if (content.includes('services:') && (content.includes('image:') || content.includes('build:')))
    return 'infra';
  return 'infra'; // default yaml → infra
}

const MERMAID_HEADER_RE =
  /^(?:flowchart|graph|sequenceDiagram|classDiagram|erDiagram|stateDiagram|stateDiagram-v2|gitGraph|mindmap|journey|architecture|architecture-beta|block-beta|timeline|quadrantChart|requirementDiagram|C4Context)\b/m;

export function isMermaidContent(content: string): boolean {
  const firstLine = content
    .trim()
    .split('\n')
    .find((l) => l.trim() && !l.trim().startsWith('%%'));
  if (!firstLine) return false;
  return MERMAID_HEADER_RE.test(firstLine.trim());
}

const EXT_TO_LANGUAGE: Record<string, SupportedLanguage> = {};
const terraformStateSchema = z.object({
  version: z.unknown(),
  resources: z.unknown(),
});

for (const [ext, lang] of Object.entries(FILE_EXTENSION_TO_LANGUAGE)) {
  EXT_TO_LANGUAGE[ext] = lang;
}

export function detectCategoryFromExtension(filename: string): ImportCategory | null {
  const ext = filename.split('.').pop()?.toLowerCase() ?? '';
  if (EXT_TO_CATEGORY[ext]) return EXT_TO_CATEGORY[ext];
  if (EXT_TO_LANGUAGE[ext]) return 'code';
  return null;
}

export function detectCategoryFromContent(
  filename: string,
  content: string
): ImportCategory | null {
  const ext = filename.split('.').pop()?.toLowerCase() ?? '';

  if (ext === 'json') return sniffJsonCategory(content);
  if (ext === 'yaml' || ext === 'yml') return sniffYamlCategory(content);

  // Fall back to extension detection for all other types
  return detectCategoryFromExtension(filename);
}

export function detectInfraFormat(
  filename: string,
  content: string
): InfraFormat | 'terraform-hcl' {
  const lower = filename.toLowerCase();
  if (lower.endsWith('.tfstate') || lower.endsWith('.tf.json')) return 'terraform-state';
  if (
    lower === 'docker-compose.yml' ||
    lower === 'docker-compose.yaml' ||
    lower === 'compose.yml' ||
    lower === 'compose.yaml'
  )
    return 'docker-compose';
  if (lower.endsWith('.tf') || lower.endsWith('.hcl')) return 'terraform-hcl';
  if (lower.endsWith('.yaml') || lower.endsWith('.yml')) {
    if (
      content.includes('kind:') &&
      (content.includes('apiVersion:') || content.includes('metadata:'))
    )
      return 'kubernetes';
    if (content.includes('services:') && (content.includes('image:') || content.includes('build:')))
      return 'docker-compose';
    return 'kubernetes';
  }
  try {
    const parsed = terraformStateSchema.safeParse(JSON.parse(content));
    if (parsed.success) return 'terraform-state';
  } catch {
    /* not JSON */
  }
  return 'terraform-state';
}

export function detectLanguage(filename: string): SupportedLanguage {
  const ext = filename.split('.').pop()?.toLowerCase() ?? '';
  return EXT_TO_LANGUAGE[ext] ?? 'typescript';
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  return `${(bytes / 1024).toFixed(0)}KB`;
}
