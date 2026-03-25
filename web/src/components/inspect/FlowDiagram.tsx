import { useMemo } from 'react'
import { ReactFlow, Background, Controls } from '@xyflow/react'
import type { Node, Edge } from '@xyflow/react'
import dagre from 'dagre'
import '@xyflow/react/dist/style.css'

import { StepNode } from './StepNode'
import type { StepNodeData } from './StepNode'
import { DataFlowEdge } from './DataFlowEdge'
import { cn } from '@/lib/utils'
import type { Capability } from '@/types/api'

const NODE_WIDTH = 280
const NODE_HEIGHT = 100

const nodeTypes = { step: StepNode }
const edgeTypes = { dataflow: DataFlowEdge }

function buildLayout(capability: Capability): { nodes: Node[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'TB', nodesep: 40, ranksep: 60 })

  // Add nodes from steps
  const nodes: Node[] = capability.steps.map((step, i) => {
    const id = `step-${i}`
    g.setNode(id, { width: NODE_WIDTH, height: NODE_HEIGHT })

    return {
      id,
      type: 'step',
      position: { x: 0, y: 0 }, // will be set by dagre
      data: {
        skillRef: step.skill_ref,
        role: step.role,
        required: step.required,
        contentPreview: step.data_classification,
      } satisfies StepNodeData,
    }
  })

  // Add edges from data_flow
  // data_flow uses bare slugs (e.g. "review-security") while steps use loom:// URIs
  const normalize = (ref: string) => ref.replace(/^loom:\/\//, '')
  const edges: Edge[] = capability.data_flow.map((flow, i) => {
    const sourceIdx = capability.steps.findIndex((s) => normalize(s.skill_ref) === flow.from_step)
    const targetIdx = capability.steps.findIndex((s) => normalize(s.skill_ref) === flow.to_step)
    const sourceId = `step-${sourceIdx >= 0 ? sourceIdx : 0}`
    const targetId = `step-${targetIdx >= 0 ? targetIdx : 0}`

    g.setEdge(sourceId, targetId)

    return {
      id: `edge-${i}`,
      source: sourceId,
      target: targetId,
      type: 'dataflow',
      data: { classification: flow.classification },
    }
  })

  // If no data_flow edges, create sequential edges between steps
  if (edges.length === 0 && capability.steps.length > 1) {
    for (let i = 0; i < capability.steps.length - 1; i++) {
      const sourceId = `step-${i}`
      const targetId = `step-${i + 1}`
      g.setEdge(sourceId, targetId)
      edges.push({
        id: `edge-seq-${i}`,
        source: sourceId,
        target: targetId,
        type: 'dataflow',
        data: { classification: 'internal' },
      })
    }
  }

  // Run dagre layout
  dagre.layout(g)

  // Apply positions from dagre
  for (const node of nodes) {
    const pos = g.node(node.id)
    if (pos) {
      node.position = {
        x: pos.x - NODE_WIDTH / 2,
        y: pos.y - NODE_HEIGHT / 2,
      }
    }
  }

  return { nodes, edges }
}

interface FlowDiagramProps {
  capability: Capability
  className?: string
}

export function FlowDiagram({ capability, className }: FlowDiagramProps) {
  const { nodes, edges } = useMemo(() => buildLayout(capability), [capability])

  return (
    <div className={cn('h-[400px] rounded-lg border bg-background', className)}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        panOnScroll
        minZoom={0.3}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={16} size={1} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  )
}
