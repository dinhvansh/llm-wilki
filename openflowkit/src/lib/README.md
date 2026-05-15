# @vrun-design/openflowkit-core

[![npm version](https://img.shields.io/npm/v/@vrun-design/openflowkit-core?style=flat-square&color=indigo)](https://www.npmjs.com/package/@vrun-design/openflowkit-core)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](https://github.com/Vrun-design/OpenFlowKit/blob/main/LICENSE)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8-blue?style=flat-square)](https://www.typescriptlang.org/)

> Core parsers, types, and brand utilities for **[OpenFlowKit](https://openflowkit.com)** — the open-source, white-label diagramming engine.

This package contains the framework-agnostic logic extracted from OpenFlowKit so you can use it independently in your own apps or build your own canvas on top.

---

## What's included

| Export | Description |
|--------|-------------|
| `parseMermaid(dsl)` | Parse Mermaid.js flowchart / state diagram DSL into React Flow–compatible `nodes` and `edges` |
| `parseOpenFlowDSL(dsl)` | Parse OpenFlow DSL V2 (type-safe, explicit IDs, groups, edge styling) |
| `generatePalette(primaryColor)` | Generate harmonious brand palettes from a single hex color |
| Type exports | `FlowNode`, `FlowEdge`, `NodeData`, `EdgeData`, `DesignSystem`, `NodeType`, and more |

---

## Install

```bash
npm install @vrun-design/openflowkit-core
```

> **Peer dependencies:** `react >=18`, `react-dom >=18`, `reactflow >=11`

---

## Usage

### Mermaid Parser

Converts Mermaid.js syntax into React Flow nodes & edges, ready to pass directly to a `<ReactFlow>` component.

```ts
import { parseMermaid } from '@vrun-design/openflowkit-core';

const dsl = `
flowchart TD
  A[Start] --> B{Is user logged in?}
  B -- Yes --> C[Dashboard]
  B -- No  --> D[Login Page]
`;

const { nodes, edges, direction, error } = parseMermaid(dsl);

// direction: 'TB' | 'LR' | 'RL' | 'BT'
// nodes & edges: React Flow-compatible arrays
```

**Supported Mermaid features:**
- Flowcharts (`flowchart TD / LR / RL / BT`)
- State diagrams (`stateDiagram-v2`)
- All node shapes: rectangle, rounded, diamond, capsule, circle, hexagon, cylinder, parallelogram
- Subgraphs (rendered as group nodes)
- Edge labels, arrow types (`-->`, `==>`, `-.->`, `---`)
- `linkStyle`, `classDef`, `style` directives

---

### OpenFlow DSL V2 Parser

```ts
import { parseOpenFlowDSL } from '@vrun-design/openflowkit-core';

const dsl = `
#id:start shape:capsule color:emerald
  User Request

#id:auth shape:diamond color:amber
  Auth Check

start --> auth | "Is authenticated?" |
`;

const { nodes, edges } = parseOpenFlowDSL(dsl);
```

---

### Brand Palette Generation

```ts
import { generatePalette } from '@vrun-design/openflowkit-core';

const palette = generatePalette('#6366f1'); // your primary brand color
// Returns: { primary, secondary, accent, surface, border, text, ... }
```

---

## TypeScript

Full TypeScript support with declaration files included.

```ts
import type { FlowNode, FlowEdge, NodeData, DesignSystem } from '@vrun-design/openflowkit-core';
```

---

## Part of OpenFlowKit

This package is the extracted core of **[OpenFlowKit](https://github.com/Vrun-design/OpenFlowKit)** — a full-featured, MIT-licensed, white-label diagramming engine built on React Flow.

- 🌐 **Website**: [openflowkit.com](https://openflowkit.com)
- 📦 **Full app**: Self-host or fork the repo
- 🐛 **Issues**: [GitHub Issues](https://github.com/Vrun-design/OpenFlowKit/issues)

---

## License

MIT © [Varun](https://github.com/Vrun-design)
