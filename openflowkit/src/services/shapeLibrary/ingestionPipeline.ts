import type { ShapePackManifest } from './types';

export interface IngestedSvgAsset {
    path: string;
    svgContent: string;
    category: string;
    label?: string;
    nodeType?: string;
    width?: number;
    height?: number;
    defaultData?: Record<string, unknown>;
}

export interface BuildShapePackManifestInput {
    packId: string;
    packName: string;
    version: string;
    author: string;
    description?: string;
    assets: IngestedSvgAsset[];
}

function slugify(value: string): string {
    return value
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '');
}

function inferIdFromPath(path: string): string {
    const normalized = path.replaceAll('\\', '/');
    const fileName = normalized.split('/').pop() ?? normalized;
    const withoutExt = fileName.replace(/\.[^/.]+$/, '');
    return slugify(withoutExt);
}

function inferIdFromFullPath(path: string): string {
    const normalized = path.replaceAll('\\', '/');
    const withoutExt = normalized.replace(/\.[^/.]+$/, '');
    return slugify(withoutExt.replaceAll('/', '-'));
}

function inferLabelFromId(id: string): string {
    return id
        .split('-')
        .filter(Boolean)
        .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
        .join(' ');
}

export function buildShapePackManifest(input: BuildShapePackManifestInput): ShapePackManifest {
    const sortedAssets = [...input.assets].sort((left, right) => left.path.localeCompare(right.path));
    const usedIds = new Set<string>();

    return {
        id: input.packId,
        name: input.packName,
        version: input.version,
        author: input.author,
        description: input.description,
        shapes: sortedAssets.map((asset) => {
            const baseId = inferIdFromPath(asset.path);
            const fallbackId = inferIdFromFullPath(asset.path);
            let id = baseId;
            if (usedIds.has(id)) {
                id = fallbackId;
            }
            if (usedIds.has(id)) {
                let suffix = 2;
                while (usedIds.has(`${id}-${suffix}`)) {
                    suffix += 1;
                }
                id = `${id}-${suffix}`;
            }
            usedIds.add(id);
            return {
                id,
                label: asset.label?.trim() || inferLabelFromId(id),
                category: asset.category.trim(),
                svgContent: asset.svgContent.trim(),
                defaultWidth: asset.width ?? 160,
                defaultHeight: asset.height ?? 96,
                nodeType: asset.nodeType ?? 'custom',
                defaultData: asset.defaultData ?? {},
            };
        }),
    };
}
