function createFallbackUuid(): string {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (token) => {
        const randomNibble = Math.floor(Math.random() * 16);
        const value = token === 'x' ? randomNibble : (randomNibble & 0x3) | 0x8;
        return value.toString(16);
    });
}

export function createId(prefix?: string): string {
    const randomUUID = globalThis.crypto?.randomUUID;
    const id = typeof randomUUID === 'function'
        ? randomUUID.call(globalThis.crypto)
        : createFallbackUuid();
    return prefix ? `${prefix}-${id}` : id;
}
