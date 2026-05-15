import { describe, expect, it } from 'vitest';
import { parseMermaidByType } from './parseMermaidByType';
import { normalizeParseDiagnostics } from './diagnosticFormatting';
import {
  getLineSelectionRange,
  groupArchitectureStrictModeDiagnostics,
} from './strictModeDiagnosticsPresentation';
import { buildArchitectureStrictModeGuidance } from './strictModeGuidance';

const STRICT_MODE_STRESS_INPUT = `
architecture-beta
service api(server)[API]
service api(server)[API Duplicate]
service invalid node syntax
nonsense token row
api -> db
api --> cache
`;

describe('architecture strict-mode UX regression fixtures', () => {
  it('produces stable grouped diagnostics and guidance from stress corpus', () => {
    const result = parseMermaidByType(STRICT_MODE_STRESS_INPUT, { architectureStrictMode: true });

    expect(result.error).toContain('strict mode rejected');
    expect(result.nodes).toHaveLength(0);
    expect(result.edges).toHaveLength(0);

    const diagnostics = normalizeParseDiagnostics(result.diagnostics);
    expect(diagnostics.length).toBeGreaterThanOrEqual(4);

    const grouped = groupArchitectureStrictModeDiagnostics(diagnostics);
    expect(grouped.map((group) => group.id)).toEqual(['syntax', 'identity', 'recovery', 'general']);

    const guidance = buildArchitectureStrictModeGuidance(diagnostics);
    expect(guidance.some((item) => item.key === 'commandBar.code.strictModeGuidance.uniqueIds')).toBe(true);
    expect(guidance.some((item) => item.key === 'commandBar.code.strictModeGuidance.edgeSyntax')).toBe(true);
    expect(guidance.some((item) => item.key === 'commandBar.code.strictModeGuidance.defineEndpoints')).toBe(true);
  });

  it('keeps jump-to-line selection range aligned with parsed syntax diagnostics', () => {
    const result = parseMermaidByType(STRICT_MODE_STRESS_INPUT, { architectureStrictMode: true });
    const diagnostics = normalizeParseDiagnostics(result.diagnostics);
    const syntaxDiagnostic = diagnostics.find(
      (diagnostic) => diagnostic.message === 'Invalid architecture edge syntax'
    );

    expect(syntaxDiagnostic?.line).toBeTypeOf('number');
    expect(syntaxDiagnostic?.snippet).toBe('api -> db');
    if (!syntaxDiagnostic || typeof syntaxDiagnostic.line !== 'number') {
      throw new Error('Expected syntax diagnostic with line number');
    }

    const range = getLineSelectionRange(STRICT_MODE_STRESS_INPUT, syntaxDiagnostic.line);
    expect(range).not.toBeNull();
    if (!range) {
      throw new Error('Expected a valid selection range');
    }
    const selectedText = STRICT_MODE_STRESS_INPUT.slice(range.start, range.end).trim();
    expect(selectedText).toBe(syntaxDiagnostic.snippet);
  });
});
