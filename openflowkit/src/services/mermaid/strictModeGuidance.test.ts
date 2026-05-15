import { describe, expect, it } from 'vitest';
import { buildArchitectureStrictModeGuidance } from './strictModeGuidance';

describe('buildArchitectureStrictModeGuidance', () => {
  it('maps strict-mode diagnostics to actionable quick fixes', () => {
    const guidance = buildArchitectureStrictModeGuidance([
      { message: 'Recovered implicit service node "cache" from edge reference.' },
      { message: 'Duplicate architecture node id "api" at line 5 (first defined at line 2)' },
      { message: 'Invalid architecture edge syntax at line 8: "api -> db"' },
    ]);

    expect(guidance.length).toBeGreaterThanOrEqual(3);
    expect(guidance.some((item) => item.key === 'commandBar.code.strictModeGuidance.defineEndpoints')).toBe(true);
    expect(guidance.some((item) => item.key === 'commandBar.code.strictModeGuidance.uniqueIds')).toBe(true);
    expect(guidance.some((item) => item.key === 'commandBar.code.strictModeGuidance.edgeSyntax')).toBe(true);
  });

  it('returns fallback guidance when diagnostics are not recognized', () => {
    const guidance = buildArchitectureStrictModeGuidance([{ message: 'Unknown parser issue' }]);
    expect(guidance).toHaveLength(1);
    expect(guidance[0].key).toBe('commandBar.code.strictModeGuidance.fallback');
  });
});
