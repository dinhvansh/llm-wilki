import { describe, expect, it } from 'vitest';
import { shouldUseOrthogonalRelationRouting } from './relationRoutingSemantics';

describe('shouldUseOrthogonalRelationRouting', () => {
  it('returns false when rollout is disabled', () => {
    expect(
      shouldUseOrthogonalRelationRouting(
        false,
        { classRelation: '-->' },
        { type: 'class' },
        { type: 'class' }
      )
    ).toBe(false);
  });

  it('returns true for relation-token edges when rollout is enabled', () => {
    expect(
      shouldUseOrthogonalRelationRouting(
        true,
        { classRelation: '-->' },
        { type: 'process' },
        { type: 'process' }
      )
    ).toBe(true);

    expect(
      shouldUseOrthogonalRelationRouting(
        true,
        { erRelation: '||--o{' },
        { type: 'process' },
        { type: 'process' }
      )
    ).toBe(true);
  });

  it('returns true for class/er graph endpoints even without explicit relation tokens', () => {
    expect(
      shouldUseOrthogonalRelationRouting(
        true,
        {},
        { type: 'class' },
        { type: 'er_entity' }
      )
    ).toBe(true);
  });

  it('returns false for non-class/er endpoints without explicit relation tokens', () => {
    expect(
      shouldUseOrthogonalRelationRouting(
        true,
        {},
        { type: 'process' },
        { type: 'decision' }
      )
    ).toBe(false);
  });
});
