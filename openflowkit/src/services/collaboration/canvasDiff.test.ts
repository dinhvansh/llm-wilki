import { describe, expect, it } from 'vitest';
import type { FlowEdge, FlowNode } from '@/lib/types';
import { computeCollaborationOperationsFromCanvasChange } from './canvasDiff';

function createNode(id: string, overrides: Partial<FlowNode> = {}): FlowNode {
  return {
    id,
    type: 'custom',
    position: { x: 0, y: 0 },
    data: { label: id },
    ...overrides,
  };
}

function createEdge(id: string, overrides: Partial<FlowEdge> = {}): FlowEdge {
  return {
    id,
    source: 'a',
    target: 'b',
    ...overrides,
  };
}

describe('computeCollaborationOperationsFromCanvasChange', () => {
  it('emits upsert/delete operations for structural canvas changes', () => {
    const previous = {
      nodes: [createNode('n-1')],
      edges: [createEdge('e-1')],
    };
    const current = {
      nodes: [createNode('n-2')],
      edges: [createEdge('e-2')],
    };

    const operations = computeCollaborationOperationsFromCanvasChange(previous, current);
    expect(operations).toEqual([
      { type: 'node.delete', payload: { nodeId: 'n-1' } },
      { type: 'edge.delete', payload: { edgeId: 'e-1' } },
      { type: 'node.upsert', payload: { node: createNode('n-2', { selected: false, dragging: false, resizing: false }) } },
      { type: 'edge.upsert', payload: { edge: createEdge('e-2', { selected: false }) } },
    ]);
  });

  it('ignores selection-only changes to avoid noisy collaboration churn', () => {
    const previous = {
      nodes: [createNode('n-1', { selected: false })],
      edges: [createEdge('e-1', { selected: false })],
    };
    const current = {
      nodes: [createNode('n-1', { selected: true })],
      edges: [createEdge('e-1', { selected: true })],
    };

    const operations = computeCollaborationOperationsFromCanvasChange(previous, current);
    expect(operations).toEqual([]);
  });
});
