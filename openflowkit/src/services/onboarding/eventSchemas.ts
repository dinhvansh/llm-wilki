import { z } from 'zod';
import type { OnboardingEvent, OnboardingEventName } from './events';

const onboardingEventNameSchema = z.enum([
  'welcome_template_selected',
  'welcome_import_selected',
  'welcome_blank_selected',
  'welcome_prompt_selected',
  'template_inserted',
  'ai_key_saved',
  'first_export_completed',
  'first_share_opened',
] satisfies [OnboardingEventName, ...OnboardingEventName[]]);

const onboardingEventSchema = z.object({
  name: onboardingEventNameSchema,
  at: z.string(),
  first: z.boolean(),
  detail: z.record(z.union([z.string(), z.number(), z.boolean()])).optional(),
});

const onboardingFirstSeenSchema = z.record(z.literal(true));

export function parseOnboardingEventLog(value: unknown): OnboardingEvent[] {
  const parsed = z.array(onboardingEventSchema).safeParse(value);
  if (!parsed.success) {
    return [];
  }

  return parsed.data.map((event): OnboardingEvent => ({
    name: event.name,
    at: event.at,
    first: event.first,
    detail: event.detail,
  }));
}

export function parseOnboardingFirstSeenMap(
  value: unknown
): Partial<Record<OnboardingEventName, true>> {
  const parsed = onboardingFirstSeenSchema.safeParse(value);
  if (!parsed.success) {
    return {};
  }

  return parsed.data as Partial<Record<OnboardingEventName, true>>;
}
