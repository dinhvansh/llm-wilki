import { describe, expect, it, vi } from 'vitest';
import type { StorageTelemetryEvent } from './storageTelemetry';
import { createStorageTelemetrySink } from './storageTelemetrySink';

describe('storageTelemetrySink', () => {
  it('returns null sink when not in dev mode', () => {
    const sink = createStorageTelemetrySink(false);
    expect(sink).toBeNull();
  });

  it('logs telemetry events in dev mode', () => {
    const logger = { debug: vi.fn() };
    const sink = createStorageTelemetrySink(true, logger);
    expect(sink).not.toBeNull();

    const event: StorageTelemetryEvent = {
      area: 'schema',
      code: 'TEST',
      severity: 'warning',
      message: 'telemetry message',
    };
    sink?.(event);

    expect(logger.debug).toHaveBeenCalledWith(
      '[storage:schema] TEST (warning) telemetry message'
    );
  });
});
