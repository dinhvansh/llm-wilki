import { describe, expect, it } from 'vitest';
import type { FlowNode } from '@/lib/types';
import {
  applyPlaybackStepStyles,
  buildPlaybackSequence,
  buildPlaybackSequenceFromState,
  capturePlaybackStyles,
  restorePlaybackStyles,
} from './contracts';

function createNode(
  id: string,
  x: number,
  y: number,
  opacity = 0.8
): FlowNode {
  return {
    id,
    type: 'process',
    position: { x, y },
    data: { label: id },
    style: { opacity },
  } as FlowNode;
}

describe('playback contracts', () => {
  it('builds a stable sequence from top-to-bottom and left-to-right ordering', () => {
    const sequence = buildPlaybackSequence([
      createNode('b', 200, 0),
      createNode('c', 0, 100),
      createNode('a', 0, 0),
    ], 1500);

    expect(sequence.version).toBe(1);
    expect(sequence.steps.map((step) => step.nodeId)).toEqual(['a', 'b', 'c']);
    expect(sequence.steps[0].durationMs).toBe(1500);
  });

  it('captures and restores original node styles', () => {
    const nodes = [createNode('a', 0, 0, 0.6), createNode('b', 100, 0, 0.4)];
    const snapshot = capturePlaybackStyles(nodes);
    const modified = applyPlaybackStepStyles(nodes, buildPlaybackSequence(nodes).steps[0], snapshot);
    const restored = restorePlaybackStyles(modified, snapshot);

    expect(restored[0].style).toEqual({ opacity: 0.6 });
    expect(restored[1].style).toEqual({ opacity: 0.4 });
  });

  it('applies active and inactive playback emphasis from a stable base snapshot', () => {
    const nodes = [createNode('a', 0, 0), createNode('b', 100, 0)];
    const snapshot = capturePlaybackStyles(nodes);
    const step = buildPlaybackSequence(nodes).steps[1];
    const updated = applyPlaybackStepStyles(nodes, step, snapshot);

    expect(updated[0].style?.opacity).toBe(0.2);
    expect(updated[0].style?.filter).toBe('grayscale(100%)');
    expect(updated[1].style?.opacity).toBe(1);
    expect(updated[1].style?.filter).toContain('drop-shadow');
    expect(updated[1].style?.transition).toBe('all 0.5s ease');
  });

  it('uses persisted playback timeline order when available', () => {
    const nodes = [createNode('a', 0, 0), createNode('b', 100, 0)];
    const sequence = buildPlaybackSequenceFromState(nodes, {
      version: 1,
      scenes: [{ id: 'scene-1', name: 'Intro', stepIds: ['step-2', 'step-1'] }],
      timeline: [
        { id: 'step-1', nodeId: 'a', durationMs: 900 },
        { id: 'step-2', nodeId: 'b', durationMs: 1200 },
      ],
      selectedSceneId: 'scene-1',
      defaultStepDurationMs: 1500,
    });

    expect(sequence.steps.map((step) => step.nodeId)).toEqual(['b', 'a']);
    expect(sequence.steps.map((step) => step.durationMs)).toEqual([1200, 900]);
  });
});
