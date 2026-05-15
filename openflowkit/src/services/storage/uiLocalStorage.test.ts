import { describe, expect, it } from 'vitest';
import {
  readLocalStorageJson,
  readLocalStorageString,
  removeLocalStorageKey,
  writeLocalStorageJson,
  writeLocalStorageString,
} from './uiLocalStorage';

describe('uiLocalStorage', () => {
  it('reads and writes string values', () => {
    writeLocalStorageString('ui-test-key', 'hello');
    expect(readLocalStorageString('ui-test-key')).toBe('hello');
    removeLocalStorageKey('ui-test-key');
    expect(readLocalStorageString('ui-test-key')).toBeNull();
  });

  it('reads and writes JSON values with fallback', () => {
    writeLocalStorageJson('ui-json-key', { enabled: true });
    expect(readLocalStorageJson('ui-json-key', { enabled: false })).toEqual({ enabled: true });
    writeLocalStorageString('ui-json-key', '{bad json}');
    expect(readLocalStorageJson('ui-json-key', { enabled: false })).toEqual({ enabled: false });
    removeLocalStorageKey('ui-json-key');
  });
});
