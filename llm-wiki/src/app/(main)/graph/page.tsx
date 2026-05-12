'use client'
import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import type { Edge, Node, NodeProps, NodeTypes } from '@xyflow/react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  useEdgesState,
  useNodesState,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { AlertTriangle, Circle, Clock, Filter, Network, Radar, RotateCcw, Star } from 'lucide-react'

import { EmptyState } from '@/components/data-display/empty-state'
import { ErrorState } from '@/components/data-display/error-state'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { StatusBadge } from '@/components/data-display/status-badge'
import { EvidenceCard } from '@/components/evidence/evidence-card'
import { PageHeader } from '@/components/layout/page-header'
import { useGraph } from '@/hooks/use-graph'
import { useCollections } from '@/hooks/use-collections'
import { cn } from '@/lib/utils'

type GraphNodeData = {
  label: string
  status?: string
  pageType?: string
  entityType?: string
  flags?: { orphan?: boolean; stale?: boolean; conflict?: boolean; hub?: boolean; recent?: boolean }
  degree?: number
  hubScore?: number
  isOrphan?: boolean
  isDimmed?: boolean
  isFocused?: boolean
  labelVisible?: boolean
}

function PageNode({ data }: NodeProps<Node<GraphNodeData>>) {
  const statusColors: Record<string, { fill: string; ring: string; halo: string }> = {
    published: { fill: 'bg-sky-500', ring: 'border-sky-200', halo: 'bg-sky-400/12' },
    draft: { fill: 'bg-amber-500', ring: 'border-amber-200', halo: 'bg-amber-400/12' },
    in_review: { fill: 'bg-violet-500', ring: 'border-violet-200', halo: 'bg-violet-400/12' },
    stale: { fill: 'bg-rose-500', ring: 'border-rose-200', halo: 'bg-rose-400/12' },
    archived: { fill: 'bg-slate-400', ring: 'border-slate-200', halo: 'bg-slate-400/10' },
  }
  const colors = statusColors[data.status ?? 'published'] ?? statusColors.published
  const nodeSize = data.flags?.hub ? 19 : data.flags?.conflict ? 16 : data.isOrphan ? 8 : data.flags?.recent ? 14 : 12
  const haloSize = nodeSize + (data.isFocused ? 28 : data.flags?.hub ? 20 : data.isOrphan ? 4 : 10)
  return (
    <div
      className={cn(
        'group relative flex min-h-10 min-w-10 items-center justify-center transition-all duration-200',
        data.isOrphan && !data.isFocused && 'opacity-50',
        data.isDimmed && 'grayscale'
      )}
    >
      <Handle type="target" position={Position.Top} className="!h-1 !w-1 !border-0 !bg-transparent" />
      <div
        className={cn('absolute rounded-full blur-sm transition-all duration-200', colors.halo, data.isFocused && 'opacity-100', !data.isFocused && 'opacity-70')}
        style={{ width: haloSize, height: haloSize }}
      />
      <div
        className={cn(
          'relative rounded-full border-[3px] shadow-[0_0_20px_rgba(15,23,42,0.15)] transition-all duration-200',
          colors.fill,
          colors.ring,
          data.isOrphan && 'border-2 shadow-[0_0_10px_rgba(15,23,42,0.08)]',
          data.flags?.conflict && 'outline outline-2 outline-orange-300/80',
          data.flags?.stale && 'outline outline-2 outline-rose-300/80',
          data.isFocused && 'scale-125 shadow-[0_0_34px_rgba(14,165,233,0.45)]'
        )}
        style={{ width: nodeSize, height: nodeSize }}
        title={`${data.label}${data.pageType ? ` · ${data.pageType}` : ''}`}
      />
      {data.flags?.hub && (
        <div className="absolute h-9 w-9 rounded-full border border-yellow-300/70 shadow-[0_0_22px_rgba(250,204,21,0.22)]" />
      )}
      {data.labelVisible && (
        <div className="pointer-events-none absolute left-1/2 top-8 max-w-40 -translate-x-1/2 whitespace-nowrap rounded-full border border-white/60 bg-white/72 px-2 py-0.5 text-[10px] font-medium text-slate-700 shadow-sm backdrop-blur-md">
          {data.label}
        </div>
      )}
      <div className="pointer-events-none absolute -bottom-1 flex translate-y-full gap-1 opacity-0 transition-opacity group-hover:opacity-100">
        {data.flags?.stale && <span className="h-1.5 w-1.5 rounded-full bg-rose-500" title="Stale" />}
        {data.flags?.conflict && <span className="h-1.5 w-1.5 rounded-full bg-orange-500" title="Conflict" />}
        {data.flags?.orphan && <span className="h-1.5 w-1.5 rounded-full bg-slate-400" title="Orphan" />}
      </div>
      <Handle type="source" position={Position.Bottom} className="!h-1 !w-1 !border-0 !bg-transparent" />
    </div>
  )
}

function EntityNode({ data }: NodeProps<Node<GraphNodeData>>) {
  const nodeSize = data.flags?.hub ? 16 : data.isOrphan ? 7 : 10
  const haloSize = nodeSize + (data.isFocused ? 24 : data.isOrphan ? 4 : 10)
  return (
    <div
      className={cn(
        'relative flex min-h-10 min-w-10 items-center justify-center transition-all duration-200',
        data.isOrphan && !data.isFocused && 'opacity-45',
        data.isDimmed && 'grayscale'
      )}
    >
      <Handle type="target" position={Position.Top} className="!h-1 !w-1 !border-0 !bg-transparent" />
      <div
        className="absolute rounded-full bg-emerald-400/12 blur-sm transition-all duration-200"
        style={{ width: haloSize, height: haloSize }}
      />
      <div
        className={cn(
          'relative rounded-full border-2 border-emerald-100 bg-emerald-500 shadow-[0_0_18px_rgba(16,185,129,0.2)] transition-all duration-200',
          data.isOrphan && 'shadow-[0_0_8px_rgba(16,185,129,0.12)]',
          data.isFocused && 'scale-125 shadow-[0_0_30px_rgba(16,185,129,0.48)]'
        )}
        style={{ width: nodeSize, height: nodeSize }}
        title={`${data.label}${data.entityType ? ` · ${data.entityType}` : ''}`}
      />
      {data.labelVisible && (
        <div className="pointer-events-none absolute left-1/2 top-8 max-w-40 -translate-x-1/2 whitespace-nowrap rounded-full border border-white/60 bg-white/72 px-2 py-0.5 text-[10px] font-medium text-slate-700 shadow-sm backdrop-blur-md">
          {data.label}
        </div>
      )}
      <div className="pointer-events-none absolute -bottom-1 h-1.5 w-1.5 translate-y-full rounded-full bg-emerald-300 opacity-70">
      </div>
      <Handle type="source" position={Position.Bottom} className="!h-1 !w-1 !border-0 !bg-transparent" />
    </div>
  )
}

const nodeTypes: NodeTypes = {
  page: PageNode,
  entity: EntityNode,
}

const EDGE_COLORS: Record<string, string> = {
  parent_child: '#6366f1',
  derived_from: '#22c55e',
  related_to: '#94a3b8',
  mentions: '#f59e0b',
  depends_on: '#ef4444',
  supersedes: '#8b5cf6',
  merged_into: '#0f766e',
}

type GraphNodeInput = {
  id: string
  type: 'page' | 'entity'
  label: string
  status?: string
  pageType?: string
  entityType?: string
  flags?: { orphan: boolean; stale: boolean; conflict: boolean; hub: boolean; recent: boolean }
  metrics?: { degree?: number; hubScore?: number }
}

type GraphEdgeInput = {
  id: string
  source: string
  target: string
  relationType: string
  label?: string
}

function hashNumber(value: string): number {
  let hash = 0
  for (let index = 0; index < value.length; index += 1) {
    hash = ((hash << 5) - hash + value.charCodeAt(index)) | 0
  }
  return Math.abs(hash)
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

function buildConnectedComponents(nodes: GraphNodeInput[], edges: GraphEdgeInput[]) {
  const adjacency = new Map<string, Set<string>>()
  nodes.forEach(node => adjacency.set(node.id, new Set()))
  edges.forEach(edge => {
    adjacency.get(edge.source)?.add(edge.target)
    adjacency.get(edge.target)?.add(edge.source)
  })

  const visited = new Set<string>()
  const components: string[][] = []
  nodes.forEach(node => {
    if (visited.has(node.id)) return
    const stack = [node.id]
    const component: string[] = []
    visited.add(node.id)
    while (stack.length) {
      const current = stack.pop()
      if (!current) continue
      component.push(current)
      adjacency.get(current)?.forEach(neighbor => {
        if (visited.has(neighbor)) return
        visited.add(neighbor)
        stack.push(neighbor)
      })
    }
    components.push(component)
  })
  return components.sort((left, right) => right.length - left.length)
}

function buildFlowNodes(nodes: GraphNodeInput[], edges: GraphEdgeInput[]): Node<GraphNodeData>[] {
  if (nodes.length === 0) return []

  const components = buildConnectedComponents(nodes, edges)
  const componentByNodeId = new Map<string, number>()
  components.forEach((component, index) => {
    component.forEach(nodeId => componentByNodeId.set(nodeId, index))
  })

  const width = Math.max(980, Math.ceil(Math.sqrt(nodes.length) * 290))
  const height = Math.max(760, Math.ceil(Math.sqrt(nodes.length) * 220))
  const globalCenter = { x: width / 2, y: height / 2 }
  const componentCenters = new Map<number, { x: number; y: number }>()
  const orbitRadius = Math.min(width, height) * 0.32
  const singleNodeComponents = components.filter(component => component.length === 1)
  const multiNodeComponents = components.filter(component => component.length > 1)

  components.forEach((component, index) => {
    if (components.length === 1) {
      componentCenters.set(index, globalCenter)
      return
    }
    if (component.length === 1 && singleNodeComponents.length > 8) {
      const orphanIndex = singleNodeComponents.findIndex(single => single[0] === component[0])
      const seed = hashNumber(component[0])
      const goldenAngle = Math.PI * (3 - Math.sqrt(5))
      const angle = orphanIndex * goldenAngle + (seed % 23) * 0.01
      const cloudRadius = 190 + Math.sqrt(orphanIndex + 1) * 44 + (seed % 31)
      componentCenters.set(index, {
        x: globalCenter.x + Math.cos(angle) * cloudRadius,
        y: globalCenter.y + Math.sin(angle) * cloudRadius * 0.62,
      })
      return
    }
    const angle = (index / components.length) * Math.PI * 2
    const distance = components.length <= 4 ? orbitRadius * 0.78 : orbitRadius * (component.length > 1 ? 0.72 : 1)
    componentCenters.set(index, {
      x: globalCenter.x + Math.cos(angle) * distance,
      y: globalCenter.y + Math.sin(angle) * distance * 0.72,
    })
  })

  const positions = new Map<string, { x: number; y: number; vx: number; vy: number }>()
  const nodeById = new Map(nodes.map(node => [node.id, node]))

  nodes.forEach((node, index) => {
    const componentIndex = componentByNodeId.get(node.id) ?? 0
    const center = componentCenters.get(componentIndex) ?? globalCenter
    const isOrphan = (components[componentIndex]?.length ?? 1) === 1
    const seed = hashNumber(node.id)
    const angle = ((seed % 360) / 360) * Math.PI * 2
    const radius = isOrphan ? seed % 28 : 30 + (seed % 90) + (node.metrics?.degree ?? 0) * 4 + (components[componentIndex]?.length ?? 1) * 2
    positions.set(node.id, {
      x: center.x + Math.cos(angle) * radius + ((index % 3) - 1) * 12,
      y: center.y + Math.sin(angle) * radius + ((index % 5) - 2) * 10,
      vx: 0,
      vy: 0,
    })
  })

  const iterations = nodes.length > 28 ? 220 : 160
  const damping = 0.84

  for (let iteration = 0; iteration < iterations; iteration += 1) {
    for (let i = 0; i < nodes.length; i += 1) {
      const left = nodes[i]
      const leftPosition = positions.get(left.id)
      if (!leftPosition) continue
      for (let j = i + 1; j < nodes.length; j += 1) {
        const right = nodes[j]
        const rightPosition = positions.get(right.id)
        if (!rightPosition) continue
        let dx = rightPosition.x - leftPosition.x
        let dy = rightPosition.y - leftPosition.y
        const distanceSq = Math.max(dx * dx + dy * dy, 24)
        const distance = Math.sqrt(distanceSq)
        dx /= distance
        dy /= distance
        const leftComponent = components[componentByNodeId.get(left.id) ?? 0]
        const rightComponent = components[componentByNodeId.get(right.id) ?? 0]
        const sameComponent = componentByNodeId.get(left.id) === componentByNodeId.get(right.id)
        const bothOrphans = leftComponent?.length === 1 && rightComponent?.length === 1
        const charge = sameComponent ? 6800 : bothOrphans ? 1200 : 2800
        const force = charge / distanceSq
        leftPosition.vx -= dx * force
        leftPosition.vy -= dy * force
        rightPosition.vx += dx * force
        rightPosition.vy += dy * force
      }
    }

    edges.forEach(edge => {
      const sourcePosition = positions.get(edge.source)
      const targetPosition = positions.get(edge.target)
      if (!sourcePosition || !targetPosition) return
      let dx = targetPosition.x - sourcePosition.x
      let dy = targetPosition.y - sourcePosition.y
      const distance = Math.max(Math.sqrt(dx * dx + dy * dy), 1)
      dx /= distance
      dy /= distance
      const sourceNode = nodeById.get(edge.source)
      const targetNode = nodeById.get(edge.target)
      const desiredDistance =
        edge.relationType === 'mentions' ? 86 :
        sourceNode?.type !== targetNode?.type ? 102 :
        edge.relationType === 'parent_child' ? 122 :
        138
      const springStrength =
        edge.relationType === 'parent_child' ? 0.028 :
        edge.relationType === 'derived_from' ? 0.022 :
        0.017
      const force = (distance - desiredDistance) * springStrength
      sourcePosition.vx += dx * force
      sourcePosition.vy += dy * force
      targetPosition.vx -= dx * force
      targetPosition.vy -= dy * force
    })

    nodes.forEach(node => {
      const position = positions.get(node.id)
      if (!position) return
      const componentIndex = componentByNodeId.get(node.id) ?? 0
      const componentCenter = componentCenters.get(componentIndex) ?? globalCenter
      const isOrphan = (components[componentIndex]?.length ?? 1) === 1
      const hubBias = node.flags?.hub ? 0.022 : 0.012
      position.vx += (componentCenter.x - position.x) * (isOrphan ? 0.03 : hubBias)
      position.vy += (componentCenter.y - position.y) * (isOrphan ? 0.03 : hubBias)
      position.vx += (globalCenter.x - position.x) * (isOrphan ? 0.0007 : 0.0014)
      position.vy += (globalCenter.y - position.y) * (isOrphan ? 0.0005 : 0.0011)
      position.vx *= damping
      position.vy *= damping
      position.x += position.vx
      position.y += position.vy
    })
  }

  return nodes.map(node => {
    const position = positions.get(node.id)
    const degree = node.metrics?.degree ?? 0
    const hubScore = node.metrics?.hubScore ?? 0
    const componentIndex = componentByNodeId.get(node.id) ?? 0
    const isOrphan = (components[componentIndex]?.length ?? 1) === 1
    const componentCenter = componentCenters.get(componentIndex) ?? globalCenter
    const x = clamp(position?.x ?? componentCenter.x, 40, width - 40)
    const y = clamp(position?.y ?? componentCenter.y, 40, height - 40)
    return {
    id: node.id,
    type: node.type,
    position: { x, y },
    data: {
      label: node.label,
      status: node.status,
      pageType: node.pageType,
      entityType: node.entityType,
      flags: node.flags,
      degree,
      hubScore,
      isOrphan,
      labelVisible: true,
    },
  }})
}

function buildFlowEdges(edges: Array<{ id: string; source: string; target: string; relationType: string; label?: string }>): Edge[] {
  return edges.map(edge => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.label || edge.relationType,
    type: 'default',
    style: { stroke: EDGE_COLORS[edge.relationType] ?? '#94a3b8', strokeWidth: edge.relationType === 'parent_child' ? 1.8 : 1.15 },
  }))
}

export default function KnowledgeGraphPage() {
  const [nodeType, setNodeType] = useState<'all' | 'page' | 'entity'>('all')
  const [status, setStatus] = useState<'all' | 'draft' | 'in_review' | 'published' | 'stale' | 'archived'>('all')
  const [localMode, setLocalMode] = useState(false)
  const [collectionId, setCollectionId] = useState('')
  const [selectedRelationTypes, setSelectedRelationTypes] = useState<string[]>([])
  const [selectedEntityTypes, setSelectedEntityTypes] = useState<string[]>([])
  const [selectedPageTypes, setSelectedPageTypes] = useState<string[]>([])
  const [showOrphans, setShowOrphans] = useState(false)
  const [showStale, setShowStale] = useState(false)
  const [showConflicts, setShowConflicts] = useState(false)
  const [showHubs, setShowHubs] = useState(false)
  const [focusId, setFocusId] = useState<string | undefined>(undefined)
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null)
  const [zoom, setZoom] = useState(1)
  const [labelMode, setLabelMode] = useState<'smart' | 'always' | 'hidden'>('smart')
  const { data: collections } = useCollections()

  useEffect(() => {
    setCollectionId(new URLSearchParams(window.location.search).get('collectionId') ?? '')
  }, [])

  const { data, isLoading, isError, error, refetch } = useGraph({
    nodeType,
    status: status === 'all' ? undefined : status,
    relationTypes: selectedRelationTypes,
    entityTypes: selectedEntityTypes,
    pageTypes: selectedPageTypes,
    collectionId: collectionId || undefined,
    focusId,
    localMode,
    showOrphans,
    showStale,
    showConflicts,
    showHubs,
  })

  const flowNodes = useMemo(() => buildFlowNodes(data?.nodes ?? [], data?.edges ?? []), [data?.edges, data?.nodes])
  const flowEdges = useMemo(() => buildFlowEdges(data?.edges ?? []), [data?.edges])
  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)

  useEffect(() => {
    setNodes(flowNodes)
    setEdges(flowEdges)
    setHoveredNodeId(null)
  }, [flowNodes, flowEdges, setNodes, setEdges])

  const detail = selectedNodeId ? data?.detailById?.[selectedNodeId] : undefined
  const interactionNodeId = hoveredNodeId ?? selectedNodeId
  const neighborIds = useMemo(() => {
    if (!interactionNodeId) return new Set<string>()
    const next = new Set<string>([interactionNodeId])
    flowEdges.forEach(edge => {
      if (edge.source === interactionNodeId) next.add(edge.target)
      if (edge.target === interactionNodeId) next.add(edge.source)
    })
    return next
  }, [flowEdges, interactionNodeId])
  const connectedEdgeIds = useMemo(() => {
    if (!interactionNodeId) return new Set<string>()
    return new Set(flowEdges.filter(edge => edge.source === interactionNodeId || edge.target === interactionNodeId).map(edge => edge.id))
  }, [flowEdges, interactionNodeId])
  const displayNodes = useMemo(() => {
    const smartLabelsVisible = zoom >= 1.08
    return nodes.map(node => {
      const isFocused = Boolean(interactionNodeId && neighborIds.has(node.id))
      const isDimmed = Boolean(interactionNodeId && !neighborIds.has(node.id))
      const isImportant = Boolean(node.data.flags?.hub || node.data.flags?.conflict || (node.data.degree ?? 0) >= 2)
      const labelVisible = labelMode === 'always' || (labelMode === 'smart' && (isFocused || (smartLabelsVisible && isImportant && !node.data.isOrphan)))
      return {
        ...node,
        data: {
          ...node.data,
          isFocused,
          isDimmed,
          labelVisible: labelMode !== 'hidden' && labelVisible,
        },
        style: {
          ...node.style,
          opacity: isDimmed ? 0.12 : node.data.isOrphan && !isFocused ? 0.58 : 1,
          zIndex: isFocused ? 10 : 1,
        },
      }
    })
  }, [interactionNodeId, labelMode, neighborIds, nodes, zoom])
  const displayEdges = useMemo(() => {
    return edges.map(edge => {
      const isConnected = Boolean(interactionNodeId && connectedEdgeIds.has(edge.id))
      const isDimmed = Boolean(interactionNodeId && !isConnected)
      const labelVisible = labelMode === 'always' || (labelMode === 'smart' && isConnected && zoom >= 1)
      return {
        ...edge,
        animated: isConnected,
        label: labelVisible ? edge.label : undefined,
        style: {
          ...edge.style,
          opacity: isDimmed ? 0.05 : isConnected ? 0.9 : 0.22,
          strokeWidth: isConnected ? 2.35 : edge.style?.strokeWidth,
        },
      }
    })
  }, [connectedEdgeIds, edges, interactionNodeId, labelMode, zoom])

  const toggleValue = (value: string, selected: string[], setSelected: (next: string[]) => void) => {
    setSelected(selected.includes(value) ? selected.filter(item => item !== value) : [...selected, value])
  }

  if (isLoading) return <LoadingSpinner label="Building knowledge graph..." />

  if (isError) {
    return (
      <div>
        <PageHeader title="Knowledge Graph" />
        <ErrorState message={(error as Error)?.message ?? 'Failed to load graph'} onRetry={() => refetch()} />
      </div>
    )
  }

  if (!data || data.nodes.length === 0) {
    return (
      <div>
        <PageHeader title="Knowledge Graph" />
        <EmptyState icon="database" title="No graph data yet" description="Add pages and sources to build the knowledge graph." />
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      <PageHeader
        title="Knowledge Graph"
        description={`${data.meta?.nodeCount ?? data.nodes.length} nodes · ${data.meta?.edgeCount ?? data.edges.length} edges`}
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setNodeType('all')
                setStatus('all')
                setLocalMode(false)
                setCollectionId('')
                setSelectedRelationTypes([])
                setSelectedEntityTypes([])
                setSelectedPageTypes([])
                setShowOrphans(false)
                setShowStale(false)
                setShowConflicts(false)
                setShowHubs(false)
                setFocusId(undefined)
                setHoveredNodeId(null)
                setLabelMode('smart')
              }}
              className="inline-flex items-center gap-1 rounded-md border border-input px-3 py-1.5 text-sm hover:bg-accent"
            >
              <RotateCcw className="h-4 w-4" />
              Reset
            </button>
          </div>
        }
      />

      <div className="border-b border-border bg-card/50 px-6 py-4">
        <div className="grid gap-4 lg:grid-cols-5">
          <div className="space-y-2">
            <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <Filter className="h-3.5 w-3.5" />
              Node Scope
            </p>
            <div className="flex flex-wrap gap-2">
              {(['all', 'page', 'entity'] as const).map(value => (
                <button key={value} onClick={() => setNodeType(value)} className={cn('rounded-md border px-2 py-1 text-xs', nodeType === value ? 'border-primary bg-primary text-primary-foreground' : 'border-input hover:bg-accent')}>
                  {value}
                </button>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              {(['all', 'draft', 'in_review', 'published', 'stale', 'archived'] as const).map(value => (
                <button key={value} onClick={() => setStatus(value)} className={cn('rounded-md border px-2 py-1 text-xs', status === value ? 'border-primary bg-primary text-primary-foreground' : 'border-input hover:bg-accent')}>
                  {value}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Collection</p>
            <select
              value={collectionId}
              onChange={event => setCollectionId(event.target.value)}
              className="h-9 w-full rounded-md border border-input bg-background px-2 text-sm"
            >
              <option value="">All Collections</option>
              <option value="standalone">Standalone</option>
              {collections?.map(collection => (
                <option key={collection.id} value={collection.id}>{collection.name}</option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <AlertTriangle className="h-3.5 w-3.5" />
              Analytics
            </p>
            <div className="flex flex-wrap gap-2">
              {[
                ['orphans', showOrphans, setShowOrphans],
                ['stale', showStale, setShowStale],
                ['conflicts', showConflicts, setShowConflicts],
                ['hubs', showHubs, setShowHubs],
              ].map(([label, checked, setter]) => (
                <button
                  key={label as string}
                  onClick={() => (setter as (value: boolean) => void)(!(checked as boolean))}
                  className={cn('rounded-md border px-2 py-1 text-xs', checked ? 'border-primary bg-primary text-primary-foreground' : 'border-input hover:bg-accent')}
                >
                  {label as string}
                </button>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">{data.meta?.clusters?.disconnectedCount ?? 0} disconnected nodes</p>
          </div>

          <div className="space-y-2">
            <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <Network className="h-3.5 w-3.5" />
              Relation Filters
            </p>
            <div className="flex flex-wrap gap-2">
              {(data.meta?.availableRelationTypes ?? []).map(value => (
                <button key={value} onClick={() => toggleValue(value, selectedRelationTypes, setSelectedRelationTypes)} className={cn('rounded-md border px-2 py-1 text-xs', selectedRelationTypes.includes(value) ? 'border-primary bg-primary text-primary-foreground' : 'border-input hover:bg-accent')}>
                  {value}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <Circle className="h-3.5 w-3.5" />
              Semantic Filters
            </p>
            <div className="flex flex-wrap gap-2">
              {(data.meta?.availableEntityTypes ?? []).map(value => (
                <button key={value} onClick={() => toggleValue(value, selectedEntityTypes, setSelectedEntityTypes)} className={cn('rounded-md border px-2 py-1 text-xs', selectedEntityTypes.includes(value) ? 'border-primary bg-primary text-primary-foreground' : 'border-input hover:bg-accent')}>
                  {value}
                </button>
              ))}
              {(data.meta?.availablePageTypes ?? []).map(value => (
                <button key={value} onClick={() => toggleValue(value, selectedPageTypes, setSelectedPageTypes)} className={cn('rounded-md border px-2 py-1 text-xs', selectedPageTypes.includes(value) ? 'border-primary bg-primary text-primary-foreground' : 'border-input hover:bg-accent')}>
                  {value}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <Radar className="h-3.5 w-3.5" />
              Interaction
            </p>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={localMode} onChange={event => setLocalMode(event.target.checked)} />
              Focus on selected node neighborhood
            </label>
            <select
              value={labelMode}
              onChange={event => setLabelMode(event.target.value as typeof labelMode)}
              className="h-8 w-full rounded-md border border-input bg-background px-2 text-xs"
            >
              <option value="smart">Smart labels</option>
              <option value="always">Always show labels</option>
              <option value="hidden">Hide labels</option>
            </select>
            <p className="text-xs text-muted-foreground">Smart labels stay quiet until hover, selection, hubs, or closer zoom.</p>
          </div>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        <div className="relative flex-1">
          <ReactFlow
            nodes={displayNodes}
            edges={displayEdges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onMoveEnd={(_, viewport) => setZoom(viewport.zoom)}
            onNodeMouseEnter={(_, node) => setHoveredNodeId(node.id)}
            onNodeMouseLeave={() => setHoveredNodeId(null)}
            onNodeClick={(_, node) => {
              setSelectedNodeId(node.id)
              if (localMode) setFocusId(node.id)
            }}
            onPaneClick={() => {
              setSelectedNodeId(null)
              setHoveredNodeId(null)
            }}
            fitView
            minZoom={0.2}
            maxZoom={2}
            className="bg-[radial-gradient(circle_at_30%_20%,rgba(14,165,233,0.08),transparent_28%),radial-gradient(circle_at_70%_70%,rgba(16,185,129,0.07),transparent_30%),linear-gradient(180deg,#f8fafc_0%,#eef2f7_100%)]"
          >
            <Background color="rgba(100,116,139,0.22)" gap={28} size={0.7} />
            <Controls className="rounded-lg border border-white/70 bg-white/75 shadow-md backdrop-blur-md" />
            <MiniMap
              className="rounded-lg border border-white/70 bg-white/70 backdrop-blur-md"
              nodeColor={node => (node.type === 'page' ? '#0ea5e9' : '#10b981')}
              maskColor="rgba(15, 23, 42, 0.06)"
            />
          </ReactFlow>
          <div className="pointer-events-none absolute left-4 top-4 rounded-2xl border border-white/70 bg-white/70 px-3 py-2 text-xs text-slate-600 shadow-sm backdrop-blur-md">
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-sky-500 shadow-[0_0_14px_rgba(14,165,233,0.45)]" />
              Pages
              <span className="ml-3 h-2.5 w-2.5 rounded-full bg-emerald-500 shadow-[0_0_14px_rgba(16,185,129,0.45)]" />
              Entities
              <span className="ml-3 h-3.5 w-3.5 rounded-full border border-yellow-300" />
              Hub
              <span className="ml-3 h-1.5 w-1.5 rounded-full bg-slate-400 opacity-60" />
              Orphan
            </div>
          </div>
        </div>

        <aside className="w-80 shrink-0 border-l border-border bg-card/60 p-4">
          {!detail ? (
            <EmptyState icon="database" title="No node selected" description="Click a node to inspect graph details, metrics, and local neighborhood." />
          ) : (
            <div className="space-y-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Node Detail</p>
                <h2 className="mt-1 text-lg font-semibold">{detail.label}</h2>
                <div className="mt-2 flex flex-wrap gap-2">
                  {detail.status && <StatusBadge status={detail.status} type="page" />}
                  {detail.pageType && <StatusBadge status={detail.pageType} type="pageType" />}
                  {detail.entityType && <StatusBadge status={detail.entityType} type="entity" />}
                </div>
              </div>

              {detail.description && <p className="text-sm text-muted-foreground">{detail.description}</p>}

              <EvidenceCard
                title={detail.label}
                subtitle={detail.type === 'page' ? 'Graph page node' : 'Graph entity node'}
                snippet={detail.description || `Graph node with ${detail.metrics.degree} direct connections.`}
                type={detail.pageType || detail.entityType || detail.type}
                confidence={detail.metrics.hubScore ? Math.min(detail.metrics.hubScore, 100) : undefined}
                meta={[
                  `Degree: ${detail.metrics.degree}`,
                  `Backlinks: ${detail.metrics.backlinkCount}`,
                  `Sources: ${detail.metrics.sourceCount ?? detail.sourceIds.length}`,
                  `Citations: ${detail.metrics.citationCount ?? 0}`,
                ]}
                actions={[
                  ...(detail.url && detail.type === 'page' ? [{ label: 'Open page', href: detail.url, variant: 'primary' as const }] : []),
                  ...(detail.type === 'page' && detail.url ? [{
                    label: 'Ask this page',
                    href: `/ask?pageId=${encodeURIComponent(detail.id)}&pageTitle=${encodeURIComponent(detail.label)}&pageSummary=${encodeURIComponent(detail.description ?? '')}`,
                  }] : []),
                  ...(detail.sourceIds[0] ? [{ label: 'Inspect source', href: `/sources/${detail.sourceIds[0]}` }] : []),
                  ...(detail.sourceIds[0] ? [{
                    label: 'Ask linked source',
                    href: `/ask?sourceId=${encodeURIComponent(detail.sourceIds[0])}&sourceTitle=${encodeURIComponent(detail.label)}`,
                  }] : []),
                ]}
              />

              <div className="grid grid-cols-3 gap-2">
                <div className="rounded-lg border border-border bg-background p-3">
                  <p className="text-xs text-muted-foreground">Degree</p>
                  <p className="text-lg font-semibold">{detail.metrics.degree}</p>
                </div>
                <div className="rounded-lg border border-border bg-background p-3">
                  <p className="text-xs text-muted-foreground">Backlinks</p>
                  <p className="text-lg font-semibold">{detail.metrics.backlinkCount}</p>
                </div>
                <div className="rounded-lg border border-border bg-background p-3">
                  <p className="text-xs text-muted-foreground">Entities</p>
                  <p className="text-lg font-semibold">{detail.metrics.relatedEntityCount}</p>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div className="rounded-lg border border-border bg-background p-3">
                  <p className="text-xs text-muted-foreground">Sources</p>
                  <p className="text-lg font-semibold">{detail.metrics.sourceCount ?? detail.sourceIds.length}</p>
                </div>
                <div className="rounded-lg border border-border bg-background p-3">
                  <p className="text-xs text-muted-foreground">Citations</p>
                  <p className="text-lg font-semibold">{detail.metrics.citationCount ?? 0}</p>
                </div>
                <div className="rounded-lg border border-border bg-background p-3">
                  <p className="text-xs text-muted-foreground">Hub</p>
                  <p className="text-lg font-semibold">{detail.metrics.hubScore ?? 0}</p>
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                {detail.flags?.hub && <span className="inline-flex items-center gap-1 rounded-full bg-yellow-100 px-2 py-1 text-xs text-yellow-700"><Star className="h-3 w-3" /> Hub</span>}
                {detail.flags?.stale && <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-1 text-xs text-red-700"><Clock className="h-3 w-3" /> Stale</span>}
                {detail.flags?.conflict && <span className="inline-flex items-center gap-1 rounded-full bg-orange-100 px-2 py-1 text-xs text-orange-700"><AlertTriangle className="h-3 w-3" /> Conflict</span>}
                {detail.flags?.orphan && <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700">Orphan</span>}
                {typeof detail.metrics.clusterId === 'number' && <span className="rounded-full bg-muted px-2 py-1 text-xs">Cluster {detail.metrics.clusterId}</span>}
              </div>

              {detail.sourceIds.length > 0 && (
                <div>
                  <p className="text-sm font-semibold">Source Links</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {detail.sourceIds.map(sourceId => (
                      <Link key={sourceId} href={`/sources/${sourceId}`} className="rounded-full bg-muted px-2 py-1 text-xs hover:bg-accent">
                        {sourceId}
                      </Link>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <div className="mb-2 flex items-center justify-between">
                  <p className="text-sm font-semibold">Connections</p>
                  <button
                    onClick={() => {
                      setLocalMode(true)
                      setFocusId(detail.id)
                    }}
                    className="text-xs text-primary hover:underline"
                  >
                    Explore local graph
                  </button>
                </div>
                <div className="mb-3 flex flex-wrap gap-2">
                  {detail.url && detail.type === 'page' && (
                    <Link href={detail.url} className="rounded-md border border-input px-2 py-1 text-xs hover:bg-accent">
                      Open page
                    </Link>
                  )}
                  {detail.type === 'page' && detail.url && (
                    <Link
                      href={`/ask?pageId=${encodeURIComponent(detail.id)}&pageTitle=${encodeURIComponent(detail.label)}&pageSummary=${encodeURIComponent(detail.description ?? '')}`}
                      className="rounded-md border border-input px-2 py-1 text-xs hover:bg-accent"
                    >
                      Ask this page
                    </Link>
                  )}
                  {detail.sourceIds[0] && (
                    <Link href={`/sources/${detail.sourceIds[0]}`} className="rounded-md border border-input px-2 py-1 text-xs hover:bg-accent">
                      Inspect source
                    </Link>
                  )}
                  {detail.sourceIds[0] && (
                    <Link
                      href={`/ask?sourceId=${encodeURIComponent(detail.sourceIds[0])}&sourceTitle=${encodeURIComponent(detail.label)}`}
                      className="rounded-md border border-input px-2 py-1 text-xs hover:bg-accent"
                    >
                      Ask linked source
                    </Link>
                  )}
                  <button
                    onClick={() => {
                      setNodeType(detail.type)
                      if (detail.pageType) setSelectedPageTypes([detail.pageType])
                      if (detail.entityType) setSelectedEntityTypes([detail.entityType])
                    }}
                    className="rounded-md border border-input px-2 py-1 text-xs hover:bg-accent"
                  >
                    Filter by type
                  </button>
                </div>
                <div className="space-y-2">
                  {detail.connections.map(connection => {
                    const otherNode = data.detailById?.[connection.otherNodeId]
                    return (
                      <button
                        key={connection.id}
                        onClick={() => {
                          setSelectedNodeId(connection.otherNodeId)
                          if (localMode) setFocusId(connection.otherNodeId)
                        }}
                        className="block w-full rounded-lg border border-border bg-background p-3 text-left hover:border-primary/50"
                      >
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-sm font-medium">{otherNode?.label ?? connection.otherNodeId}</span>
                          <span className="text-xs text-muted-foreground">{connection.relationType}</span>
                        </div>
                      </button>
                    )
                  })}
                </div>
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}
