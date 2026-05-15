import type { CollaborationPresenceState } from './types';

export interface CollaborationPresenceViewModel {
  viewerCount: number;
  remotePresence: CollaborationPresenceState[];
}

export function buildCollaborationPresenceViewModel(
  presence: CollaborationPresenceState[],
  localClientId: string | null
): CollaborationPresenceViewModel {
  const remotePresence = localClientId
    ? presence.filter((entry) => entry.clientId !== localClientId)
    : presence;

  return {
    viewerCount: presence.length,
    remotePresence,
  };
}
