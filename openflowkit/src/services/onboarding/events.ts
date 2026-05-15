import { captureAnalyticsEvent } from '@/services/analytics/analytics';
import {
  parseOnboardingEventLog,
  parseOnboardingFirstSeenMap,
} from './eventSchemas';

export type OnboardingEventName =
  | 'welcome_template_selected'
  | 'welcome_import_selected'
  | 'welcome_blank_selected'
  | 'welcome_prompt_selected'
  | 'template_inserted'
  | 'ai_key_saved'
  | 'first_export_completed'
  | 'first_share_opened';

export interface OnboardingEvent {
  name: OnboardingEventName;
  at: string;
  first: boolean;
  detail?: Record<string, string | number | boolean>;
}

const EVENT_LOG_STORAGE_KEY = 'openflowkit_onboarding_events';
const EVENT_FIRST_SEEN_STORAGE_KEY = 'openflowkit_onboarding_event_firsts';
const MAX_STORED_EVENTS = 100;

function readStorageValue(key: string): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorageValue(key: string, value: string): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Ignore local-only instrumentation failures.
  }
}

function readEventLog(): OnboardingEvent[] {
  const raw = readStorageValue(EVENT_LOG_STORAGE_KEY);
  if (!raw) return [];

  try {
    return parseOnboardingEventLog(JSON.parse(raw));
  } catch {
    return [];
  }
}

function readFirstSeenMap(): Partial<Record<OnboardingEventName, true>> {
  const raw = readStorageValue(EVENT_FIRST_SEEN_STORAGE_KEY);
  if (!raw) return {};

  try {
    return parseOnboardingFirstSeenMap(JSON.parse(raw));
  } catch {
    return {};
  }
}

export function recordOnboardingEvent(
  name: OnboardingEventName,
  detail?: Record<string, string | number | boolean>
): OnboardingEvent {
  const firstSeen = readFirstSeenMap();
  const event: OnboardingEvent = {
    name,
    at: new Date().toISOString(),
    first: firstSeen[name] !== true,
    detail,
  };

  const events = readEventLog();
  const nextEvents = [...events, event].slice(-MAX_STORED_EVENTS);
  writeStorageValue(EVENT_LOG_STORAGE_KEY, JSON.stringify(nextEvents));

  if (event.first) {
    writeStorageValue(
      EVENT_FIRST_SEEN_STORAGE_KEY,
      JSON.stringify({
        ...firstSeen,
        [name]: true,
      })
    );
  }

  captureAnalyticsEvent(name, {
    first: event.first,
    ...detail,
  });

  return event;
}

export function getOnboardingEvents(): OnboardingEvent[] {
  return readEventLog();
}

export interface OnboardingActionSuggestion {
  action: 'blank' | 'ai' | 'import' | 'templates';
  eventName: OnboardingEventName;
  lastUsedAt: string;
}

const ACTION_EVENT_PRIORITY: Record<OnboardingActionSuggestion['action'], OnboardingEventName[]> = {
  blank: ['welcome_blank_selected'],
  ai: ['welcome_prompt_selected'],
  import: ['welcome_import_selected'],
  templates: ['welcome_template_selected', 'template_inserted'],
};

export function getRecentOnboardingActionSuggestions(
  limit = 3
): OnboardingActionSuggestion[] {
  const events = readEventLog().slice().reverse();
  const suggestions: OnboardingActionSuggestion[] = [];
  const seenActions = new Set<OnboardingActionSuggestion['action']>();

  for (const event of events) {
    const action = (Object.entries(ACTION_EVENT_PRIORITY).find(([, eventNames]) =>
      eventNames.includes(event.name)
    )?.[0] ?? null) as OnboardingActionSuggestion['action'] | null;

    if (!action || seenActions.has(action)) {
      continue;
    }

    seenActions.add(action);
    suggestions.push({
      action,
      eventName: event.name,
      lastUsedAt: event.at,
    });

    if (suggestions.length >= limit) {
      break;
    }
  }

  return suggestions;
}

export function clearOnboardingEvents(): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem(EVENT_LOG_STORAGE_KEY);
    window.localStorage.removeItem(EVENT_FIRST_SEEN_STORAGE_KEY);
  } catch {
    // Ignore cleanup failures in local-only instrumentation.
  }
}
