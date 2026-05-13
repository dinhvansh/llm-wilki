'use client'

import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  applyEdgeChanges,
  applyNodeChanges,
  type Connection,
  type Edge,
  type Node,
  type OnConnect,
  type OnEdgesChange,
  type OnNodesChange,
} from '@xyflow/react'
import { useCallback, useMemo } from 'react'

import type { FlowDocument, FlowEdge, FlowNode } from '@/lib/types'
import { firstFlowPage, updateFirstFlowPage } from '@/lib/openflow'

const NODE_COLORS: Record<string, string> = {
  start: '#dcfce7',
  end: '#fee2e2',
  decision: '#fef3c7',
  handoff: '#dbeafe',
  task: '#f8fafc',
}

function toReactNode(node: FlowNode): Node {
  const nodeType = node.type || 'task'
  return {
    id: node.id,
    position: node.position ?? { x: 0, y: 0 },
    data: {
      label: (
        <div className="space-y-1">
          <div className="text-[10px] font-semibold uppercase text-muted-foreground">{nodeType}</div>
          <div className="text-sm font-semibold text-foreground">{node.label}</div>
          {node.owner ? <div className="text-[11px] text-muted-foreground">{node.owner}</div> : null}
        </div>
      ),
    },
    style: {
      width: node.size?.width ?? 220,
      minHeight: node.size?.height ?? 72,
      borderRadius: nodeType === 'decision' ? 18 : 10,
      border: '1px solid hsl(34 24% 78%)',
      background: NODE_COLORS[nodeType] ?? NODE_COLORS.task,
      boxShadow: '0 8px 24px rgba(25, 20, 15, 0.08)',
    },
  }
}

function toReactEdge(edge: FlowEdge): Edge {
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.label || undefined,
    type: edge.type || 'smoothstep',
    animated: false,
    style: { stroke: 'hsl(212 18% 38%)', strokeWidth: 1.8 },
    labelStyle: { fill: 'hsl(212 30% 22%)', fontSize: 12, fontWeight: 600 },
    labelBgStyle: { fill: 'hsl(42 38% 96%)' },
  }
}

function fromReactNodes(nodes: Node[], current: FlowNode[]): FlowNode[] {
  const byId = new Map(current.map(node => [node.id, node]))
  return nodes.map(node => {
    const existing = byId.get(node.id)
    return {
      ...(existing ?? { id: node.id, type: 'task', label: String(node.data?.label ?? 'Node') }),
      position: { x: Math.round(node.position.x), y: Math.round(node.position.y) },
    }
  })
}

function fromReactEdges(edges: Edge[], current: FlowEdge[]): FlowEdge[] {
  const byId = new Map(current.map(edge => [edge.id, edge]))
  return edges.map(edge => ({
    ...(byId.get(edge.id) ?? { id: edge.id, source: edge.source, target: edge.target, type: edge.type ?? 'smoothstep' }),
    source: edge.source,
    target: edge.target,
    type: edge.type ?? 'smoothstep',
  }))
}

export function OpenFlowCanvas({
  document,
  onChange,
  onSelectNode,
}: {
  document: FlowDocument
  onChange: (next: FlowDocument) => void
  onSelectNode?: (nodeId: string | null) => void
}) {
  const page = firstFlowPage(document)
  const nodes = useMemo(() => page.nodes.map(toReactNode), [page.nodes])
  const edges = useMemo(() => page.edges.map(toReactEdge), [page.edges])

  const commitNodes = useCallback(
    (nextNodes: Node[]) => {
      onChange(updateFirstFlowPage(document, { nodes: fromReactNodes(nextNodes, page.nodes) }))
    },
    [document, onChange, page.nodes],
  )

  const commitEdges = useCallback(
    (nextEdges: Edge[]) => {
      onChange(updateFirstFlowPage(document, { edges: fromReactEdges(nextEdges, page.edges) }))
    },
    [document, onChange, page.edges],
  )

  const onNodesChange = useCallback<OnNodesChange>(
    changes => commitNodes(applyNodeChanges(changes, nodes)),
    [commitNodes, nodes],
  )

  const onEdgesChange = useCallback<OnEdgesChange>(
    changes => commitEdges(applyEdgeChanges(changes, edges)),
    [commitEdges, edges],
  )

  const onConnect = useCallback<OnConnect>(
    (connection: Connection) => {
      if (!connection.source || !connection.target) return
      commitEdges([
        ...edges,
        {
          id: `edge-${Date.now()}`,
          source: connection.source,
          target: connection.target,
          sourceHandle: connection.sourceHandle,
          targetHandle: connection.targetHandle,
          type: 'smoothstep',
        },
      ])
    },
    [commitEdges, edges],
  )

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      onNodeClick={(_, node) => onSelectNode?.(node.id)}
      onPaneClick={() => onSelectNode?.(null)}
      fitView
      minZoom={0.2}
      maxZoom={2}
      className="bg-[linear-gradient(180deg,hsl(42_38%_97%),hsl(42_28%_94%))]"
    >
      <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="hsl(34 20% 78%)" />
      <MiniMap pannable zoomable nodeStrokeWidth={3} />
      <Controls />
    </ReactFlow>
  )
}
