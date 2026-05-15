import { describe, expect, it } from 'vitest';
import { createCollaborationCommentService } from './comments';

describe('collaboration comment service', () => {
  it('creates and lists threads by anchor', () => {
    const service = createCollaborationCommentService();
    const thread = service.addThread('room-1', { kind: 'node', nodeId: 'n-1' }, 'client-a', 'First');

    expect(service.listThreads()).toHaveLength(1);
    const byAnchor = service.listThreadsByAnchor({ kind: 'node', nodeId: 'n-1' });
    expect(byAnchor).toHaveLength(1);
    expect(byAnchor[0].id).toBe(thread.id);
  });

  it('adds replies to existing thread', () => {
    const service = createCollaborationCommentService();
    const thread = service.addThread('room-1', { kind: 'edge', edgeId: 'e-1' }, 'client-a', 'First');
    const updated = service.addReply(thread.id, 'client-b', 'Reply');

    expect(updated).not.toBeNull();
    expect(updated?.comments).toHaveLength(2);
  });

  it('resolves a thread', () => {
    const service = createCollaborationCommentService();
    const thread = service.addThread('room-1', { kind: 'node', nodeId: 'n-2' }, 'client-a', 'Open');
    const resolved = service.resolveThread(thread.id);

    expect(resolved?.resolvedAt).not.toBeNull();
  });
});
