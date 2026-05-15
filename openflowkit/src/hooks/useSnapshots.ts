import { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { FlowNode, FlowEdge, FlowSnapshot } from '@/lib/types';
import { createId } from '@/lib/id';
import { loadSnapshots, saveSnapshots } from '@/services/storage/snapshotStorage';
import {
    SNAPSHOT_KIND_AUTO,
    SNAPSHOT_KIND_MANUAL,
    applySnapshotRetention,
    buildCanvasFingerprint,
    buildSnapshotName,
    getAutoSnapshotDebounceMs,
    getAutoSnapshotMinIntervalMs,
    normalizeSnapshot,
} from './snapshotPolicy';

function cloneSnapshotData<T>(value: T): T {
    return JSON.parse(JSON.stringify(value)) as T;
}

function isManualSnapshot(snapshot: FlowSnapshot): boolean {
    return normalizeSnapshot(snapshot).kind === SNAPSHOT_KIND_MANUAL;
}

function isAutoSnapshot(snapshot: FlowSnapshot): boolean {
    return normalizeSnapshot(snapshot).kind === SNAPSHOT_KIND_AUTO;
}

export const useSnapshots = () => {
    const [snapshots, setSnapshots] = useState<FlowSnapshot[]>([]);
    const hasHydratedRef = useRef(false);
    const hasSeenCanvasRef = useRef(false);
    const lastCanvasFingerprintRef = useRef<string | null>(null);
    const lastAutoSnapshotAtRef = useRef(0);
    const autoSnapshotTimerRef = useRef<number | null>(null);
    const flushPendingAutoSnapshotRef = useRef<() => void>(() => {});
    const pendingAutoSnapshotRef = useRef<{
        nodes: FlowNode[];
        edges: FlowEdge[];
        fingerprint: string;
    } | null>(null);

    const persistSnapshots = useCallback((nextSnapshots: FlowSnapshot[]) => {
        void saveSnapshots(nextSnapshots);
    }, []);

    const flushPendingAutoSnapshot = useCallback(() => {
        if (!hasHydratedRef.current) {
            return;
        }
        const pendingAutoSnapshot = pendingAutoSnapshotRef.current;
        if (!pendingAutoSnapshot) {
            return;
        }

        const now = Date.now();
        const elapsedMs = now - lastAutoSnapshotAtRef.current;
        const minIntervalMs = getAutoSnapshotMinIntervalMs();
        if (elapsedMs < minIntervalMs) {
            autoSnapshotTimerRef.current = window.setTimeout(() => {
                autoSnapshotTimerRef.current = null;
                flushPendingAutoSnapshotRef.current();
            }, minIntervalMs - elapsedMs);
            return;
        }

        const timestamp = new Date(now).toISOString();
        const autoSnapshot: FlowSnapshot = {
            id: createId('snapshot'),
            name: buildSnapshotName(SNAPSHOT_KIND_AUTO, timestamp),
            timestamp,
            kind: SNAPSHOT_KIND_AUTO,
            nodes: pendingAutoSnapshot.nodes,
            edges: pendingAutoSnapshot.edges,
        };

        setSnapshots((previousSnapshots) => {
            const updatedSnapshots = applySnapshotRetention([autoSnapshot, ...previousSnapshots], now);
            persistSnapshots(updatedSnapshots);
            return updatedSnapshots;
        });

        lastAutoSnapshotAtRef.current = now;
        lastCanvasFingerprintRef.current = pendingAutoSnapshot.fingerprint;
        pendingAutoSnapshotRef.current = null;
    }, [persistSnapshots]);

    useEffect(() => {
        flushPendingAutoSnapshotRef.current = flushPendingAutoSnapshot;
    }, [flushPendingAutoSnapshot]);

    useEffect(() => {
        let cancelled = false;
        void loadSnapshots().then((persistedSnapshots) => {
            if (!cancelled) {
                setSnapshots(applySnapshotRetention(persistedSnapshots.map(normalizeSnapshot)));
                hasHydratedRef.current = true;
            }
        });
        return () => {
            cancelled = true;
        };
    }, []);

    useEffect(() => {
        return () => {
            if (autoSnapshotTimerRef.current !== null) {
                window.clearTimeout(autoSnapshotTimerRef.current);
            }
        };
    }, []);

    const saveSnapshot = useCallback((name: string, nodes: FlowNode[], edges: FlowEdge[]) => {
        const timestamp = new Date().toISOString();
        const newSnapshot: FlowSnapshot = {
            id: createId('snapshot'),
            name,
            timestamp,
            kind: SNAPSHOT_KIND_MANUAL,
            nodes: cloneSnapshotData(nodes),
            edges: cloneSnapshotData(edges),
        };

        setSnapshots(prev => {
            const updated = applySnapshotRetention([newSnapshot, ...prev]);
            persistSnapshots(updated);
            return updated;
        });
    }, [persistSnapshots]);

    const deleteSnapshot = useCallback((id: string) => {
        setSnapshots(prev => {
            const updated = prev.filter(s => s.id !== id);
            persistSnapshots(updated);
            return updated;
        });
    }, [persistSnapshots]);

    const queueAutoSnapshot = useCallback((nodes: FlowNode[], edges: FlowEdge[]) => {
        if (!hasHydratedRef.current) {
            return;
        }

        const fingerprint = buildCanvasFingerprint(nodes, edges);
        if (!hasSeenCanvasRef.current) {
            hasSeenCanvasRef.current = true;
            lastCanvasFingerprintRef.current = fingerprint;
            return;
        }
        if (fingerprint === lastCanvasFingerprintRef.current) {
            return;
        }
        if (nodes.length === 0 && edges.length === 0) {
            lastCanvasFingerprintRef.current = fingerprint;
            return;
        }

        pendingAutoSnapshotRef.current = {
            fingerprint,
            nodes: cloneSnapshotData(nodes),
            edges: cloneSnapshotData(edges),
        };

        if (autoSnapshotTimerRef.current !== null) {
            window.clearTimeout(autoSnapshotTimerRef.current);
        }
        autoSnapshotTimerRef.current = window.setTimeout(() => {
            autoSnapshotTimerRef.current = null;
            flushPendingAutoSnapshot();
        }, getAutoSnapshotDebounceMs());
    }, [flushPendingAutoSnapshot]);

    const restoreSnapshot = useCallback((snapshot: FlowSnapshot, setNodes: (n: FlowNode[]) => void, setEdges: (e: FlowEdge[]) => void) => {
        // Deep copy to avoid reference issues
        const nodesCopy = cloneSnapshotData(snapshot.nodes);
        const edgesCopy = cloneSnapshotData(snapshot.edges);
        setNodes(nodesCopy);
        setEdges(edgesCopy);
    }, []);

    const manualSnapshots = useMemo(
        () => snapshots.filter(isManualSnapshot),
        [snapshots]
    );
    const autoSnapshots = useMemo(
        () => snapshots.filter(isAutoSnapshot),
        [snapshots]
    );

    return {
        snapshots,
        manualSnapshots,
        autoSnapshots,
        saveSnapshot,
        deleteSnapshot,
        queueAutoSnapshot,
        restoreSnapshot,
    };
};
