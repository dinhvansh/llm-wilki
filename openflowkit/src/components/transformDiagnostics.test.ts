import { describe, expect, it } from 'vitest';
import { getTransformDiagnosticsAttrs } from './transformDiagnostics';

describe('transform diagnostics attributes', () => {
  it('returns diagnostics attributes in test mode', () => {
    const attrs = getTransformDiagnosticsAttrs({
      nodeFamily: 'custom',
      selected: true,
      compact: true,
      minHeight: 120,
      actualHeight: 96,
      hasIcon: true,
      hasSubLabel: false,
    });

    expect(attrs['data-transform-diagnostics']).toBe('1');
    expect(attrs['data-transform-family']).toBe('custom');
    expect(attrs['data-transform-selected']).toBe('1');
    expect(attrs['data-transform-compact']).toBe('1');
    expect(attrs['data-transform-min-height']).toBe('120');
    expect(attrs['data-transform-actual-height']).toBe('96');
    expect(attrs['data-transform-has-icon']).toBe('1');
    expect(attrs['data-transform-has-sublabel']).toBe('0');
  });
});
