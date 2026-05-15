import type { ShapeDefinition, ShapePackManifest } from './types';

function isPositiveFiniteNumber(value: number): boolean {
    return Number.isFinite(value) && value > 0;
}

function validateShapeDefinition(shape: ShapeDefinition, index: number): string[] {
    const errors: string[] = [];
    const prefix = `Shape[${index}]`;

    if (!shape.id.trim()) {
        errors.push(`${prefix} id is required`);
    }
    if (!shape.label.trim()) {
        errors.push(`${prefix} label is required`);
    }
    if (!shape.category.trim()) {
        errors.push(`${prefix} category is required`);
    }
    if (!shape.svgContent.trim()) {
        errors.push(`${prefix} svgContent is required`);
    }
    if (!isPositiveFiniteNumber(shape.defaultWidth)) {
        errors.push(`${prefix} defaultWidth must be > 0`);
    }
    if (!isPositiveFiniteNumber(shape.defaultHeight)) {
        errors.push(`${prefix} defaultHeight must be > 0`);
    }

    return errors;
}

export function validateShapePackManifest(pack: ShapePackManifest): string[] {
    const errors: string[] = [];

    if (!pack.id.trim()) {
        errors.push('Pack id is required');
    }
    if (!pack.name.trim()) {
        errors.push('Pack name is required');
    }
    if (!pack.version.trim()) {
        errors.push('Pack version is required');
    }
    if (!pack.author.trim()) {
        errors.push('Pack author is required');
    }
    if (pack.shapes.length === 0) {
        errors.push('Pack must include at least one shape');
    }

    const seenShapeIds = new Set<string>();
    pack.shapes.forEach((shape, index) => {
        errors.push(...validateShapeDefinition(shape, index));
        if (seenShapeIds.has(shape.id)) {
            errors.push(`Duplicate shape id: ${shape.id}`);
        }
        seenShapeIds.add(shape.id);
    });

    return errors;
}

export function validateShapePackManifests(packs: ShapePackManifest[]): string[] {
    const errors: string[] = [];
    const seenPackIds = new Set<string>();

    packs.forEach((pack, index) => {
        if (seenPackIds.has(pack.id)) {
            errors.push(`Duplicate pack id: ${pack.id}`);
        }
        seenPackIds.add(pack.id);

        const packErrors = validateShapePackManifest(pack);
        packErrors.forEach((error) => {
            errors.push(`Pack[${index}] ${error}`);
        });
    });

    return errors;
}
