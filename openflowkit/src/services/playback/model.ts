import type { PlaybackScene, PlaybackState, PlaybackTimelineStep } from '@/lib/types';

const PLAYBACK_STATE_VERSION = 1;
const DEFAULT_STEP_DURATION_MS = 2000;

function sanitizePlaybackScene(raw: unknown): PlaybackScene | null {
  if (!raw || typeof raw !== 'object') {
    return null;
  }

  const candidate = raw as Partial<PlaybackScene>;
  if (typeof candidate.id !== 'string' || candidate.id.length === 0) {
    return null;
  }
  if (typeof candidate.name !== 'string' || candidate.name.length === 0) {
    return null;
  }
  if (!Array.isArray(candidate.stepIds)) {
    return null;
  }

  return {
    id: candidate.id,
    name: candidate.name,
    stepIds: candidate.stepIds.filter((stepId): stepId is string => typeof stepId === 'string'),
    mode: candidate.mode === 'manual' ? 'manual' : 'auto',
  };
}

function sanitizePlaybackTimelineStep(raw: unknown): PlaybackTimelineStep | null {
  if (!raw || typeof raw !== 'object') {
    return null;
  }

  const candidate = raw as Partial<PlaybackTimelineStep>;
  if (typeof candidate.id !== 'string' || candidate.id.length === 0) {
    return null;
  }
  if (typeof candidate.nodeId !== 'string' || candidate.nodeId.length === 0) {
    return null;
  }

  return {
    id: candidate.id,
    nodeId: candidate.nodeId,
    durationMs: typeof candidate.durationMs === 'number' && candidate.durationMs > 0
      ? candidate.durationMs
      : undefined,
    sceneId: typeof candidate.sceneId === 'string' && candidate.sceneId.length > 0
      ? candidate.sceneId
      : undefined,
    emphasis: candidate.emphasis === 'focus' ? 'focus' : undefined,
  };
}

export function createEmptyPlaybackState(): PlaybackState {
  return {
    version: PLAYBACK_STATE_VERSION,
    scenes: [],
    timeline: [],
    selectedSceneId: null,
    defaultStepDurationMs: DEFAULT_STEP_DURATION_MS,
  };
}

export function clonePlaybackState(playback?: PlaybackState | null): PlaybackState | undefined {
  if (!playback) {
    return undefined;
  }

  return {
    version: PLAYBACK_STATE_VERSION,
    scenes: playback.scenes.map((scene) => ({
      ...scene,
      stepIds: [...scene.stepIds],
    })),
    timeline: playback.timeline.map((step) => ({ ...step })),
    selectedSceneId: playback.selectedSceneId,
    defaultStepDurationMs: playback.defaultStepDurationMs,
  };
}

export function sanitizePlaybackState(raw: unknown): PlaybackState | undefined {
  if (!raw || typeof raw !== 'object') {
    return undefined;
  }

  const candidate = raw as Partial<PlaybackState> & {
    scenes?: unknown;
    timeline?: unknown;
  };

  const scenes = Array.isArray(candidate.scenes)
    ? candidate.scenes
      .map((scene) => sanitizePlaybackScene(scene))
      .filter((scene): scene is PlaybackScene => scene !== null)
    : [];
  const timeline = Array.isArray(candidate.timeline)
    ? candidate.timeline
      .map((step) => sanitizePlaybackTimelineStep(step))
      .filter((step): step is PlaybackTimelineStep => step !== null)
    : [];

  return {
    version: PLAYBACK_STATE_VERSION,
    scenes,
    timeline,
    selectedSceneId: typeof candidate.selectedSceneId === 'string' ? candidate.selectedSceneId : null,
    defaultStepDurationMs:
      typeof candidate.defaultStepDurationMs === 'number' && candidate.defaultStepDurationMs > 0
        ? candidate.defaultStepDurationMs
        : DEFAULT_STEP_DURATION_MS,
  };
}
