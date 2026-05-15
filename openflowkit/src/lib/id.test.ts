import { afterEach, describe, expect, it, vi } from 'vitest';
import { createId } from './id';

const originalCryptoDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'crypto');

function restoreCrypto(): void {
    if (originalCryptoDescriptor) {
        Object.defineProperty(globalThis, 'crypto', originalCryptoDescriptor);
        return;
    }

    Reflect.deleteProperty(globalThis, 'crypto');
}

describe('createId', () => {
    afterEach(() => {
        vi.restoreAllMocks();
        restoreCrypto();
    });

    it('uses native randomUUID when available', () => {
        const randomUUID = vi.fn(() => 'native-id');
        Object.defineProperty(globalThis, 'crypto', {
            value: { randomUUID },
            configurable: true,
        });

        expect(createId('node')).toBe('node-native-id');
        expect(randomUUID).toHaveBeenCalledOnce();
    });

    it('falls back when randomUUID is unavailable in insecure contexts', () => {
        vi.spyOn(Math, 'random').mockReturnValue(0);
        Object.defineProperty(globalThis, 'crypto', {
            value: {},
            configurable: true,
        });

        expect(createId()).toBe('00000000-0000-4000-8000-000000000000');
    });
});
