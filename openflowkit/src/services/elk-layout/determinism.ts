import type { FlowEdge, FlowNode } from '@/lib/types';
import { getNodeParentId } from '@/lib/nodeParent';
import type { NormalizedLayoutInputs } from './types';

function buildComponentOrderIndex(nodes: FlowNode[], edges: FlowEdge[]): Map<string, number> {
    const nodeIds = nodes.map((node) => node.id).sort((a, b) => a.localeCompare(b));
    const nodeIdSet = new Set(nodeIds);
    const adjacency = new Map<string, string[]>();

    for (const nodeId of nodeIds) {
        adjacency.set(nodeId, []);
    }

    for (const edge of edges) {
        if (!nodeIdSet.has(edge.source) || !nodeIdSet.has(edge.target)) continue;
        adjacency.get(edge.source)?.push(edge.target);
        adjacency.get(edge.target)?.push(edge.source);
    }

    for (const [nodeId, neighbors] of adjacency.entries()) {
        neighbors.sort((a, b) => a.localeCompare(b));
        adjacency.set(nodeId, neighbors);
    }

    const visited = new Set<string>();
    const componentOrder = new Map<string, number>();
    let componentIndex = 0;

    for (const startNodeId of nodeIds) {
        if (visited.has(startNodeId)) continue;

        const queue = [startNodeId];
        visited.add(startNodeId);

        while (queue.length > 0) {
            const current = queue.shift();
            if (!current) continue;
            componentOrder.set(current, componentIndex);

            const neighbors = adjacency.get(current) || [];
            for (const neighbor of neighbors) {
                if (visited.has(neighbor)) continue;
                visited.add(neighbor);
                queue.push(neighbor);
            }
        }

        componentIndex += 1;
    }

    return componentOrder;
}

export function normalizeLayoutInputsForDeterminism(nodes: FlowNode[], edges: FlowEdge[]): NormalizedLayoutInputs {
    const sortedNodes = [...nodes].sort((a, b) => a.id.localeCompare(b.id));
    const componentOrderIndex = buildComponentOrderIndex(sortedNodes, edges);
    const childrenByParent = new Map<string, FlowNode[]>();
    const topLevelNodes: FlowNode[] = [];

    for (const node of sortedNodes) {
        const parentId = getNodeParentId(node);
        if (!parentId) {
            topLevelNodes.push(node);
            continue;
        }
        const children = childrenByParent.get(parentId) || [];
        children.push(node);
        childrenByParent.set(parentId, children);
    }

    const sortNodesByComponentAndId = (a: FlowNode, b: FlowNode): number => {
        const aComponent = componentOrderIndex.get(a.id) ?? Number.POSITIVE_INFINITY;
        const bComponent = componentOrderIndex.get(b.id) ?? Number.POSITIVE_INFINITY;
        if (aComponent !== bComponent) return aComponent - bComponent;
        return a.id.localeCompare(b.id);
    };

    topLevelNodes.sort(sortNodesByComponentAndId);
    for (const [parentId, children] of childrenByParent.entries()) {
        children.sort(sortNodesByComponentAndId);
        childrenByParent.set(parentId, children);
    }

    const sortedEdges = [...edges].sort((a, b) => {
        const aSourceComponent = componentOrderIndex.get(a.source) ?? Number.POSITIVE_INFINITY;
        const bSourceComponent = componentOrderIndex.get(b.source) ?? Number.POSITIVE_INFINITY;
        if (aSourceComponent !== bSourceComponent) return aSourceComponent - bSourceComponent;

        const aTargetComponent = componentOrderIndex.get(a.target) ?? Number.POSITIVE_INFINITY;
        const bTargetComponent = componentOrderIndex.get(b.target) ?? Number.POSITIVE_INFINITY;
        if (aTargetComponent !== bTargetComponent) return aTargetComponent - bTargetComponent;

        if (a.source !== b.source) return a.source.localeCompare(b.source);
        if (a.target !== b.target) return a.target.localeCompare(b.target);
        return a.id.localeCompare(b.id);
    });

    return { topLevelNodes, childrenByParent, sortedEdges };
}
