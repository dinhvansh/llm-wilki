import fs from 'node:fs/promises';
import path from 'node:path';

function slugify(value) {
  return value
    .toLowerCase()
    .replace(/^azure-public-service-icons$/g, '')
    .replace(/^icons$/g, '')
    .replace(/^\d+-icon-service-/g, '')
    .replace(/-icon-service-/g, '-')
    .replace(/\(classic\)/g, 'classic')
    .replace(/\(deprecated\)/g, 'deprecated')
    .replace(/&/g, ' and ')
    .replace(/\+/g, ' plus ')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .replace(/-+/g, '-');
}

async function ensureDir(dirPath) {
  await fs.mkdir(dirPath, { recursive: true });
}

async function walk(dirPath) {
  const entries = await fs.readdir(dirPath, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    const fullPath = path.join(dirPath, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await walk(fullPath)));
      continue;
    }
    files.push(fullPath);
  }

  return files;
}

const [, , sourceRootArg, outputRootArg] = process.argv;

if (!sourceRootArg || !outputRootArg) {
  console.error('Usage: node scripts/shape-pack/import-azure-official-pack.mjs <sourceRoot> <outputRoot>');
  process.exit(1);
}

const sourceRoot = path.resolve(sourceRootArg);
const outputRoot = path.resolve(outputRootArg);
const svgFiles = (await walk(sourceRoot)).filter((filePath) => filePath.toLowerCase().endsWith('.svg'));
let copiedCount = 0;

for (const filePath of svgFiles) {
  const relativePath = path.relative(sourceRoot, filePath);
  const segments = relativePath.split(path.sep);

  if (segments.length < 2) {
    continue;
  }

  const categorySegment = slugify(segments[0]) || 'misc';
  const sourceStem = path.basename(segments.at(-1), '.svg');
  const fileStem = slugify(sourceStem);
  if (!fileStem) {
    continue;
  }

  const outputDir = path.join(outputRoot, categorySegment);
  const outputPath = path.join(outputDir, `${fileStem}.svg`);
  await ensureDir(outputDir);
  await fs.copyFile(filePath, outputPath);
  copiedCount += 1;
}

console.log(`Imported ${copiedCount} Azure SVGs into ${outputRoot}`);
