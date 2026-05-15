import type {
  CollaborationDocumentState,
  CollaborationOperationEnvelope,
  CollaborationPresenceState,
} from './types';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

export function isCollaborationOperationEnvelope(value: unknown): value is CollaborationOperationEnvelope {
  if (!isRecord(value)) return false;
  if (typeof value.opId !== 'string') return false;
  if (typeof value.roomId !== 'string') return false;
  if (typeof value.clientId !== 'string') return false;
  if (typeof value.baseVersion !== 'number') return false;
  if (typeof value.timestamp !== 'number') return false;
  if (typeof value.type !== 'string') return false;
  if (!isRecord(value.payload)) return false;
  return true;
}

export function isCollaborationDocumentState(value: unknown): value is CollaborationDocumentState {
  if (!isRecord(value)) return false;
  if (typeof value.roomId !== 'string') return false;
  if (typeof value.version !== 'number') return false;
  if (!Array.isArray(value.nodes)) return false;
  if (!Array.isArray(value.edges)) return false;
  return true;
}

export function isCollaborationPresenceState(value: unknown): value is CollaborationPresenceState {
  if (!isRecord(value)) return false;
  if (typeof value.clientId !== 'string') return false;
  if (typeof value.name !== 'string') return false;
  if (typeof value.color !== 'string') return false;
  if (!isRecord(value.cursor)) return false;
  if (typeof value.cursor.x !== 'number') return false;
  if (typeof value.cursor.y !== 'number') return false;
  return true;
}
