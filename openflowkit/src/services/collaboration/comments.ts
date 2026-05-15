import { createId } from '@/lib/id';

export type CollaborationCommentAnchor =
  | { kind: 'node'; nodeId: string }
  | { kind: 'edge'; edgeId: string };

export interface CollaborationCommentEntry {
  id: string;
  threadId: string;
  authorClientId: string;
  message: string;
  createdAt: number;
}

export interface CollaborationCommentThread {
  id: string;
  roomId: string;
  anchor: CollaborationCommentAnchor;
  createdAt: number;
  resolvedAt: number | null;
  comments: CollaborationCommentEntry[];
}

export interface CollaborationCommentService {
  listThreads: () => CollaborationCommentThread[];
  listThreadsByAnchor: (anchor: CollaborationCommentAnchor) => CollaborationCommentThread[];
  addThread: (roomId: string, anchor: CollaborationCommentAnchor, authorClientId: string, message: string) => CollaborationCommentThread;
  addReply: (threadId: string, authorClientId: string, message: string) => CollaborationCommentThread | null;
  resolveThread: (threadId: string) => CollaborationCommentThread | null;
}

function isAnchorMatch(left: CollaborationCommentAnchor, right: CollaborationCommentAnchor): boolean {
  if (left.kind !== right.kind) {
    return false;
  }
  return left.kind === 'node'
    ? left.nodeId === (right as { nodeId: string }).nodeId
    : left.edgeId === (right as { edgeId: string }).edgeId;
}

function createEntry(threadId: string, authorClientId: string, message: string): CollaborationCommentEntry {
  return {
    id: createId('comment'),
    threadId,
    authorClientId,
    message,
    createdAt: Date.now(),
  };
}

export function createCollaborationCommentService(): CollaborationCommentService {
  const threads = new Map<string, CollaborationCommentThread>();

  return {
    listThreads: () => Array.from(threads.values()),
    listThreadsByAnchor: (anchor) => {
      return Array.from(threads.values()).filter((thread) => isAnchorMatch(thread.anchor, anchor));
    },
    addThread: (roomId, anchor, authorClientId, message) => {
      const threadId = createId('thread');
      const thread: CollaborationCommentThread = {
        id: threadId,
        roomId,
        anchor,
        createdAt: Date.now(),
        resolvedAt: null,
        comments: [createEntry(threadId, authorClientId, message)],
      };
      threads.set(threadId, thread);
      return thread;
    },
    addReply: (threadId, authorClientId, message) => {
      const existing = threads.get(threadId);
      if (!existing) return null;
      const updated: CollaborationCommentThread = {
        ...existing,
        comments: [...existing.comments, createEntry(threadId, authorClientId, message)],
      };
      threads.set(threadId, updated);
      return updated;
    },
    resolveThread: (threadId) => {
      const existing = threads.get(threadId);
      if (!existing) return null;
      const updated: CollaborationCommentThread = {
        ...existing,
        resolvedAt: Date.now(),
      };
      threads.set(threadId, updated);
      return updated;
    },
  };
}
