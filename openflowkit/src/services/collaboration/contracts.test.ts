import { describe, expect, it } from 'vitest';
import {
  isCollaborationDocumentState,
  isCollaborationOperationEnvelope,
  isCollaborationPresenceState,
} from './contracts';

describe('collaboration contracts', () => {
  it('accepts valid operation envelope shape', () => {
    const value = {
      opId: 'op-1',
      roomId: 'room-1',
      clientId: 'client-1',
      baseVersion: 5,
      timestamp: Date.now(),
      type: 'node.upsert',
      payload: { nodeId: 'n-1' },
    };

    expect(isCollaborationOperationEnvelope(value)).toBe(true);
  });

  it('rejects invalid document state shape', () => {
    const value = {
      roomId: 'room-1',
      version: '5',
      nodes: [],
      edges: [],
    };

    expect(isCollaborationDocumentState(value)).toBe(false);
  });

  it('accepts valid presence state shape', () => {
    const value = {
      clientId: 'client-1',
      name: 'Varun',
      color: '#6366f1',
      cursor: { x: 100, y: 200 },
    };

    expect(isCollaborationPresenceState(value)).toBe(true);
  });
});
