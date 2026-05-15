import type { FlowNode } from '@/lib/types';

export interface QueryState {
    text: string;
    nodeType: string;
    shape: string;
    color: string;
    labelContains: string;
    metadataKey: string;
    metadataValue: string;
}

export const EMPTY_QUERY: QueryState = {
    text: '',
    nodeType: '',
    shape: '',
    color: '',
    labelContains: '',
    metadataKey: '',
    metadataValue: '',
};

export function matchesNodeQuery(node: FlowNode, query: QueryState): boolean {
    const text = query.text.trim().toLowerCase();
    const labelContains = query.labelContains.trim().toLowerCase();
    const metadataKey = query.metadataKey.trim();
    const metadataValue = query.metadataValue.trim().toLowerCase();

    const label = (node.data?.label || '').toLowerCase();
    const subLabel = (node.data?.subLabel || '').toLowerCase();
    const nodeId = (node.id || '').toLowerCase();
    const nodeType = node.type || '';
    const shape = String(node.data?.shape || '');
    const color = String(node.data?.color || '');

    if (text && !label.includes(text) && !subLabel.includes(text) && !nodeId.includes(text)) {
        return false;
    }
    if (query.nodeType && nodeType !== query.nodeType) {
        return false;
    }
    if (query.shape && shape !== query.shape) {
        return false;
    }
    if (query.color && color !== query.color) {
        return false;
    }
    if (labelContains && !label.includes(labelContains)) {
        return false;
    }
    if (metadataKey) {
        const nodeData = (node.data ?? {}) as Record<string, unknown>;
        const metadataRaw = nodeData[metadataKey];
        if (metadataRaw === undefined || metadataRaw === null) {
            return false;
        }
        if (metadataValue && !String(metadataRaw).toLowerCase().includes(metadataValue)) {
            return false;
        }
    }
    return true;
}
