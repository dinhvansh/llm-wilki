import { describe, expect, it } from 'vitest';
import type { FlowNode } from '@/lib/types';
import { EMPTY_QUERY, matchesNodeQuery, type QueryState } from './searchQuery';

function createNode(overrides?: Partial<FlowNode>): FlowNode {
    return {
        id: 'n-1',
        type: 'process',
        position: { x: 0, y: 0 },
        data: {
            label: 'API Gateway',
            subLabel: 'edge layer',
            shape: 'rounded',
            color: 'blue',
            env: 'prod',
        },
        ...overrides,
    } as FlowNode;
}

describe('matchesNodeQuery', () => {
    it('matches with empty query', () => {
        const node = createNode();
        expect(matchesNodeQuery(node, EMPTY_QUERY)).toBe(true);
    });

    it('matches by node type and shape', () => {
        const node = createNode();
        const query: QueryState = {
            ...EMPTY_QUERY,
            nodeType: 'process',
            shape: 'rounded',
        };
        expect(matchesNodeQuery(node, query)).toBe(true);
    });

    it('matches label and metadata filters', () => {
        const node = createNode();
        const query: QueryState = {
            ...EMPTY_QUERY,
            labelContains: 'gateway',
            metadataKey: 'env',
            metadataValue: 'pro',
        };
        expect(matchesNodeQuery(node, query)).toBe(true);
    });

    it('does not match when metadata key is missing', () => {
        const node = createNode();
        const query: QueryState = {
            ...EMPTY_QUERY,
            metadataKey: 'team',
        };
        expect(matchesNodeQuery(node, query)).toBe(false);
    });

    it('does not match with different color', () => {
        const node = createNode();
        const query: QueryState = {
            ...EMPTY_QUERY,
            color: 'red',
        };
        expect(matchesNodeQuery(node, query)).toBe(false);
    });
});
