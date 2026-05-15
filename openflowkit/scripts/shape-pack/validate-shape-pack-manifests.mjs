import fs from 'node:fs/promises';
import path from 'node:path';

function validateShape(shape, index) {
  const errors = [];
  const prefix = `shape[${index}]`;

  if (typeof shape.id !== 'string' || !shape.id.trim()) errors.push(`${prefix}.id missing`);
  if (typeof shape.label !== 'string' || !shape.label.trim()) errors.push(`${prefix}.label missing`);
  if (typeof shape.category !== 'string' || !shape.category.trim()) errors.push(`${prefix}.category missing`);
  if (typeof shape.svgContent !== 'string' || !shape.svgContent.trim()) errors.push(`${prefix}.svgContent missing`);
  if (typeof shape.defaultWidth !== 'number' || shape.defaultWidth <= 0) {
    errors.push(`${prefix}.defaultWidth invalid`);
  }
  if (typeof shape.defaultHeight !== 'number' || shape.defaultHeight <= 0) {
    errors.push(`${prefix}.defaultHeight invalid`);
  }

  return errors;
}

function validateManifest(manifest) {
  const errors = [];
  if (typeof manifest.id !== 'string' || !manifest.id.trim()) errors.push('manifest.id missing');
  if (typeof manifest.name !== 'string' || !manifest.name.trim()) errors.push('manifest.name missing');
  if (typeof manifest.version !== 'string' || !manifest.version.trim()) errors.push('manifest.version missing');
  if (typeof manifest.author !== 'string' || !manifest.author.trim()) errors.push('manifest.author missing');

  if (!Array.isArray(manifest.shapes) || manifest.shapes.length === 0) {
    errors.push('manifest.shapes missing/empty');
    return errors;
  }

  const seenIds = new Set();
  manifest.shapes.forEach((shape, index) => {
    errors.push(...validateShape(shape, index));
    if (typeof shape.id === 'string' && shape.id.trim()) {
      if (seenIds.has(shape.id)) {
        errors.push(`duplicate shape id: ${shape.id}`);
      }
      seenIds.add(shape.id);
    }
  });

  return errors;
}

async function findManifestFiles(rootDir) {
  const results = [];

  async function walk(currentDir) {
    const entries = await fs.readdir(currentDir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(currentDir, entry.name);
      if (entry.isDirectory()) {
        await walk(fullPath);
        continue;
      }
      if (entry.isFile() && entry.name.endsWith('.manifest.json')) {
        results.push(fullPath);
      }
    }
  }

  await walk(rootDir);
  return results.sort((left, right) => left.localeCompare(right));
}

async function main() {
  const root = path.resolve('assets/third-party-icons');
  const manifestFiles = await findManifestFiles(root);

  if (manifestFiles.length === 0) {
    console.log('No shape-pack manifest files found under assets/third-party-icons (skipping).');
    return;
  }

  let totalErrors = 0;

  for (const manifestPath of manifestFiles) {
    const raw = await fs.readFile(manifestPath, 'utf8');
    let manifest;

    try {
      manifest = JSON.parse(raw);
    } catch (error) {
      totalErrors += 1;
      console.error(`Invalid JSON: ${manifestPath}`);
      console.error(error instanceof Error ? error.message : String(error));
      continue;
    }

    const errors = validateManifest(manifest);
    if (errors.length > 0) {
      totalErrors += errors.length;
      console.error(`Manifest validation failed: ${manifestPath}`);
      errors.forEach((error) => console.error(`  - ${error}`));
      continue;
    }

    console.log(`Manifest valid: ${manifestPath} (${manifest.shapes.length} shapes)`);
  }

  if (totalErrors > 0) {
    process.exitCode = 1;
    return;
  }

  console.log('All discovered shape-pack manifests are valid.');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
