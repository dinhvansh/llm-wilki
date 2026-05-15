import { describe, expect, it } from 'vitest';
import type { FlowEdge, FlowNode } from '@/lib/types';
import {
  addPlaybackScene,
  deletePlaybackScene,
  generatePlaybackStateFromGraph,
  getPlaybackStepsForSelectedScene,
  reorderPlaybackTimelineStep,
  togglePlaybackStepInScene,
} from './studio';

function createNode(id: string, x: number, y: number): FlowNode {
  return {
    id,
    type: 'process',
    position: { x, y },
    data: { label: id },
  } as FlowNode;
}

function createEdge(source: string, target: string): FlowEdge {
  return {
    id: `${source}-${target}`,
    source,
    target,
  } as FlowEdge;
}

describe('playback studio helpers', () => {
  it('generates a smart sequence using graph order when acyclic', () => {
    const playback = generatePlaybackStateFromGraph(
      [createNode('a', 0, 0), createNode('b', 100, 0), createNode('c', 200, 0)],
      [createEdge('a', 'b'), createEdge('b', 'c')],
      'smart'
    );

    expect(playback.timeline.map((step) => step.nodeId)).toEqual(['a', 'b', 'c']);
    expect(playback.scenes[0]?.mode).toBe('auto');
  });

  it('falls back to manual review mode when the graph contains a cycle', () => {
    const playback = generatePlaybackStateFromGraph(
      [createNode('a', 0, 0), createNode('b', 100, 0)],
      [createEdge('a', 'b'), createEdge('b', 'a')],
      'smart'
    );

    expect(playback.scenes[0]?.mode).toBe('manual');
  });

  it('can add, edit membership, and remove scenes while preserving selected scene order', () => {
    let playback = generatePlaybackStateFromGraph(
      [createNode('a', 0, 0), createNode('b', 100, 0)],
      [],
      'left-to-right'
    );

    playback = addPlaybackScene(playback, 'Branch');
    expect(playback.selectedSceneId).toBe('scene-2');

    playback = togglePlaybackStepInScene(playback, 'scene-2', 'step:b');
    expect(getPlaybackStepsForSelectedScene(playback).map((step) => step.nodeId)).toEqual(['a']);

    playback = deletePlaybackScene(playback, 'scene-2');
    expect(playback.selectedSceneId).toBe('scene-main');
  });

  it('reorders timeline steps and keeps scene order aligned', () => {
    let playback = generatePlaybackStateFromGraph(
      [createNode('a', 0, 0), createNode('b', 100, 0), createNode('c', 200, 0)],
      [],
      'left-to-right'
    );

    playback = reorderPlaybackTimelineStep(playback, 'step:c', 'up');
    expect(playback.timeline.map((step) => step.nodeId)).toEqual(['a', 'c', 'b']);
    expect(playback.scenes[0]?.stepIds).toEqual(['step:a', 'step:c', 'step:b']);
  });
});
