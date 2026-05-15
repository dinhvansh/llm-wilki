import type { FlowEdge, FlowNode } from '@/lib/types';
import { useFlowStore } from '@/store';
import { createEmptyFlowHistory } from '@/store/historyState';
import { mergeActivePagesIntoDocuments } from '@/store/workspaceDocumentModel';
import type { FlowDocument } from '@/services/storage/flowDocumentModel';

type WikiFlowNode = {
  id: string;
  type?: string;
  label?: string;
  owner?: string;
  position?: { x?: number; y?: number };
  size?: { width?: number; height?: number };
  data?: Record<string, unknown>;
};

type WikiFlowEdge = {
  id: string;
  source: string;
  target: string;
  type?: string;
  label?: string;
  data?: Record<string, unknown>;
};

type WikiFlowDocument = {
  version?: string;
  engine?: string;
  family?: string;
  pages?: Array<{
    id?: string;
    name?: string;
    nodes?: WikiFlowNode[];
    edges?: WikiFlowEdge[];
    groups?: unknown[];
    lanes?: unknown[];
    viewport?: Record<string, unknown>;
  }>;
  metadata?: Record<string, unknown>;
};

type InitMessage = {
  type: 'llmwiki:openflowkit:init';
  diagramId: string;
  title: string;
  objective?: string;
  owner?: string;
  document: WikiFlowDocument;
};

type RequestSaveMessage = {
  type: 'llmwiki:openflowkit:request-save';
  requestId?: string;
};

type BridgeMessage = InitMessage | RequestSaveMessage;

let activeWikiMetadata: Record<string, unknown> = {};
let activeWikiDocumentId = 'llmwiki-flow';

function nowIso(): string {
  return new Date().toISOString();
}

function normalizeNodeType(type: string | undefined): string {
  if (type === 'task' || type === 'handoff') return 'process';
  return type || 'process';
}

function toOpenFlowKitNode(node: WikiFlowNode, index: number): FlowNode {
  const type = normalizeNodeType(node.type);
  const width = Number(node.size?.width ?? 220);
  const height = Number(node.size?.height ?? 72);
  return {
    id: node.id || `node-${index + 1}`,
    type,
    position: {
      x: Number(node.position?.x ?? 120 + index * 260),
      y: Number(node.position?.y ?? 120 + index * 90),
    },
    data: {
      ...(node.data ?? {}),
      label: node.label || type,
      subLabel: node.owner || '',
      width,
      height,
      shape: type === 'decision' ? 'diamond' : type === 'start' || type === 'end' ? 'capsule' : 'rounded',
    },
    width,
    height,
  } as FlowNode;
}

function toOpenFlowKitEdge(edge: WikiFlowEdge, index: number): FlowEdge {
  return {
    id: edge.id || `edge-${index + 1}`,
    source: edge.source,
    target: edge.target,
    type: edge.type || 'smoothstep',
    label: edge.label || undefined,
    data: edge.data ?? {},
  } as FlowEdge;
}

function toOpenFlowKitDocument(message: InitMessage): FlowDocument {
  const sourcePage = message.document.pages?.[0] ?? {};
  const documentId = message.diagramId || 'llmwiki-flow';
  const pageId = sourcePage.id || `${documentId}:page:main`;
  const updatedAt = nowIso();
  return {
    id: documentId,
    name: message.title || String(message.document.metadata?.title ?? 'Wiki flow'),
    createdAt: updatedAt,
    updatedAt,
    activePageId: pageId,
    pages: [
      {
        id: pageId,
        name: sourcePage.name || 'Main',
        diagramType: 'flowchart',
        updatedAt,
        nodes: (sourcePage.nodes ?? []).map(toOpenFlowKitNode),
        edges: (sourcePage.edges ?? []).map(toOpenFlowKitEdge),
        history: createEmptyFlowHistory(),
      },
    ],
  };
}

function fromOpenFlowKitNode(node: FlowNode): WikiFlowNode {
  const data = (node.data ?? {}) as Record<string, unknown>;
  const label = typeof data.label === 'string' ? data.label : node.id;
  const subLabel = typeof data.subLabel === 'string' ? data.subLabel : '';
  const type = node.type === 'process' ? 'task' : String(node.type ?? 'task');
  const width = Number(data.width ?? node.width ?? 220);
  const height = Number(data.height ?? node.height ?? 72);
  return {
    id: node.id,
    type,
    label,
    owner: subLabel,
    position: { x: Math.round(node.position.x), y: Math.round(node.position.y) },
    size: { width, height },
    data,
  };
}

function fromOpenFlowKitEdge(edge: FlowEdge): WikiFlowEdge {
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    type: String(edge.type ?? 'smoothstep'),
    label: typeof edge.label === 'string' ? edge.label : '',
    data: (edge.data ?? {}) as Record<string, unknown>,
  };
}

function getActiveOpenFlowKitDocument(): FlowDocument | null {
  const state = useFlowStore.getState();
  const documents = mergeActivePagesIntoDocuments({
    documents: state.documents,
    activeDocumentId: state.activeDocumentId,
    activePages: state.tabs,
    activePageId: state.activeTabId,
    activeNodes: state.nodes,
    activeEdges: state.edges,
  });
  return documents.find((document) => document.id === state.activeDocumentId) ?? documents[0] ?? null;
}

function toWikiFlowDocument(document: FlowDocument): WikiFlowDocument {
  const page = document.pages.find((item) => item.id === document.activePageId) ?? document.pages[0];
  return {
    version: '1.0',
    engine: 'openflowkit',
    family: 'flowchart',
    pages: [
      {
        id: page?.id ?? `${document.id}:page:main`,
        name: page?.name ?? 'Main',
        nodes: (page?.nodes ?? []).map(fromOpenFlowKitNode),
        edges: (page?.edges ?? []).map(fromOpenFlowKitEdge),
        groups: [],
        viewport: {},
      },
    ],
    metadata: {
      ...activeWikiMetadata,
      title: document.name,
      updatedAt: nowIso(),
    },
  };
}

function postToParent(payload: Record<string, unknown>, targetOrigin: string): void {
  window.parent?.postMessage(payload, targetOrigin || '*');
}

function openDocumentRoute(documentId: string): void {
  const nextPath = `/llmwiki/${encodeURIComponent(documentId)}`;
  const nextHash = `#${nextPath}`;
  if (window.location.hash === nextHash) {
    window.dispatchEvent(new PopStateEvent('popstate'));
    return;
  }

  const previousUrl = window.location.href;
  window.location.hash = nextPath;
  window.dispatchEvent(new HashChangeEvent('hashchange', { oldURL: previousUrl, newURL: window.location.href }));
  window.dispatchEvent(new PopStateEvent('popstate'));
}

function allowedOrigin(origin: string): boolean {
  const configured = import.meta.env.VITE_LLM_WIKI_PARENT_ORIGIN as string | undefined;
  if (!configured) return true;
  return origin === configured;
}

function loadDocument(message: InitMessage, sourceOrigin: string): void {
  const document = toOpenFlowKitDocument(message);
  activeWikiMetadata = {
    ...(message.document.metadata ?? {}),
    objective: message.objective ?? message.document.metadata?.objective ?? '',
    owner: message.owner ?? message.document.metadata?.owner ?? '',
  };
  activeWikiDocumentId = document.id;

  useFlowStore.setState({
    documents: [document],
    activeDocumentId: document.id,
    tabs: document.pages,
    activeTabId: document.activePageId,
    nodes: document.pages[0]?.nodes ?? [],
    edges: document.pages[0]?.edges ?? [],
    selectedNodeId: null,
    selectedEdgeId: null,
  });

  openDocumentRoute(document.id);
  [0, 50, 250, 750].forEach((delayMs) => {
    window.setTimeout(() => openDocumentRoute(document.id), delayMs);
  });

  postToParent(
    {
      type: 'openflowkit:document-loaded',
      diagramId: activeWikiDocumentId,
    },
    sourceOrigin,
  );
}

function sendSave(requestId: string | undefined, sourceOrigin: string): void {
  const document = getActiveOpenFlowKitDocument();
  if (!document) {
    postToParent(
      {
        type: 'openflowkit:save-error',
        requestId,
        diagramId: activeWikiDocumentId,
        message: 'No active OpenFlowKit document is loaded.',
      },
      sourceOrigin,
    );
    return;
  }
  postToParent(
    {
      type: 'openflowkit:document-saved',
      requestId,
      diagramId: activeWikiDocumentId,
      document: toWikiFlowDocument(document),
    },
    sourceOrigin,
  );
}

function isBridgeMessage(value: unknown): value is BridgeMessage {
  if (!value || typeof value !== 'object') return false;
  const type = (value as { type?: unknown }).type;
  return type === 'llmwiki:openflowkit:init' || type === 'llmwiki:openflowkit:request-save';
}

export function installLlmWikiBridge(): void {
  if (typeof window === 'undefined') return;
  window.addEventListener('message', (event: MessageEvent<unknown>) => {
    if (!allowedOrigin(event.origin) || !isBridgeMessage(event.data)) return;
    if (event.data.type === 'llmwiki:openflowkit:init') {
      loadDocument(event.data, event.origin);
      return;
    }
    sendSave(event.data.requestId, event.origin);
  });

  window.setTimeout(() => {
    postToParent({ type: 'openflowkit:ready' }, '*');
  }, 0);
}
