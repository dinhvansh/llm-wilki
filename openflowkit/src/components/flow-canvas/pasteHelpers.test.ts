import { describe, expect, it } from 'vitest';
import {
  createPastedTextNode,
  isEditablePasteTarget,
  resolveLayoutDirection,
} from './pasteHelpers';

describe('pasteHelpers', () => {
  it('detects editable paste targets', () => {
    const input = document.createElement('input');
    const div = document.createElement('div');

    expect(isEditablePasteTarget(input)).toBe(true);
    expect(isEditablePasteTarget(div)).toBe(false);
    expect(isEditablePasteTarget(null)).toBe(false);
  });

  it('normalizes layout direction with safe fallback', () => {
    expect(resolveLayoutDirection({ direction: 'LR' })).toBe('LR');
    expect(resolveLayoutDirection({ metadata: { direction: 'BT' } })).toBe('BT');
    expect(resolveLayoutDirection({ direction: 'UNKNOWN' })).toBe('TB');
  });

  it('creates a pasted text node bound to active layer', () => {
    const node = createPastedTextNode('hello', { x: 10, y: 20 }, 'default');
    expect(node.position).toEqual({ x: 10, y: 20 });
    expect(node.data.label).toBe('hello');
    expect(node.data.layerId).toBe('default');
  });
});
