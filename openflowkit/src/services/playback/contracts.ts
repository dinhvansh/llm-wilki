import type { CSSProperties } from 'react';
import type { FlowNode, PlaybackState } from '@/lib/types';

export const PLAYBACK_STYLE_TRANSITION = 'all 0.5s ease';
const PLAYBACK_ROW_TOLERANCE_PX = 50;

export interface PlaybackStepViewport {
  duration: number;
  padding: number;
  minZoom: number;
  maxZoom: number;
}

export interface PlaybackStep {
  id: string;
  nodeId: string;
  durationMs: number;
  viewport: PlaybackStepViewport;
}

export interface PlaybackSequence {
  version: 1;
  steps: PlaybackStep[];
}

export type PlaybackStyleSnapshot = Record<string, CSSProperties | undefined>;

export function buildPlaybackSequence(nodes: FlowNode[], defaultDurationMs = 2000): PlaybackSequence {
  return buildPlaybackSequenceFromState(nodes, undefined, defaultDurationMs);
}

function buildPlaybackSequenceFromNodes(nodes: FlowNode[], defaultDurationMs: number): PlaybackSequence {
  const orderedNodes = [...nodes].sort((left, right) => {
    const yDiff = left.position.y - right.position.y;
    if (Math.abs(yDiff) > PLAYBACK_ROW_TOLERANCE_PX) {
      return yDiff;
    }

    return left.position.x - right.position.x;
  });

  return {
    version: 1,
    steps: orderedNodes.map((node) => ({
      id: `focus:${node.id}`,
      nodeId: node.id,
      durationMs: defaultDurationMs,
      viewport: {
        duration: 800,
        padding: 2,
        minZoom: 0.5,
        maxZoom: 1.5,
      },
    })),
  };
}

export function buildPlaybackSequenceFromState(
  nodes: FlowNode[],
  playback: PlaybackState | undefined,
  defaultDurationMs = 2000
): PlaybackSequence {
  if (!playback || playback.timeline.length === 0) {
    return buildPlaybackSequenceFromNodes(nodes, defaultDurationMs);
  }

  const nodeIds = new Set(nodes.map((node) => node.id));
  const scene = playback.selectedSceneId
    ? playback.scenes.find((candidate) => candidate.id === playback.selectedSceneId)
    : null;
  const allowedStepIds = scene ? new Set(scene.stepIds) : null;
  const sceneStepOrder = scene
    ? new Map(scene.stepIds.map((stepId, index) => [stepId, index]))
    : null;
  const playbackDefaultDurationMs = playback.defaultStepDurationMs > 0
    ? playback.defaultStepDurationMs
    : defaultDurationMs;

  const steps = playback.timeline
    .filter((step) => nodeIds.has(step.nodeId))
    .filter((step) => (allowedStepIds ? allowedStepIds.has(step.id) : true))
    .sort((left, right) => {
      if (!sceneStepOrder) {
        return 0;
      }

      return (sceneStepOrder.get(left.id) ?? Number.MAX_SAFE_INTEGER)
        - (sceneStepOrder.get(right.id) ?? Number.MAX_SAFE_INTEGER);
    })
    .map((step) => ({
      id: step.id,
      nodeId: step.nodeId,
      durationMs: step.durationMs ?? playbackDefaultDurationMs,
      viewport: {
        duration: 800,
        padding: 2,
        minZoom: 0.5,
        maxZoom: 1.5,
      },
    }));

  if (steps.length === 0) {
    return buildPlaybackSequenceFromNodes(nodes, defaultDurationMs);
  }

  return {
    version: 1,
    steps,
  };
}

export function capturePlaybackStyles(nodes: FlowNode[]): PlaybackStyleSnapshot {
  return nodes.reduce<PlaybackStyleSnapshot>((snapshot, node) => {
    snapshot[node.id] = node.style ?? {};
    return snapshot;
  }, {});
}

export function restorePlaybackStyles(
  nodes: FlowNode[],
  snapshot: PlaybackStyleSnapshot
): FlowNode[] {
  return nodes.map((node) => {
    const originalStyle = snapshot[node.id];
    return originalStyle ? { ...node, style: originalStyle } : node;
  });
}

export function applyPlaybackStepStyles(
  nodes: FlowNode[],
  step: PlaybackStep,
  snapshot: PlaybackStyleSnapshot
): FlowNode[] {
  return nodes.map((node) => {
    const baseStyle = snapshot[node.id] ?? node.style ?? {};
    const isActive = node.id === step.nodeId;

    return {
      ...node,
      style: {
        ...baseStyle,
        opacity: isActive ? 1 : 0.2,
        filter: isActive
          ? 'drop-shadow(0 0 12px var(--brand-primary))'
          : 'grayscale(100%)',
        transition: PLAYBACK_STYLE_TRANSITION,
      },
    };
  });
}
