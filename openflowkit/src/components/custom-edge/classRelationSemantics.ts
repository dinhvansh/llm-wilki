import { isClassRelationToken, type ClassRelationToken } from '@/lib/relationSemantics';
import type { EdgeData } from '@/lib/types';

export const CLASS_MARKER_ARROW_FILLED = 'ofk-class-arrow-filled';
export const CLASS_MARKER_ARROW_OPEN = 'ofk-class-arrow-open';
export const CLASS_MARKER_TRIANGLE_OPEN = 'ofk-class-triangle-open';
export const CLASS_MARKER_DIAMOND_OPEN = 'ofk-class-diamond-open';
export const CLASS_MARKER_DIAMOND_FILLED = 'ofk-class-diamond-filled';
export const ER_MARKER_BAR = 'ofk-er-bar';
export const ER_MARKER_CIRCLE = 'ofk-er-circle';
export const ER_MARKER_CROW = 'ofk-er-crow';

interface ClassRelationVisualSpec {
  markerStartId?: string;
  markerEndId?: string;
  dashed: boolean;
}

type RelationVisualSpec = ClassRelationVisualSpec;

function getClassRelationToken(data: EdgeData | undefined, label: unknown): ClassRelationToken | undefined {
  const dataToken = typeof data?.classRelation === 'string' ? data.classRelation.trim() : '';
  if (dataToken && isClassRelationToken(dataToken)) {
    return dataToken;
  }

  const labelToken = typeof label === 'string' ? label.trim() : '';
  if (labelToken && isClassRelationToken(labelToken)) {
    return labelToken;
  }

  return undefined;
}

export function resolveClassRelationVisualSpec(
  enabled: boolean,
  data: EdgeData | undefined,
  label: unknown
): ClassRelationVisualSpec | null {
  if (!enabled) return null;

  const token = getClassRelationToken(data, label);
  if (!token) return null;

  if (token === '<|--') {
    return { markerStartId: CLASS_MARKER_TRIANGLE_OPEN, dashed: false };
  }
  if (token === '--|>') {
    return { markerEndId: CLASS_MARKER_TRIANGLE_OPEN, dashed: false };
  }
  if (token === '*--') {
    return { markerStartId: CLASS_MARKER_DIAMOND_FILLED, dashed: false };
  }
  if (token === '--*') {
    return { markerEndId: CLASS_MARKER_DIAMOND_FILLED, dashed: false };
  }
  if (token === 'o--') {
    return { markerStartId: CLASS_MARKER_DIAMOND_OPEN, dashed: false };
  }
  if (token === '--o') {
    return { markerEndId: CLASS_MARKER_DIAMOND_OPEN, dashed: false };
  }
  if (token === '..>') {
    return { markerEndId: CLASS_MARKER_ARROW_OPEN, dashed: true };
  }
  if (token === '<..') {
    return { markerStartId: CLASS_MARKER_ARROW_OPEN, dashed: true };
  }
  if (token === '<--') {
    return { markerStartId: CLASS_MARKER_ARROW_FILLED, dashed: false };
  }
  if (token === '-->') {
    return { markerEndId: CLASS_MARKER_ARROW_FILLED, dashed: false };
  }
  if (token === '<-->') {
    return { markerStartId: CLASS_MARKER_ARROW_FILLED, markerEndId: CLASS_MARKER_ARROW_FILLED, dashed: false };
  }
  if (token === '..') {
    return { dashed: true };
  }
  if (token === '--') {
    return { dashed: false };
  }

  return null;
}

function resolveERTokenEndpointMarker(token: string): string[] {
  if (token === '||') return [ER_MARKER_BAR];
  if (token === '|{') return [ER_MARKER_BAR, ER_MARKER_CROW];
  if (token === 'o{') return [ER_MARKER_CIRCLE, ER_MARKER_CROW];
  if (token === '}|') return [ER_MARKER_CROW, ER_MARKER_BAR];
  if (token === '}o') return [ER_MARKER_CROW, ER_MARKER_CIRCLE];
  return [];
}

function resolveERRelationVisualSpec(data: EdgeData | undefined): RelationVisualSpec | null {
  const relation = typeof data?.erRelation === 'string' ? data.erRelation.trim() : '';
  if (!relation) return null;

  const relationMatch = relation.match(/^(\|\||\|\{|o\{|\}\||\}o)(--|\.\.)(\|\||\|\{|o\{|\}\||\}o)$/);
  if (!relationMatch) return null;

  const startMarkers = resolveERTokenEndpointMarker(relationMatch[1]);
  const connector = relationMatch[2];
  const endMarkers = resolveERTokenEndpointMarker(relationMatch[3]);

  // React Flow allows one marker per side; prioritize crow's-foot, then circle, then bar.
  function pickMarker(markers: string[]): string | undefined {
    if (markers.includes(ER_MARKER_CROW)) return ER_MARKER_CROW;
    if (markers.includes(ER_MARKER_CIRCLE)) return ER_MARKER_CIRCLE;
    if (markers.includes(ER_MARKER_BAR)) return ER_MARKER_BAR;
    return undefined;
  }

  return {
    markerStartId: pickMarker(startMarkers),
    markerEndId: pickMarker(endMarkers),
    dashed: connector === '..',
  };
}

export function resolveRelationVisualSpec(
  enabled: boolean,
  data: EdgeData | undefined,
  label: unknown
): RelationVisualSpec | null {
  if (!enabled) return null;

  const classSpec = resolveClassRelationVisualSpec(true, data, label);
  if (classSpec) return classSpec;

  return resolveERRelationVisualSpec(data);
}

export function toMarkerUrl(markerId: string | undefined): string | undefined {
  return markerId ? `url(#${markerId})` : undefined;
}
