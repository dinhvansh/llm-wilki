export interface TransformDiagnosticsInput {
  nodeFamily: string;
  selected: boolean;
  compact?: boolean;
  minHeight?: number;
  actualHeight?: number;
  hasIcon?: boolean;
  hasSubLabel?: boolean;
}

function isDiagnosticsEnabled(): boolean {
  return import.meta.env.MODE === 'test' || import.meta.env.VITE_TRANSFORM_DIAGNOSTICS === '1';
}

export function getTransformDiagnosticsAttrs(input: TransformDiagnosticsInput): Record<string, string> {
  if (!isDiagnosticsEnabled()) {
    return {};
  }

  return {
    'data-transform-diagnostics': '1',
    'data-transform-family': input.nodeFamily,
    'data-transform-selected': input.selected ? '1' : '0',
    'data-transform-compact': input.compact ? '1' : '0',
    'data-transform-min-height': input.minHeight !== undefined ? String(input.minHeight) : '',
    'data-transform-actual-height': input.actualHeight !== undefined ? String(input.actualHeight) : '',
    'data-transform-has-icon': input.hasIcon ? '1' : '0',
    'data-transform-has-sublabel': input.hasSubLabel ? '1' : '0',
  };
}
