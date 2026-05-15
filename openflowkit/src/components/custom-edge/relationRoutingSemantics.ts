import type { EdgeData } from '@/lib/types';

interface NodeLike {
  type?: string;
}

function isClassOrEntityNodeType(type: string | undefined): boolean {
  return type === 'class' || type === 'er_entity';
}

export function shouldUseOrthogonalRelationRouting(
  enabled: boolean,
  data: EdgeData | undefined,
  sourceNode: NodeLike | undefined,
  targetNode: NodeLike | undefined
): boolean {
  if (!enabled) return false;

  if (typeof data?.classRelation === 'string' && data.classRelation.trim().length > 0) {
    return true;
  }
  if (typeof data?.erRelation === 'string' && data.erRelation.trim().length > 0) {
    return true;
  }

  return isClassOrEntityNodeType(sourceNode?.type) && isClassOrEntityNodeType(targetNode?.type);
}
