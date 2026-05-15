import { describe, expect, it } from 'vitest';
import type { FlowEdge, FlowNode, FlowSnapshot } from '@/lib/types';
import {
    SNAPSHOT_KIND_AUTO,
    SNAPSHOT_KIND_MANUAL,
    applySnapshotRetention,
    buildCanvasFingerprint,
    normalizeSnapshot,
} from './snapshotPolicy';

function createSnapshot(index: number, kind?: FlowSnapshot['kind'], ageMs = 0): FlowSnapshot {
    return {
        id: `snapshot-${index}`,
        name: `Snapshot ${index}`,
        timestamp: new Date(Date.now() - ageMs).toISOString(),
        kind,
        nodes: [],
        edges: [],
    };
}

describe('snapshotPolicy', () => {
    it('normalizes snapshots to manual by default', () => {
        const normalized = normalizeSnapshot(createSnapshot(1));
        expect(normalized.kind).toBe(SNAPSHOT_KIND_MANUAL);
    });

    it('retains only fresh autosaved snapshots', () => {
        const now = Date.now();
        const veryOld = 20 * 24 * 60 * 60 * 1000;
        const retained = applySnapshotRetention(
            [
                createSnapshot(1, SNAPSHOT_KIND_AUTO, 60_000),
                createSnapshot(2, SNAPSHOT_KIND_AUTO, veryOld),
                createSnapshot(3, SNAPSHOT_KIND_MANUAL, veryOld),
            ],
            now
        );

        expect(retained.some((snapshot) => snapshot.id === 'snapshot-2')).toBe(false);
        expect(retained.some((snapshot) => snapshot.id === 'snapshot-1')).toBe(true);
        expect(retained.some((snapshot) => snapshot.id === 'snapshot-3')).toBe(true);
    });

    it('builds stable fingerprints for identical canvases', () => {
        const nodes: FlowNode[] = [{ id: 'n1', type: 'process', position: { x: 10, y: 20 }, data: { label: 'A' } }];
        const edges: FlowEdge[] = [{ id: 'e1', source: 'n1', target: 'n2' }];

        const first = buildCanvasFingerprint(nodes, edges);
        const second = buildCanvasFingerprint(nodes, edges);

        expect(first).toBe(second);
    });
});
