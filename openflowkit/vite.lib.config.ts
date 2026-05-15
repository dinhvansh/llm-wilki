import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import dts from 'vite-plugin-dts';
import { resolve } from 'path';

export default defineConfig({
    plugins: [
        react(),
        dts({
            // Only process the lib source files
            include: ['src/lib/**/*.ts'],
            // Exclude test files from declaration output
            exclude: ['src/lib/**/*.test.ts', 'src/lib/**/*.spec.ts'],
            // Output declarations alongside the JS bundles
            outDir: 'src/lib/dist',
            // Ensure the entry file for the lib is the root index
            insertTypesEntry: true,
            entryRoot: 'src/lib',
        }),
    ],
    publicDir: false,
    build: {
        lib: {
            entry: resolve(__dirname, 'src/lib/index.ts'),
            name: 'OpenFlowKitCore',
            fileName: (format) => `openflowkit-core.${format}.js`,
            formats: ['es', 'cjs'],
        },
        outDir: 'src/lib/dist',
        // Clean dist before every build so no stale artefacts remain
        emptyOutDir: true,
        rollupOptions: {
            external: ['react', 'react-dom', 'reactflow'],
            output: {
                globals: {
                    react: 'React',
                    'react-dom': 'ReactDOM',
                    reactflow: 'ReactFlow',
                },
            },
        },
    },
});
