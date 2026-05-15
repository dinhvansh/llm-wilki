import type { FlowEdge, FlowNode } from '@/lib/types';
import type { LocalCollaborationOperationInput } from './runtimeController';

export interface CollaborationCanvasSnapshot {
  nodes: FlowNode[];
  edges: FlowEdge[];
}

function normalizeNodeForCollaboration(node: FlowNode): FlowNode {
  return {
    ...node,
    selected: false,
    dragging: false,
    resizing: false,
  };
}

function normalizeEdgeForCollaboration(edge: FlowEdge): FlowEdge {
  return {
    ...edge,
    selected: false,
  };
}

function areEqualByJson(left: unknown, right: unknown): boolean {
  return JSON.stringify(left) === JSON.stringify(right);
}

export function computeCollaborationOperationsFromCanvasChange(
  previous: CollaborationCanvasSnapshot,
  current: CollaborationCanvasSnapshot
): LocalCollaborationOperationInput[] {
  const operations: LocalCollaborationOperationInput[] = [];

  const previousNodesById = new Map(previous.nodes.map((node) => [node.id, normalizeNodeForCollaboration(node)]));
  const currentNodesById = new Map(current.nodes.map((node) => [node.id, normalizeNodeForCollaboration(node)]));
  const previousEdgesById = new Map(previous.edges.map((edge) => [edge.id, normalizeEdgeForCollaboration(edge)]));
  const currentEdgesById = new Map(current.edges.map((edge) => [edge.id, normalizeEdgeForCollaboration(edge)]));

  for (const previousNodeId of previousNodesById.keys()) {
    if (!currentNodesById.has(previousNodeId)) {
      operations.push({
        type: 'node.delete',
        payload: { nodeId: previousNodeId },
      });
    }
  }

  for (const previousEdgeId of previousEdgesById.keys()) {
    if (!currentEdgesById.has(previousEdgeId)) {
      operations.push({
        type: 'edge.delete',
        payload: { edgeId: previousEdgeId },
      });
    }
  }

  for (const [currentNodeId, currentNode] of currentNodesById.entries()) {
    const previousNode = previousNodesById.get(currentNodeId);
    if (!previousNode || !areEqualByJson(previousNode, currentNode)) {
      operations.push({
        type: 'node.upsert',
        payload: { node: currentNode },
      });
    }
  }

  for (const [currentEdgeId, currentEdge] of currentEdgesById.entries()) {
    const previousEdge = previousEdgesById.get(currentEdgeId);
    if (!previousEdge || !areEqualByJson(previousEdge, currentEdge)) {
      operations.push({
        type: 'edge.upsert',
        payload: { edge: currentEdge },
      });
    }
  }

  return operations;
}
