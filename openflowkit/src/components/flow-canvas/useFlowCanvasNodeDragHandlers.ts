import type { FlowNode } from '@/lib/types';

interface UseFlowCanvasNodeDragHandlersParams {
    toTypedFlowNode: (node: unknown) => FlowNode;
    onNodeDragStart: (event: unknown, node: FlowNode) => void;
    onNodeDrag: (event: unknown, node: FlowNode, draggedNodes: FlowNode[]) => void;
    onNodeDragStop: (event: unknown, node: FlowNode) => void;
    startInteractionLowDetail: () => void;
    endInteractionLowDetail: () => void;
    updateAlignmentGuidesForNode: (node: FlowNode) => void;
    clearAlignmentGuides: () => void;
}

export function useFlowCanvasNodeDragHandlers({
    toTypedFlowNode,
    onNodeDragStart,
    onNodeDrag,
    onNodeDragStop,
    startInteractionLowDetail,
    endInteractionLowDetail,
    updateAlignmentGuidesForNode,
    clearAlignmentGuides,
}: UseFlowCanvasNodeDragHandlersParams) {
    const handleNodeDragStart = (event: unknown, node: unknown): void => {
        startInteractionLowDetail();
        onNodeDragStart(event, toTypedFlowNode(node));
    };

    const handleNodeDrag = (event: unknown, node: unknown, _draggedNodes: unknown): void => {
        const flowNode = toTypedFlowNode(node);
        onNodeDrag(event, flowNode, []);
        updateAlignmentGuidesForNode(flowNode);
    };

    const handleNodeDragStop = (event: unknown, node: unknown): void => {
        onNodeDragStop(event, toTypedFlowNode(node));
        clearAlignmentGuides();
        endInteractionLowDetail();
    };

    return {
        handleNodeDragStart,
        handleNodeDrag,
        handleNodeDragStop,
    };
}
