import { describe, expect, it } from 'vitest';
import { validateShapePackManifest, validateShapePackManifests } from './manifestValidation';
import { STARTER_SHAPE_PACKS } from './starterPacks';
import type { ShapePackManifest } from './types';

function createValidPack(): ShapePackManifest {
    return {
        id: 'pack-a',
        name: 'Pack A',
        version: '1.0.0',
        author: 'OpenFlowKit',
        shapes: [
            {
                id: 'shape-a',
                label: 'Shape A',
                category: 'test',
                svgContent: '<svg />',
                defaultWidth: 100,
                defaultHeight: 60,
                nodeType: 'process',
                defaultData: {},
            },
        ],
    };
}

describe('shape pack manifest validation', () => {
    it('accepts valid starter manifests', () => {
        expect(validateShapePackManifests(STARTER_SHAPE_PACKS)).toEqual([]);
    });

    it('reports shape-level validation errors', () => {
        const pack = createValidPack();
        pack.shapes[0].id = '';
        pack.shapes[0].defaultWidth = 0;

        expect(validateShapePackManifest(pack)).toEqual(
            expect.arrayContaining(['Shape[0] id is required', 'Shape[0] defaultWidth must be > 0']),
        );
    });

    it('reports duplicate pack ids and duplicate shape ids', () => {
        const packA = createValidPack();
        const packB = createValidPack();
        packB.shapes.push({
            ...packB.shapes[0],
            label: 'Shape A Duplicate',
        });

        const errors = validateShapePackManifests([packA, packB]);

        expect(errors).toEqual(
            expect.arrayContaining(['Duplicate pack id: pack-a', 'Pack[1] Duplicate shape id: shape-a']),
        );
    });
});
