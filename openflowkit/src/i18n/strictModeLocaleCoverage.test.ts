import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

type JsonMap = Record<string, unknown>;

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const LOCALES_DIR = path.join(__dirname, 'locales');

const LOCALES = ['en', 'de', 'es', 'fr', 'ja', 'tr', 'zh'] as const;

const STRICT_MODE_KEY_PATHS = [
  'commandBar.code.quickFixes',
  'commandBar.code.linePrefix',
  'commandBar.code.hintPrefix',
  'commandBar.code.strictModeGuidance.defineEndpoints',
  'commandBar.code.strictModeGuidance.uniqueIds',
  'commandBar.code.strictModeGuidance.edgeSyntax',
  'commandBar.code.strictModeGuidance.nodeSyntax',
  'commandBar.code.strictModeGuidance.fallback',
  'settingsModal.canvas.architectureStrictMode',
  'settingsModal.canvas.architectureStrictModeDesc',
  'flowCanvas.strictModePasteBlocked',
] as const;

function loadLocale(locale: typeof LOCALES[number]): JsonMap {
  const localePath = path.join(LOCALES_DIR, locale, 'translation.json');
  const raw = fs.readFileSync(localePath, 'utf8');
  return JSON.parse(raw) as JsonMap;
}

function getByPath(obj: JsonMap, dotPath: string): unknown {
  return dotPath.split('.').reduce<unknown>((current, segment) => {
    if (!current || typeof current !== 'object') {
      return undefined;
    }
    return (current as JsonMap)[segment];
  }, obj);
}

describe('strict-mode locale coverage', () => {
  it('has all strict-mode keys in every supported locale', () => {
    for (const locale of LOCALES) {
      const dict = loadLocale(locale);
      for (const keyPath of STRICT_MODE_KEY_PATHS) {
        const value = getByPath(dict, keyPath);
        expect(typeof value, `${locale}.${keyPath} should be a string`).toBe('string');
        expect((value as string).trim().length, `${locale}.${keyPath} should not be empty`).toBeGreaterThan(0);
      }
    }
  });

  it('has translated non-English values for strict-mode keys', () => {
    const enDict = loadLocale('en');

    for (const locale of LOCALES) {
      if (locale === 'en') continue;
      const dict = loadLocale(locale);

      for (const keyPath of STRICT_MODE_KEY_PATHS) {
        const enValue = getByPath(enDict, keyPath);
        const localeValue = getByPath(dict, keyPath);
        expect(localeValue, `${locale}.${keyPath} should differ from English`).not.toBe(enValue);
      }
    }
  });
});
