import type { FlowDocument, FlowEdge, FlowNode, FlowPage } from './types'

export function emptyFlowDocument(title: string, objective = '', owner = 'Current User'): FlowDocument {
  return {
    version: '1.0',
    engine: 'openflowkit',
    family: 'flowchart',
    pages: [
      {
        id: 'page-main',
        name: 'Main',
        lanes: [
          { id: 'lane-editor', label: owner, x: 80, width: 260 },
          { id: 'lane-system', label: 'System', x: 380, width: 260 },
        ],
        nodes: [
          { id: 'start', type: 'start', label: 'Start', owner, position: { x: 80, y: 120 }, size: { width: 180, height: 60 } },
          { id: 'task-1', type: 'task', label: 'Define the first step', owner, position: { x: 80, y: 260 }, size: { width: 220, height: 72 } },
          { id: 'end', type: 'end', label: 'Done', owner: 'System', position: { x: 380, y: 400 }, size: { width: 180, height: 60 } },
        ],
        edges: [
          { id: 'edge-1', source: 'start', target: 'task-1', type: 'smoothstep' },
          { id: 'edge-2', source: 'task-1', target: 'end', type: 'smoothstep' },
        ],
        groups: [],
        viewport: { x: 0, y: 0, zoom: 1 },
      },
    ],
    metadata: { title, objective, owner, sourceIds: [], sourcePageIds: [], reviewStatus: 'needs_review', openQuestions: [], citations: [] },
  }
}

export function firstFlowPage(document?: FlowDocument | null): FlowPage {
  const page = document?.pages?.[0]
  return page ?? { id: 'page-main', name: 'Main', lanes: [], nodes: [], edges: [], groups: [], viewport: {} }
}

export function updateFirstFlowPage(document: FlowDocument, patch: Partial<FlowPage>): FlowDocument {
  const page = firstFlowPage(document)
  return {
    ...document,
    pages: [{ ...page, ...patch }, ...(document.pages ?? []).slice(1)],
  }
}

export function updateFlowMetadata(document: FlowDocument, patch: Partial<FlowDocument['metadata']>): FlowDocument {
  return { ...document, metadata: { ...(document.metadata ?? {}), ...patch } }
}

export function flowNodeTypeLabel(type: string): string {
  if (type === 'start') return 'Start'
  if (type === 'end') return 'End'
  if (type === 'decision') return 'Decision'
  if (type === 'handoff') return 'Handoff'
  return 'Task'
}

export function makeFlowNode(index: number, type = 'task'): FlowNode {
  return {
    id: `${type}-${Date.now()}-${index}`,
    type,
    label: type === 'decision' ? 'Decision?' : `New ${flowNodeTypeLabel(type)}`,
    owner: 'System',
    position: { x: 120 + (index % 3) * 260, y: 160 + index * 80 },
    size: { width: type === 'decision' ? 180 : 220, height: 72 },
  }
}

export function makeFlowEdge(source: string, target: string, index: number): FlowEdge {
  return { id: `edge-${Date.now()}-${index}`, source, target, type: 'smoothstep', label: '' }
}
