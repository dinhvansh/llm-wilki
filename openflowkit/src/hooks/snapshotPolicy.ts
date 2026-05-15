import type { FlowEdge, FlowNode, FlowSnapshot } from '@/lib/types';

export const SNAPSHOT_KIND_MANUAL = 'manual' as const;
export const SNAPSHOT_KIND_AUTO = 'auto' as const;

const AUTO_SNAPSHOT_PREFIX = 'Autosave';
const AUTO_SNAPSHOT_DEBOUNCE_MS = 1800;
const AUTO_SNAPSHOT_MIN_INTERVAL_MS = 45_000;
const MAX_MANUAL_SNAPSHOTS = 75;
const MAX_AUTO_SNAPSHOTS = 30;
const MAX_AUTO_SNAPSHOT_AGE_MS = 14 * 24 * 60 * 60 * 1000;

export function getAutoSnapshotDebounceMs(): number {
    return AUTO_SNAPSHOT_DEBOUNCE_MS;
}

export function getAutoSnapshotMinIntervalMs(): number {
    return AUTO_SNAPSHOT_MIN_INTERVAL_MS;
}

export function normalizeSnapshot(snapshot: FlowSnapshot): FlowSnapshot {
    return {
        ...snapshot,
        kind: snapshot.kind === SNAPSHOT_KIND_AUTO ? SNAPSHOT_KIND_AUTO : SNAPSHOT_KIND_MANUAL,
    };
}

function getSnapshotTimestampMs(snapshot: FlowSnapshot): number {
    const parsed = Date.parse(snapshot.timestamp);
    return Number.isFinite(parsed) ? parsed : 0;
}

function sortSnapshotsNewestFirst(snapshots: FlowSnapshot[]): FlowSnapshot[] {
    return [...snapshots].sort((left, right) => getSnapshotTimestampMs(right) - getSnapshotTimestampMs(left));
}

export function applySnapshotRetention(snapshots: FlowSnapshot[], nowMs = Date.now()): FlowSnapshot[] {
    const sortedSnapshots = sortSnapshotsNewestFirst(snapshots.map(normalizeSnapshot));
    const retainedManual = sortedSnapshots
        .filter((snapshot) => snapshot.kind === SNAPSHOT_KIND_MANUAL)
        .slice(0, MAX_MANUAL_SNAPSHOTS);
    const retainedAuto = sortedSnapshots
        .filter((snapshot) => snapshot.kind === SNAPSHOT_KIND_AUTO)
        .filter((snapshot) => nowMs - getSnapshotTimestampMs(snapshot) <= MAX_AUTO_SNAPSHOT_AGE_MS)
        .slice(0, MAX_AUTO_SNAPSHOTS);
    return sortSnapshotsNewestFirst([...retainedManual, ...retainedAuto]);
}

export function buildSnapshotName(kind: FlowSnapshot['kind'], timestampIso: string): string {
    if (kind === SNAPSHOT_KIND_AUTO) {
        const formatted = new Date(timestampIso).toLocaleString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
        });
        return `${AUTO_SNAPSHOT_PREFIX} • ${formatted}`;
    }
    return 'Snapshot';
}

export function buildCanvasFingerprint(nodes: FlowNode[], edges: FlowEdge[]): string {
    return JSON.stringify({ nodes, edges });
}
