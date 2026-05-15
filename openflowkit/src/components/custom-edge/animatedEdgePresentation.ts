import type { CSSProperties } from 'react';
import type { EdgeAnimationConfig } from '@/lib/types';

interface ResolveAnimatedEdgePresentationParams {
  animatedExportEnabled: boolean;
  selected: boolean;
  hovered: boolean;
  edgeAnimated: boolean;
  animationConfig?: EdgeAnimationConfig;
  baseStyle: CSSProperties;
}

export interface AnimatedEdgePresentation {
  shouldRenderOverlay: boolean;
  overlayStyle: CSSProperties;
}

export function resolveAnimatedEdgePresentation({
  animatedExportEnabled,
  selected,
  hovered,
  edgeAnimated,
  animationConfig,
  baseStyle,
}: ResolveAnimatedEdgePresentationParams): AnimatedEdgePresentation {
  const overlayStyle: CSSProperties = {
    stroke: baseStyle.stroke,
    strokeWidth: Math.max(Number(baseStyle.strokeWidth ?? 2), 2),
    strokeDasharray: animationConfig?.dashArray
      ?? (typeof baseStyle.strokeDasharray === 'string' && baseStyle.strokeDasharray.length > 0
        ? baseStyle.strokeDasharray
        : '8 8'),
  };

  if (!animatedExportEnabled) {
    return {
      shouldRenderOverlay: selected || hovered,
      overlayStyle,
    };
  }

  const shouldRenderOverlay = edgeAnimated
    && animationConfig?.enabled === true
    && animationConfig.state === 'active';

  return {
    shouldRenderOverlay,
    overlayStyle: {
      ...overlayStyle,
      animationDuration: `${animationConfig?.durationMs ?? 600}ms`,
    },
  };
}
