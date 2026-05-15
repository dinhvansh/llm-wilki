import { describe, expect, it } from 'vitest';
import { resolveAnimatedEdgePresentation } from './animatedEdgePresentation';

describe('animated edge presentation', () => {
  it('preserves hover and selection overlays when animated export is disabled', () => {
    const result = resolveAnimatedEdgePresentation({
      animatedExportEnabled: false,
      selected: true,
      hovered: false,
      edgeAnimated: false,
      baseStyle: { stroke: '#000', strokeWidth: 1.5 },
    });

    expect(result.shouldRenderOverlay).toBe(true);
    expect(result.overlayStyle.strokeDasharray).toBe('8 8');
  });

  it('only renders active configured overlays when animated export is enabled', () => {
    const result = resolveAnimatedEdgePresentation({
      animatedExportEnabled: true,
      selected: true,
      hovered: true,
      edgeAnimated: true,
      animationConfig: {
        enabled: true,
        state: 'active',
        durationMs: 1400,
        dashArray: '12 6',
      },
      baseStyle: { stroke: '#123456', strokeWidth: 2 },
    });

    expect(result.shouldRenderOverlay).toBe(true);
    expect(result.overlayStyle.animationDuration).toBe('1400ms');
    expect(result.overlayStyle.strokeDasharray).toBe('12 6');
  });

  it('suppresses overlays for idle animated edges when the new pipeline is enabled', () => {
    const result = resolveAnimatedEdgePresentation({
      animatedExportEnabled: true,
      selected: true,
      hovered: true,
      edgeAnimated: true,
      animationConfig: {
        enabled: true,
        state: 'idle',
      },
      baseStyle: { stroke: '#123456', strokeWidth: 2 },
    });

    expect(result.shouldRenderOverlay).toBe(false);
  });
});
