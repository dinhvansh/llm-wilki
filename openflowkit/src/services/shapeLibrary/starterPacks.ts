import type { ShapePackManifest } from './types';

const SIMPLE_RECT_SVG = '<svg viewBox="0 0 120 72"><rect x="1" y="1" width="118" height="70" rx="12" fill="#eef2ff" stroke="#6366f1" stroke-width="2"/></svg>';
const SIMPLE_CYLINDER_SVG = '<svg viewBox="0 0 120 72"><ellipse cx="60" cy="14" rx="44" ry="10" fill="#ecfeff" stroke="#0891b2" stroke-width="2"/><path d="M16 14v36c0 6 20 10 44 10s44-4 44-10V14" fill="#ecfeff" stroke="#0891b2" stroke-width="2"/></svg>';
const SIMPLE_DIAMOND_SVG = '<svg viewBox="0 0 120 72"><path d="M60 4l52 32-52 32L8 36z" fill="#fffbeb" stroke="#d97706" stroke-width="2"/></svg>';
const SIMPLE_CLOUD_SVG = '<svg viewBox="0 0 120 72"><path d="M32 52h54c11 0 20-8 20-18 0-10-8-18-18-18-2-8-10-14-20-14-11 0-20 8-22 18-9 1-16 8-16 16 0 9 8 16 18 16z" fill="#eff6ff" stroke="#2563eb" stroke-width="2"/></svg>';

export const STARTER_SHAPE_PACKS: ShapePackManifest[] = [
    {
        id: 'starter-core-v1',
        name: 'Starter Core Shapes',
        version: '1.0.0',
        author: 'OpenFlowKit',
        description: 'Small curated starter pack to bootstrap shape-library ingestion contracts.',
        shapes: [
            {
                id: 'process-card',
                label: 'Process Card',
                category: 'flowchart',
                svgContent: SIMPLE_RECT_SVG,
                defaultWidth: 180,
                defaultHeight: 96,
                nodeType: 'process',
                defaultData: { color: 'blue', shape: 'rounded-rectangle' },
            },
            {
                id: 'decision-diamond',
                label: 'Decision',
                category: 'flowchart',
                svgContent: SIMPLE_DIAMOND_SVG,
                defaultWidth: 180,
                defaultHeight: 128,
                nodeType: 'decision',
                defaultData: { color: 'amber', shape: 'diamond' },
            },
            {
                id: 'data-store',
                label: 'Data Store',
                category: 'architecture',
                svgContent: SIMPLE_CYLINDER_SVG,
                defaultWidth: 180,
                defaultHeight: 96,
                nodeType: 'database',
                defaultData: { color: 'cyan', shape: 'rounded-rectangle' },
            },
            {
                id: 'cloud-gateway',
                label: 'Cloud Gateway',
                category: 'architecture',
                svgContent: SIMPLE_CLOUD_SVG,
                defaultWidth: 180,
                defaultHeight: 96,
                nodeType: 'cloud',
                defaultData: { color: 'blue', shape: 'rounded-rectangle' },
            },
        ],
    },
];
