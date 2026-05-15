import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

const projectRoot = process.cwd();
const srcRoot = join(projectRoot, 'src');

const fileExtensions = new Set(['.ts', '.tsx', '.js', '.jsx']);

const checks = [
  {
    id: 'legacy-import',
    label: "Imports from 'reactflow'",
    pattern: /from\s+['"]reactflow['"]/g,
  },
  {
    id: 'legacy-parent-node-property',
    label: 'parentNode property usage',
    pattern: /\.parentNode\b|\bparentNode\s*:/g,
  },
  {
    id: 'legacy-edge-update',
    label: 'onEdgeUpdate usage',
    pattern: /\bonEdgeUpdate\b/g,
  },
];

function hasSupportedExtension(filePath) {
  return [...fileExtensions].some((extension) => filePath.endsWith(extension));
}

function collectFiles(directory) {
  const entries = readdirSync(directory);
  const files = [];

  for (const entry of entries) {
    const fullPath = join(directory, entry);
    const stat = statSync(fullPath);
    if (stat.isDirectory()) {
      files.push(...collectFiles(fullPath));
      continue;
    }
    if (hasSupportedExtension(fullPath)) {
      files.push(fullPath);
    }
  }

  return files;
}

function countMatches(content, pattern) {
  const matches = content.match(pattern);
  return matches ? matches.length : 0;
}

const files = collectFiles(srcRoot);
const totals = new Map(checks.map((check) => [check.id, 0]));
const filesByCheck = new Map(checks.map((check) => [check.id, []]));

for (const filePath of files) {
  const content = readFileSync(filePath, 'utf8');
  for (const check of checks) {
    const count = countMatches(content, check.pattern);
    if (count === 0) {
      continue;
    }
    totals.set(check.id, (totals.get(check.id) ?? 0) + count);
    filesByCheck.get(check.id)?.push({
      file: relative(projectRoot, filePath),
      count,
    });
  }
}

console.log('React Flow v12 Migration Audit');
console.log('=============================\n');

for (const check of checks) {
  const total = totals.get(check.id) ?? 0;
  console.log(`${check.label}: ${total}`);
  const fileEntries = filesByCheck.get(check.id) ?? [];
  for (const entry of fileEntries) {
    console.log(`  - ${entry.file} (${entry.count})`);
  }
  console.log('');
}
