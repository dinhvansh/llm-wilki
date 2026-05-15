export const COLLAB_ROOM_QUERY_PARAM = 'room';
export const COLLAB_SECRET_QUERY_PARAM = 'secret';

export interface ResolvedCollaborationRoom {
  roomId: string;
  roomSecret: string | null;
  shouldWriteToUrl: boolean;
}

function createShortRoomId(seed: string): string {
  let hash = 0;
  for (let index = 0; index < seed.length; index += 1) {
    hash = ((hash << 5) - hash) + seed.charCodeAt(index);
    hash |= 0;
  }
  const normalized = Math.abs(hash).toString(36);
  return `room-${normalized.slice(0, 8)}`;
}

export function resolveCollaborationRoomId(search: string, fallbackRoomId: string): ResolvedCollaborationRoom {
  const params = new URLSearchParams(search);
  const roomParam = params.get(COLLAB_ROOM_QUERY_PARAM)?.trim() ?? '';
  const secretParam = params.get(COLLAB_SECRET_QUERY_PARAM)?.trim() ?? '';
  if (roomParam.length > 0) {
    return {
      roomId: roomParam,
      roomSecret: secretParam.length > 0 ? secretParam : null,
      shouldWriteToUrl: false,
    };
  }

  return {
    roomId: createShortRoomId(fallbackRoomId),
    roomSecret: null,
    shouldWriteToUrl: true,
  };
}

export function buildCollaborationInviteUrl(currentHref: string, roomId: string, roomSecret: string): string {
  const url = new URL(currentHref);
  url.searchParams.set(COLLAB_ROOM_QUERY_PARAM, roomId);
  if (roomSecret !== roomId) {
    url.searchParams.set(COLLAB_SECRET_QUERY_PARAM, roomSecret);
  } else {
    url.searchParams.delete(COLLAB_SECRET_QUERY_PARAM);
  }
  return url.toString();
}
