import { parseMermaid } from '@/lib/mermaidParser';
import type { DiagramPlugin } from '@/diagram-types/core';

export const FLOWCHART_PLUGIN: DiagramPlugin = {
  id: 'flowchart',
  displayName: 'Flowchart',
  parseMermaid: (input) => parseMermaid(input),
};

