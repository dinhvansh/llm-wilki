import { describe, expect, it } from 'vitest';
import { createShapePackRegistry } from './registry';
import type { ShapePackManifest } from './types';

function createPack(id: string, shapeId: string): ShapePackManifest {
    return {
        id,
        name: `Pack ${id}`,
        version: '1.0.0',
        author: 'OpenFlowKit',
        shapes: [
            {
                id: shapeId,
                label: 'Service',
                category: 'infra',
                svgContent: '<svg />',
                defaultWidth: 120,
                defaultHeight: 72,
                nodeType: 'process',
                defaultData: { color: 'blue' },
            },
        ],
    };
}

describe('shape pack registry', () => {
    it('registers and retrieves packs by id', () => {
        const registry = createShapePackRegistry();
        const pack = createPack('aws-core', 'ec2');

        registry.registerPack(pack);

        expect(registry.getPack('aws-core')?.name).toBe('Pack aws-core');
        expect(registry.listPacks()).toHaveLength(1);
    });

    it('rejects duplicate pack ids', () => {
        const registry = createShapePackRegistry([createPack('aws-core', 'ec2')]);

        expect(() => registry.registerPack(createPack('aws-core', 's3'))).toThrow(
            'Shape pack already registered: aws-core',
        );
    });

    it('returns cloned results to prevent external mutation', () => {
        const registry = createShapePackRegistry([createPack('aws-core', 'ec2')]);
        const pack = registry.getPack('aws-core');

        if (!pack) {
            throw new Error('expected pack');
        }

        pack.name = 'Mutated';
        pack.shapes[0].label = 'Mutated shape';

        const freshPack = registry.getPack('aws-core');
        expect(freshPack?.name).toBe('Pack aws-core');
        expect(freshPack?.shapes[0].label).toBe('Service');
    });
});
