import type { CollaborationDocumentState, CollaborationOperationEnvelope } from './types';

export type CollaborationVersionDecision = 'apply' | 'rebase' | 'defer' | 'reject';

export interface CollaborationVersionGuardResult {
  decision: CollaborationVersionDecision;
  reason: 'ok' | 'stale_base' | 'future_base' | 'room_mismatch';
}

export function guardCollaborationOperationVersion(
  state: CollaborationDocumentState,
  operation: CollaborationOperationEnvelope
): CollaborationVersionGuardResult {
  if (operation.roomId !== state.roomId) {
    return {
      decision: 'reject',
      reason: 'room_mismatch',
    };
  }

  if (operation.baseVersion === state.version) {
    return {
      decision: 'apply',
      reason: 'ok',
    };
  }

  if (operation.baseVersion < state.version) {
    return {
      decision: 'rebase',
      reason: 'stale_base',
    };
  }

  return {
    decision: 'rebase',
    reason: 'future_base',
  };
}

export function rebaseCollaborationOperation(
  state: CollaborationDocumentState,
  operation: CollaborationOperationEnvelope
): CollaborationOperationEnvelope {
  return {
    ...operation,
    baseVersion: state.version,
  };
}
