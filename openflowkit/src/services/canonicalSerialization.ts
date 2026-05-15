import type { Edge, Node } from '@/lib/reactflowCompat';
import { getNodeParentId } from '@/lib/nodeParent';

export type ExportSerializationMode = 'deterministic' | 'legacy';

export function sortNodesCanonical<T extends Node>(nodes: T[]): T[] {
  return [...nodes].sort((a, b) => {
    const parentA = getNodeParentId(a);
    const parentB = getNodeParentId(b);
    if (parentA !== parentB) return parentA.localeCompare(parentB);
    return a.id.localeCompare(b.id);
  });
}

export function sortEdgesCanonical<T extends Edge>(edges: T[]): T[] {
  return [...edges].sort((a, b) => {
    if (a.source !== b.source) return a.source.localeCompare(b.source);
    if (a.target !== b.target) return a.target.localeCompare(b.target);
    return a.id.localeCompare(b.id);
  });
}

export function orderGraphForSerialization<TNode extends Node, TEdge extends Edge>(
  nodes: TNode[],
  edges: TEdge[],
  mode: ExportSerializationMode
): { nodes: TNode[]; edges: TEdge[] } {
  if (mode === 'legacy') {
    return {
      nodes: [...nodes],
      edges: [...edges],
    };
  }

  return {
    nodes: sortNodesCanonical(nodes),
    edges: sortEdgesCanonical(edges),
  };
}
