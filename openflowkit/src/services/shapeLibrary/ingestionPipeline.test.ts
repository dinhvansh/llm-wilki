import { describe, expect, it } from 'vitest';
import { buildShapePackManifest } from './ingestionPipeline';

describe('shape library ingestion pipeline', () => {
    it('builds deterministic manifests by sorting input assets by path', () => {
        const manifest = buildShapePackManifest({
            packId: 'aws-starter-v1',
            packName: 'AWS Starter',
            version: '1.0.0',
            author: 'OpenFlowKit',
            assets: [
                {
                    path: 'compute/ec2-instance.svg',
                    svgContent: '<svg id="ec2" />',
                    category: 'compute',
                },
                {
                    path: 'storage/s3-bucket.svg',
                    svgContent: '<svg id="s3" />',
                    category: 'storage',
                },
            ],
        });

        expect(manifest.shapes.map((shape) => shape.id)).toEqual(['ec2-instance', 's3-bucket']);
    });

    it('infers labels and defaults when optional metadata is omitted', () => {
        const manifest = buildShapePackManifest({
            packId: 'aws-starter-v1',
            packName: 'AWS Starter',
            version: '1.0.0',
            author: 'OpenFlowKit',
            assets: [
                {
                    path: 'network/vpc-gateway.svg',
                    svgContent: '   <svg id="vpc" />   ',
                    category: 'network',
                },
            ],
        });

        expect(manifest.shapes[0]).toMatchObject({
            id: 'vpc-gateway',
            label: 'Vpc Gateway',
            defaultWidth: 160,
            defaultHeight: 96,
            nodeType: 'custom',
        });
        expect(manifest.shapes[0].svgContent).toBe('<svg id="vpc" />');
    });
});
