import {
  setStorageTelemetryHandler,
  type StorageTelemetryEvent,
} from './storageTelemetry';

type Logger = Pick<Console, 'debug'>;

export function createStorageTelemetrySink(
  isDev: boolean,
  logger: Logger = console
): ((event: StorageTelemetryEvent) => void) | null {
  if (!isDev) return null;
  return (event: StorageTelemetryEvent) => {
    logger.debug(
      `[storage:${event.area}] ${event.code} (${event.severity}) ${event.message}`
    );
  };
}

export function installStorageTelemetrySink(): void {
  const sink = createStorageTelemetrySink(import.meta.env.DEV);
  setStorageTelemetryHandler(sink);
}
