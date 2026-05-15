import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { StudioPlaybackPanel } from './StudioPlaybackPanel';
import { useFlowStore } from '@/store';
import { createInitialFlowState } from '@/store/persistence';
import type { FlowEdge, FlowNode, FlowTab } from '@/lib/types';

function createNode(id: string, label: string): FlowNode {
  return {
    id,
    type: 'process',
    position: { x: 0, y: 0 },
    data: { label, subLabel: '', color: 'slate' },
  };
}

function createEdge(id: string, source: string, target: string): FlowEdge {
  return { id, source, target };
}

function createTab(id: string, name: string, nodes: FlowNode[], edges: FlowEdge[]): FlowTab {
  return {
    id,
    name,
    nodes,
    edges,
    history: { past: [], future: [] },
  };
}

describe('StudioPlaybackPanel', () => {
  beforeEach(() => {
    useFlowStore.setState(createInitialFlowState());
  });

  it('renders and updates playback state without entering a subscription loop', () => {
    const nodes = [createNode('n1', 'Start'), createNode('n2', 'Finish')];
    const edges = [createEdge('e1', 'n1', 'n2')];
    const tab = createTab('tab-1', 'Main', nodes, edges);

    useFlowStore.setState({
      tabs: [tab],
      activeTabId: 'tab-1',
      nodes,
      edges,
    });

    render(
      <StudioPlaybackPanel
        nodes={nodes}
        edges={edges}
        currentStepIndex={-1}
        totalSteps={0}
        isPlaying={false}
        onStartPlayback={vi.fn()}
        onPlayPause={vi.fn()}
        onStop={vi.fn()}
        onScrubToStep={vi.fn()}
        onNext={vi.fn()}
        onPrev={vi.fn()}
        playbackSpeed={2000}
        onPlaybackSpeedChange={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Generate smart timeline' }));

    expect(screen.getByText('Timeline')).not.toBeNull();
    expect(useFlowStore.getState().tabs[0].playback?.timeline).toHaveLength(2);
  });
});
