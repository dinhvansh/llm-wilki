import type { NodeType } from '@/lib/types';

export interface ShapeDefinition {
    id: string;
    label: string;
    category: string;
    svgContent: string;
    defaultWidth: number;
    defaultHeight: number;
    nodeType: NodeType | 'custom' | string;
    defaultData: Record<string, unknown>;
}

export interface ShapePackManifest {
    id: string;
    name: string;
    version: string;
    author: string;
    description?: string;
    shapes: ShapeDefinition[];
}
