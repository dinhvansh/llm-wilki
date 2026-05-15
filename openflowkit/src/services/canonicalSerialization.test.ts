import { describe, expect, it } from 'vitest';
import type { FlowEdge, FlowNode } from '@/lib/types';
import { getNodeParentId, setNodeParent } from '@/lib/nodeParent';
import { orderGraphForSerialization, sortEdgesCanonical, sortNodesCanonical } from './canonicalSerialization';

function createNode(id: string, parentId?: string): FlowNode {
  const node: FlowNode = {
    id,
    type: 'process',
    position: { x: 0, y: 0 },
    data: { label: id },
  };
  if (!parentId) return node;
  return setNodeParent(node, parentId);
}

function createEdge(id: string, source: string, target: string): FlowEdge {
  return { id, source, target } as FlowEdge;
}

describe('canonicalSerialization', () => {
  it('sorts nodes by parent and then id', () => {
    const nodes = [
      createNode('n3', 'g2'),
      createNode('n2'),
      createNode('n1', 'g1'),
      createNode('n0'),
    ];
    const sorted = sortNodesCanonical(nodes);
    expect(sorted.map((node) => `${getNodeParentId(node) ?? ''}/${node.id}`)).toEqual([
      '/n0',
      '/n2',
      'g1/n1',
      'g2/n3',
    ]);
  });

  it('sorts edges by source, target, and id', () => {
    const edges = [
      createEdge('e2', 'b', 'a'),
      createEdge('e3', 'a', 'b'),
      createEdge('e1', 'a', 'b'),
    ];
    const sorted = sortEdgesCanonical(edges);
    expect(sorted.map((edge) => edge.id)).toEqual(['e1', 'e3', 'e2']);
  });

  it('preserves insertion order in legacy mode', () => {
    const nodes = [createNode('n2'), createNode('n1')];
    const edges = [createEdge('e2', 'b', 'a'), createEdge('e1', 'a', 'b')];

    const ordered = orderGraphForSerialization(nodes, edges, 'legacy');
    expect(ordered.nodes.map((node) => node.id)).toEqual(['n2', 'n1']);
    expect(ordered.edges.map((edge) => edge.id)).toEqual(['e2', 'e1']);
  });

  it('uses canonical ordering in deterministic mode', () => {
    const nodes = [createNode('n2'), createNode('n1')];
    const edges = [createEdge('e2', 'b', 'a'), createEdge('e1', 'a', 'b')];

    const ordered = orderGraphForSerialization(nodes, edges, 'deterministic');
    expect(ordered.nodes.map((node) => node.id)).toEqual(['n1', 'n2']);
    expect(ordered.edges.map((edge) => edge.id)).toEqual(['e1', 'e2']);
  });
});
