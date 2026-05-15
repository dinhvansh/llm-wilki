import fs from 'node:fs/promises';
import path from 'node:path';

function slugify(value) {
  return value
    .toLowerCase()
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
  console.error('Usage: node scripts/shape-pack/import-cncf-artwork-icons.mjs <sourceRoot> <outputRoot>');
  process.exit(1);
}

const sourceRoot = path.resolve(sourceRootArg);
const outputRoot = path.resolve(outputRootArg);
const allFiles = await walk(sourceRoot);
const iconFiles = allFiles.filter((filePath) => filePath.replaceAll('\\', '/').includes('/icon/color/') && filePath.toLowerCase().endsWith('.svg'));
const bestIconByProject = new Map();

for (const filePath of iconFiles.sort((left, right) => left.localeCompare(right))) {
  const relativePath = path.relative(sourceRoot, filePath);
  const [projectName] = relativePath.split(path.sep);
  if (!projectName || bestIconByProject.has(projectName)) {
    continue;
  }
  bestIconByProject.set(projectName, filePath);
}

const outputDir = path.join(outputRoot, 'projects');
await ensureDir(outputDir);

for (const [projectName, filePath] of bestIconByProject.entries()) {
  const outputPath = path.join(outputDir, `${slugify(projectName)}.svg`);
  await fs.copyFile(filePath, outputPath);
}

console.log(`Imported ${bestIconByProject.size} CNCF project SVGs into ${outputRoot}`);
