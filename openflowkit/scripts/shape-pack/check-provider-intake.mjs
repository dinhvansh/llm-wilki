import fs from 'node:fs/promises';
import path from 'node:path';

async function pathExists(targetPath) {
  try {
    await fs.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

async function listProviderDirs(rootDir) {
  const entries = await fs.readdir(rootDir, { withFileTypes: true });
  return entries
    .filter((entry) => entry.isDirectory())
    .map((entry) => path.join(rootDir, entry.name))
    .sort((left, right) => left.localeCompare(right));
}

function providerNameFromPath(providerPath) {
  return path.basename(providerPath);
}

async function countFilesRecursively(rootDir, extension) {
  let count = 0;

  async function walk(currentDir) {
    const entries = await fs.readdir(currentDir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(currentDir, entry.name);
      if (entry.isDirectory()) {
        await walk(fullPath);
        continue;
      }
      if (!entry.isFile()) {
        continue;
      }
      if (extension === null || entry.name.endsWith(extension)) {
        count += 1;
      }
    }
  }

  if (!(await pathExists(rootDir))) {
    return 0;
  }

  await walk(rootDir);
  return count;
}

async function main() {
  const rootDir = path.resolve('assets/third-party-icons');
  if (!(await pathExists(rootDir))) {
    console.error(`Missing third-party icons root: ${rootDir}`);
    process.exit(1);
  }

  const providerDirs = await listProviderDirs(rootDir);
  if (providerDirs.length === 0) {
    console.error('No provider directories found under assets/third-party-icons');
    process.exit(1);
  }

  let totalErrors = 0;

  for (const providerDir of providerDirs) {
    const provider = providerNameFromPath(providerDir);
    const sourcePath = path.join(providerDir, 'SOURCE.md');
    const rawDir = path.join(providerDir, 'raw');
    const processedDir = path.join(providerDir, 'processed');

    const hasSource = await pathExists(sourcePath);
    const hasRawDir = await pathExists(rawDir);
    const hasProcessedDir = await pathExists(processedDir);

    if (!hasSource) {
      console.error(`[${provider}] Missing SOURCE.md`);
      totalErrors += 1;
    }
    if (!hasRawDir) {
      console.error(`[${provider}] Missing raw/ directory`);
      totalErrors += 1;
    }
    if (!hasProcessedDir) {
      console.error(`[${provider}] Missing processed/ directory`);
      totalErrors += 1;
    }

    const rawSvgCount = await countFilesRecursively(rawDir, '.svg');
    const processedSvgCount = await countFilesRecursively(processedDir, '.svg');
    const manifestCount = await countFilesRecursively(providerDir, '.manifest.json');

    console.log(
      `[${provider}] source=${hasSource ? 'yes' : 'no'} rawSvg=${rawSvgCount} processedSvg=${processedSvgCount} manifests=${manifestCount}`,
    );
  }

  if (totalErrors > 0) {
    process.exitCode = 1;
    return;
  }

  console.log('Provider intake checklist passed.');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
