import type { FlowEdge, FlowNode, PlaybackScene, PlaybackState, PlaybackTimelineStep } from '@/lib/types';
import { createEmptyPlaybackState } from './model';

export type PlaybackGenerationPreset = 'smart' | 'top-to-bottom' | 'left-to-right' | 'reverse';

function createStepId(nodeId: string): string {
  return `step:${nodeId}`;
}

function compareByPosition(
  nodesById: Map<string, FlowNode>,
  orientation: 'TB' | 'LR'
): (leftId: string, rightId: string) => number {
  return (leftId, rightId) => {
    const left = nodesById.get(leftId);
    const right = nodesById.get(rightId);
    if (!left || !right) {
      return leftId.localeCompare(rightId);
    }

    if (orientation === 'LR') {
      const xDiff = left.position.x - right.position.x;
      if (Math.abs(xDiff) > 10) return xDiff;
      return left.position.y - right.position.y || leftId.localeCompare(rightId);
    }

    const yDiff = left.position.y - right.position.y;
    if (Math.abs(yDiff) > 10) return yDiff;
    return left.position.x - right.position.x || leftId.localeCompare(rightId);
  };
}

function inferOrientation(nodes: FlowNode[]): 'TB' | 'LR' {
  if (nodes.length <= 1) {
    return 'TB';
  }

  const xs = nodes.map((node) => node.position.x);
  const ys = nodes.map((node) => node.position.y);
  const width = Math.max(...xs) - Math.min(...xs);
  const height = Math.max(...ys) - Math.min(...ys);
  return width > height ? 'LR' : 'TB';
}

function topologicalSortNodes(nodes: FlowNode[], edges: FlowEdge[]): { orderedNodeIds: string[]; hasCycle: boolean } {
  const nodeIds = new Set(nodes.map((node) => node.id));
  const indegree = new Map<string, number>();
  const adjacency = new Map<string, string[]>();
  const nodesById = new Map(nodes.map((node) => [node.id, node]));
  const orientation = inferOrientation(nodes);
  const compare = compareByPosition(nodesById, orientation);

  for (const node of nodes) {
    indegree.set(node.id, 0);
    adjacency.set(node.id, []);
  }

  for (const edge of edges) {
    if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target) || edge.source === edge.target) {
      continue;
    }

    adjacency.get(edge.source)?.push(edge.target);
    indegree.set(edge.target, (indegree.get(edge.target) ?? 0) + 1);
  }

  const queue = [...nodes.map((node) => node.id).filter((id) => (indegree.get(id) ?? 0) === 0)].sort(compare);
  const orderedNodeIds: string[] = [];

  while (queue.length > 0) {
    const nextId = queue.shift()!;
    orderedNodeIds.push(nextId);

    const neighbors = adjacency.get(nextId) ?? [];
    for (const neighbor of neighbors) {
      const nextIndegree = (indegree.get(neighbor) ?? 1) - 1;
      indegree.set(neighbor, nextIndegree);
      if (nextIndegree === 0) {
        queue.push(neighbor);
        queue.sort(compare);
      }
    }
  }

  return {
    orderedNodeIds: orderedNodeIds.length === nodes.length
      ? orderedNodeIds
      : [...nodes.map((node) => node.id)].sort(compare),
    hasCycle: orderedNodeIds.length !== nodes.length,
  };
}

function sortNodeIdsByPreset(nodes: FlowNode[], edges: FlowEdge[], preset: PlaybackGenerationPreset): { orderedNodeIds: string[]; hasCycle: boolean } {
  const nodesById = new Map(nodes.map((node) => [node.id, node]));
  const orientation = inferOrientation(nodes);

  switch (preset) {
    case 'left-to-right':
      return {
        orderedNodeIds: [...nodes.map((node) => node.id)].sort(compareByPosition(nodesById, 'LR')),
        hasCycle: false,
      };
    case 'top-to-bottom':
      return {
        orderedNodeIds: [...nodes.map((node) => node.id)].sort(compareByPosition(nodesById, 'TB')),
        hasCycle: false,
      };
    case 'reverse': {
      const base = [...nodes.map((node) => node.id)].sort(compareByPosition(nodesById, orientation));
      return { orderedNodeIds: base.reverse(), hasCycle: false };
    }
    case 'smart':
    default:
      return topologicalSortNodes(nodes, edges);
  }
}

function sortSceneStepIdsByTimeline(scene: PlaybackScene, timeline: PlaybackTimelineStep[]): PlaybackScene {
  const order = new Map(timeline.map((step, index) => [step.id, index]));
  return {
    ...scene,
    stepIds: [...scene.stepIds].sort((left, right) => (order.get(left) ?? Number.MAX_SAFE_INTEGER) - (order.get(right) ?? Number.MAX_SAFE_INTEGER)),
  };
}

export function generatePlaybackStateFromGraph(
  nodes: FlowNode[],
  edges: FlowEdge[],
  preset: PlaybackGenerationPreset,
  existingPlayback?: PlaybackState
): PlaybackState {
  const base = existingPlayback ? { ...existingPlayback } : createEmptyPlaybackState();
  const { orderedNodeIds, hasCycle } = sortNodeIdsByPreset(nodes, edges, preset);
  const timeline = orderedNodeIds.map<PlaybackTimelineStep>((nodeId) => ({
    id: createStepId(nodeId),
    nodeId,
    durationMs: existingPlayback?.timeline.find((step) => step.nodeId === nodeId)?.durationMs ?? base.defaultStepDurationMs,
    sceneId: 'scene-main',
    emphasis: 'focus',
  }));
  const scenes: PlaybackScene[] = [{
    id: 'scene-main',
    name: hasCycle && preset === 'smart' ? 'Manual Review' : 'Main Flow',
    stepIds: timeline.map((step) => step.id),
    mode: hasCycle && preset === 'smart' ? 'manual' : 'auto',
  }];

  return {
    version: 1,
    scenes,
    timeline,
    selectedSceneId: 'scene-main',
    defaultStepDurationMs: base.defaultStepDurationMs,
  };
}

export function addPlaybackScene(playback: PlaybackState, name?: string): PlaybackState {
  const nextSceneId = `scene-${playback.scenes.length + 1}`;
  const nextScene: PlaybackScene = {
    id: nextSceneId,
    name: name ?? `Scene ${playback.scenes.length + 1}`,
    stepIds: playback.timeline.map((step) => step.id),
    mode: 'manual',
  };

  return {
    ...playback,
    scenes: [...playback.scenes, nextScene],
    selectedSceneId: nextSceneId,
  };
}

export function renamePlaybackScene(playback: PlaybackState, sceneId: string, name: string): PlaybackState {
  return {
    ...playback,
    scenes: playback.scenes.map((scene) => scene.id === sceneId ? { ...scene, name } : scene),
  };
}

export function selectPlaybackScene(playback: PlaybackState, sceneId: string | null): PlaybackState {
  return {
    ...playback,
    selectedSceneId: sceneId,
  };
}

export function deletePlaybackScene(playback: PlaybackState, sceneId: string): PlaybackState {
  const scenes = playback.scenes.filter((scene) => scene.id !== sceneId);
  return {
    ...playback,
    scenes,
    selectedSceneId: playback.selectedSceneId === sceneId ? scenes[0]?.id ?? null : playback.selectedSceneId,
  };
}

export function togglePlaybackStepInScene(playback: PlaybackState, sceneId: string, stepId: string): PlaybackState {
  return {
    ...playback,
    scenes: playback.scenes.map((scene) => {
      if (scene.id !== sceneId) {
        return scene;
      }

      const hasStep = scene.stepIds.includes(stepId);
      const stepIds = hasStep
        ? scene.stepIds.filter((candidate) => candidate !== stepId)
        : [...scene.stepIds, stepId];

      return {
        ...scene,
        stepIds: sortSceneStepIdsByTimeline({ ...scene, stepIds }, playback.timeline).stepIds,
        mode: 'manual',
      };
    }),
  };
}

export function reorderPlaybackTimelineStep(
  playback: PlaybackState,
  stepId: string,
  direction: 'up' | 'down'
): PlaybackState {
  const index = playback.timeline.findIndex((step) => step.id === stepId);
  if (index === -1) {
    return playback;
  }

  const targetIndex = direction === 'up' ? index - 1 : index + 1;
  if (targetIndex < 0 || targetIndex >= playback.timeline.length) {
    return playback;
  }

  const timeline = [...playback.timeline];
  const [step] = timeline.splice(index, 1);
  timeline.splice(targetIndex, 0, step);

  return {
    ...playback,
    timeline,
    scenes: playback.scenes.map((scene) => sortSceneStepIdsByTimeline({ ...scene, mode: 'manual' }, timeline)),
  };
}

export function setPlaybackStepDuration(playback: PlaybackState, stepId: string, durationMs: number): PlaybackState {
  return {
    ...playback,
    timeline: playback.timeline.map((step) => step.id === stepId ? { ...step, durationMs } : step),
  };
}

export function setPlaybackDefaultDuration(playback: PlaybackState, durationMs: number): PlaybackState {
  return {
    ...playback,
    defaultStepDurationMs: durationMs,
  };
}

export function getPlaybackStepsForSelectedScene(playback: PlaybackState): PlaybackTimelineStep[] {
  if (!playback.selectedSceneId) {
    return playback.timeline;
  }

  const scene = playback.scenes.find((candidate) => candidate.id === playback.selectedSceneId);
  if (!scene) {
    return playback.timeline;
  }

  const stepOrder = new Map(scene.stepIds.map((stepId, index) => [stepId, index]));
  return playback.timeline
    .filter((step) => stepOrder.has(step.id))
    .sort((left, right) => (stepOrder.get(left.id) ?? Number.MAX_SAFE_INTEGER) - (stepOrder.get(right.id) ?? Number.MAX_SAFE_INTEGER));
}
