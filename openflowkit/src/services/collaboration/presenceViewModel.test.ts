import { describe, expect, it } from 'vitest';
import { buildCollaborationPresenceViewModel } from './presenceViewModel';

describe('collaboration presence view model', () => {
  it('computes viewer count and filters local presence from remote list', () => {
    const result = buildCollaborationPresenceViewModel(
      [
        { clientId: 'local', name: 'Local', color: '#111111', cursor: { x: 0, y: 0 } },
        { clientId: 'remote-a', name: 'A', color: '#222222', cursor: { x: 10, y: 20 } },
      ],
      'local'
    );

    expect(result.viewerCount).toBe(2);
    expect(result.remotePresence.map((entry) => entry.clientId)).toEqual(['remote-a']);
  });
});
