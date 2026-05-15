import { describe, expect, it } from 'vitest';
import { clonePlaybackState, createEmptyPlaybackState, sanitizePlaybackState } from './model';

describe('playback model', () => {
  it('creates an empty playback state with defaults', () => {
    expect(createEmptyPlaybackState()).toEqual({
      version: 1,
      scenes: [],
      timeline: [],
      selectedSceneId: null,
      defaultStepDurationMs: 2000,
    });
  });

  it('sanitizes persisted playback state while dropping malformed entries', () => {
    const playback = sanitizePlaybackState({
      scenes: [
        { id: 'scene-1', name: 'Intro', stepIds: ['step-1'], mode: 'manual' },
        { bogus: true },
      ],
      timeline: [
        { id: 'step-1', nodeId: 'node-1', durationMs: 1200, emphasis: 'focus' },
        { id: '', nodeId: 'bad' },
      ],
      selectedSceneId: 'scene-1',
      defaultStepDurationMs: 1400,
    });

    expect(playback?.scenes).toHaveLength(1);
    expect(playback?.timeline).toHaveLength(1);
    expect(playback?.selectedSceneId).toBe('scene-1');
    expect(playback?.defaultStepDurationMs).toBe(1400);
  });

  it('clones playback state deeply', () => {
    const original = sanitizePlaybackState({
      scenes: [{ id: 'scene-1', name: 'Intro', stepIds: ['step-1'] }],
      timeline: [{ id: 'step-1', nodeId: 'node-1' }],
    });
    const clone = clonePlaybackState(original);

    expect(clone).toEqual(original);
    expect(clone).not.toBe(original);
    expect(clone?.scenes).not.toBe(original?.scenes);
    expect(clone?.timeline).not.toBe(original?.timeline);
  });
});
