import type { FlowNode } from '@/lib/types';
import { createId } from '@/lib/id';
import { createTextNode } from '@/hooks/node-operations/utils';

type ParseResultLike = {
  metadata?: { direction?: string };
  direction?: string;
};

export function isEditablePasteTarget(target: EventTarget | null): boolean {
  const element = target instanceof HTMLElement ? target : null;
  if (!element) return false;
  const tagName = element.tagName.toLowerCase();
  if (tagName === 'input' || tagName === 'textarea' || tagName === 'select') return true;
  if (element.isContentEditable) return true;
  return element.closest('[contenteditable="true"]') !== null;
}

export function resolveLayoutDirection(result: ParseResultLike): 'TB' | 'LR' | 'RL' | 'BT' {
  const direction = result.metadata?.direction || result.direction || 'TB';
  if (direction === 'LR' || direction === 'RL' || direction === 'BT' || direction === 'TB') {
    return direction;
  }
  return 'TB';
}

export function createPastedTextNode(
  text: string,
  position: { x: number; y: number },
  activeLayerId: string
): FlowNode {
  const textNodeId = createId('text');
  const newTextNode = createTextNode(textNodeId, position, text);
  newTextNode.data = {
    ...newTextNode.data,
    layerId: activeLayerId,
  };
  return newTextNode;
}
