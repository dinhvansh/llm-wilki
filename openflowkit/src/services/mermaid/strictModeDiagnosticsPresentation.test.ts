import { describe, expect, it } from 'vitest';
import {
  getLineSelectionRange,
  groupArchitectureStrictModeDiagnostics,
} from './strictModeDiagnosticsPresentation';

describe('groupArchitectureStrictModeDiagnostics', () => {
  it('groups diagnostics into stable strict-mode categories', () => {
    const groups = groupArchitectureStrictModeDiagnostics([
      { message: 'Invalid architecture edge syntax at line 8: "api -> db"', line: 8 },
      { message: 'Duplicate architecture node id "api" at line 5', line: 5 },
      { message: 'Recovered implicit service node "cache" from edge reference.' },
      { message: 'Unknown parser issue' },
    ]);

    expect(groups.map((group) => group.id)).toEqual(['syntax', 'identity', 'recovery', 'general']);
    expect(groups[0].diagnostics).toHaveLength(1);
    expect(groups[1].diagnostics).toHaveLength(1);
    expect(groups[2].diagnostics).toHaveLength(1);
    expect(groups[3].diagnostics).toHaveLength(1);
  });
});

describe('getLineSelectionRange', () => {
  const source = ['line one', 'line two', 'line three'].join('\n');

  it('returns start/end selection range for valid line numbers', () => {
    expect(getLineSelectionRange(source, 2)).toEqual({ start: 9, end: 17 });
    expect(getLineSelectionRange(source, 3)).toEqual({ start: 18, end: 28 });
  });

  it('returns null for invalid line numbers', () => {
    expect(getLineSelectionRange(source, 0)).toBeNull();
    expect(getLineSelectionRange(source, 4)).toBeNull();
    expect(getLineSelectionRange(source, -1)).toBeNull();
  });
});
