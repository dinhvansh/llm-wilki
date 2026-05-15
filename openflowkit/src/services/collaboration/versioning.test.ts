import { describe, expect, it } from 'vitest';
import type { CollaborationDocumentState, CollaborationOperationEnvelope } from './types';
import { guardCollaborationOperationVersion, rebaseCollaborationOperation } from './versioning';

function createOperation(baseVersion: number, roomId = 'room-1'): CollaborationOperationEnvelope {
  return {
    opId: `op-${baseVersion}`,
    roomId,
    clientId: 'client-1',
    baseVersion,
    timestamp: 1,
    type: 'node.delete',
    payload: { nodeId: 'n-1' },
  };
}

describe('collaboration versioning', () => {
  const state: CollaborationDocumentState = {
    roomId: 'room-1',
    version: 4,
    nodes: [],
    edges: [],
  };

  it('applies operation when baseVersion matches', () => {
    const result = guardCollaborationOperationVersion(state, createOperation(4));
    expect(result).toEqual({ decision: 'apply', reason: 'ok' });
  });

  it('requests rebase when operation baseVersion is stale', () => {
    const operation = createOperation(2);
    const result = guardCollaborationOperationVersion(state, operation);

    expect(result).toEqual({ decision: 'rebase', reason: 'stale_base' });
    const rebased = rebaseCollaborationOperation(state, operation);
    expect(rebased.baseVersion).toBe(4);
    expect(rebased.opId).toBe(operation.opId);
  });

  it('rebases operation when baseVersion is from a future state', () => {
    const result = guardCollaborationOperationVersion(state, createOperation(8));
    expect(result).toEqual({ decision: 'rebase', reason: 'future_base' });
  });

  it('rejects operation from different room', () => {
    const result = guardCollaborationOperationVersion(state, createOperation(4, 'room-2'));
    expect(result).toEqual({ decision: 'reject', reason: 'room_mismatch' });
  });
});
