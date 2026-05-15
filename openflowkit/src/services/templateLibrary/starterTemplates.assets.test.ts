import { describe, expect, it } from 'vitest';
import { STARTER_TEMPLATE_MANIFESTS } from './starterTemplates';
import { loadProviderCatalog } from '@/services/shapeLibrary/providerCatalog';

describe('starter template provider assets', () => {
    it('uses provider icon ids that exist in the local asset catalogs', async () => {
        const providerCatalogs = await Promise.all([
            loadProviderCatalog('aws'),
            loadProviderCatalog('azure'),
            loadProviderCatalog('cncf'),
        ]);
        const validAssetIds = new Set(
            providerCatalogs.flatMap((items) => items.map((item) => `${item.archIconPackId}:${item.archIconShapeId}`))
        );

        const assetNodes = STARTER_TEMPLATE_MANIFESTS
            .flatMap((template) => template.graph.nodes)
            .filter((node) => node.data.assetPresentation === 'icon');

        expect(assetNodes.length).toBeGreaterThan(0);

        assetNodes.forEach((node) => {
            expect(validAssetIds.has(`${node.data.archIconPackId}:${node.data.archIconShapeId}`)).toBe(true);
        });
    });
});
