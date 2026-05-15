import { describe, expect, it } from 'vitest';
import { normalizeParseDiagnostics } from './diagnosticFormatting';

describe('normalizeParseDiagnostics', () => {
  it('normalizes line+snippet architecture diagnostics from string format', () => {
    const diagnostics = normalizeParseDiagnostics([
      'Invalid architecture edge syntax at line 8: "api -> db"',
    ]);

    expect(diagnostics).toEqual([
      {
        message: 'Invalid architecture edge syntax',
        line: 8,
        snippet: 'api -> db',
      },
    ]);
  });

  it('normalizes line-only architecture diagnostics from string format', () => {
    const diagnostics = normalizeParseDiagnostics([
      'Duplicate architecture node id "api" at line 5 (first defined at line 2)',
    ]);

    expect(diagnostics).toEqual([
      {
        message: 'Duplicate architecture node id "api" (first defined at line 2)',
        line: 5,
      },
    ]);
  });

  it('passes through structured diagnostics unchanged', () => {
    const diagnostics = normalizeParseDiagnostics([
      {
        message: 'No nodes found.',
        line: 1,
        snippet: 'flowchart TD',
        hint: 'Add a node declaration.',
      },
    ]);

    expect(diagnostics).toEqual([
      {
        message: 'No nodes found.',
        line: 1,
        snippet: 'flowchart TD',
        hint: 'Add a node declaration.',
      },
    ]);
  });

  it('returns empty array when input is not an array', () => {
    expect(normalizeParseDiagnostics(undefined)).toEqual([]);
    expect(normalizeParseDiagnostics(null)).toEqual([]);
    expect(normalizeParseDiagnostics('bad input')).toEqual([]);
  });
});
