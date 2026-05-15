import type { ShapePackManifest } from './types';

export interface ShapePackRegistry {
    getPack(packId: string): ShapePackManifest | undefined;
    listPacks(): ShapePackManifest[];
    registerPack(pack: ShapePackManifest): void;
}

function clonePack(pack: ShapePackManifest): ShapePackManifest {
    return {
        ...pack,
        shapes: pack.shapes.map((shape) => ({ ...shape })),
    };
}

export function createShapePackRegistry(initialPacks: ShapePackManifest[] = []): ShapePackRegistry {
    const packsById = new Map<string, ShapePackManifest>();

    function registerPack(pack: ShapePackManifest): void {
        if (packsById.has(pack.id)) {
            throw new Error(`Shape pack already registered: ${pack.id}`);
        }
        packsById.set(pack.id, clonePack(pack));
    }

    for (const pack of initialPacks) {
        registerPack(pack);
    }

    return {
        getPack(packId: string): ShapePackManifest | undefined {
            const pack = packsById.get(packId);
            return pack ? clonePack(pack) : undefined;
        },
        listPacks(): ShapePackManifest[] {
            return Array.from(packsById.values()).map(clonePack);
        },
        registerPack,
    };
}
