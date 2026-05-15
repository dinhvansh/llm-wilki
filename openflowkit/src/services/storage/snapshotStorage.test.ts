import { afterEach, describe, expect, it } from 'vitest';
import type { FlowSnapshot } from '@/lib/types';
import { loadSnapshots, saveSnapshots } from './snapshotStorage';

const SNAPSHOT_KEY = 'flowmind_snapshots';

function createSnapshot(id: string): FlowSnapshot {
  return {
    id,
    name: `Snapshot ${id}`,
    timestamp: '2026-03-05T00:00:00.000Z',
    nodes: [],
    edges: [],
  };
}

describe('snapshotStorage local fallback', () => {
  const originalIndexedDb = globalThis.indexedDB;

  afterEach(() => {
    localStorage.removeItem(SNAPSHOT_KEY);
    if (typeof originalIndexedDb === 'undefined') {
      delete (globalThis as { indexedDB?: IDBFactory }).indexedDB;
    } else {
      globalThis.indexedDB = originalIndexedDb;
    }
  });

  it('loads snapshots from localStorage when IndexedDB is unavailable', async () => {
    delete (globalThis as { indexedDB?: IDBFactory }).indexedDB;
    const expected = [createSnapshot('snap-1')];
    localStorage.setItem(SNAPSHOT_KEY, JSON.stringify(expected));

    const loaded = await loadSnapshots();

    expect(loaded).toEqual(expected);
  });

  it('saves snapshots to localStorage when IndexedDB is unavailable', async () => {
    delete (globalThis as { indexedDB?: IDBFactory }).indexedDB;
    const expected = [createSnapshot('snap-2')];

    await saveSnapshots(expected);

    expect(localStorage.getItem(SNAPSHOT_KEY)).toBe(JSON.stringify(expected));
  });
});
