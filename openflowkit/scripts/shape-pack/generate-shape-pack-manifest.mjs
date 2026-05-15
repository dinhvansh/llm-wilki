import fs from 'node:fs/promises';
import path from 'node:path';

function slugify(value) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function inferLabelFromId(id) {
  return id
    .split('-')
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ');
}

async function listSvgFiles(rootDir) {
  const results = [];

  async function walk(currentDir) {
    const entries = await fs.readdir(currentDir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(currentDir, entry.name);
      if (entry.isDirectory()) {
        await walk(fullPath);
        continue;
      }
      if (!entry.isFile() || !entry.name.endsWith('.svg')) {
        continue;
      }
      results.push(fullPath);
    }
  }

  await walk(rootDir);
  return results.sort((left, right) => left.localeCompare(right));
}

function getCategoryFromRelativePath(relativePath) {
  const normalized = relativePath.replaceAll('\\', '/');
  const parts = normalized.split('/');
  return parts.length > 1 ? parts[0] : 'misc';
}

function buildShape(relativePath, svgContent) {
  const normalizedRelativePath = relativePath.replaceAll('\\', '/').replace(/\.svg$/i, '');
  const id = slugify(normalizedRelativePath.replaceAll('/', '-'));

  return {
    id,
    label: inferLabelFromId(id),
    category: getCategoryFromRelativePath(relativePath),
    svgContent: svgContent.trim(),
    defaultWidth: 160,
    defaultHeight: 96,
    nodeType: 'custom',
    defaultData: {},
  };
}

async function main() {
  const args = process.argv.slice(2);
  const sourceDir = args[0];
  const outputPath = args[1];
  const packId = args[2] ?? 'official-pack-v1';
  const packName = args[3] ?? 'Official Pack';
  const packVersion = args[4] ?? '1.0.0';
  const packAuthor = args[5] ?? 'OpenFlowKit';

  if (!sourceDir || !outputPath) {
    console.error(
      'Usage: node scripts/shape-pack/generate-shape-pack-manifest.mjs <processedSvgDir> <outputJsonPath> [packId] [packName] [version] [author]',
    );
    process.exit(1);
  }

  const absoluteSource = path.resolve(sourceDir);
  const absoluteOutput = path.resolve(outputPath);
  const svgFiles = await listSvgFiles(absoluteSource);

  const shapes = [];
  for (const svgFile of svgFiles) {
    const relativePath = path.relative(absoluteSource, svgFile);
    const svgContent = await fs.readFile(svgFile, 'utf8');
    shapes.push(buildShape(relativePath, svgContent));
  }

  const manifest = {
    id: packId,
    name: packName,
    version: packVersion,
    author: packAuthor,
    shapes,
  };

  await fs.mkdir(path.dirname(absoluteOutput), { recursive: true });
  await fs.writeFile(absoluteOutput, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');

  console.log(`Generated manifest: ${absoluteOutput}`);
  console.log(`Shapes: ${shapes.length}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
