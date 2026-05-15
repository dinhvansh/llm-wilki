import { useEffect, useRef, useState } from 'react';
import type { ViewSettings } from '@/store/types';
import {
  getInteractionLodCooldownMs,
  isInteractionLowDetailModeActive,
} from './largeGraphSafetyMode';

interface UseFlowCanvasInteractionLodParams {
  safetyModeActive: boolean;
  largeGraphSafetyProfile: ViewSettings['largeGraphSafetyProfile'];
}

interface FlowCanvasInteractionLodState {
  interactionLowDetailModeActive: boolean;
  startInteractionLowDetail: () => void;
  endInteractionLowDetail: () => void;
}

export function useFlowCanvasInteractionLod({
  safetyModeActive,
  largeGraphSafetyProfile,
}: UseFlowCanvasInteractionLodParams): FlowCanvasInteractionLodState {
  const [isInteracting, setIsInteracting] = useState(false);
  const [isInteractionCooldown, setIsInteractionCooldown] = useState(false);
  const interactionCooldownTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (interactionCooldownTimeoutRef.current) {
        clearTimeout(interactionCooldownTimeoutRef.current);
      }
    };
  }, []);

  function startInteractionLowDetail(): void {
    if (interactionCooldownTimeoutRef.current) {
      clearTimeout(interactionCooldownTimeoutRef.current);
      interactionCooldownTimeoutRef.current = null;
    }
    setIsInteractionCooldown(false);
    setIsInteracting(true);
  }

  function endInteractionLowDetail(): void {
    setIsInteracting(false);
    setIsInteractionCooldown(true);

    if (interactionCooldownTimeoutRef.current) {
      clearTimeout(interactionCooldownTimeoutRef.current);
    }
    interactionCooldownTimeoutRef.current = setTimeout(() => {
      setIsInteractionCooldown(false);
      interactionCooldownTimeoutRef.current = null;
    }, getInteractionLodCooldownMs(largeGraphSafetyProfile));
  }

  const interactionLowDetailModeActive = isInteractionLowDetailModeActive(
    safetyModeActive,
    isInteracting || isInteractionCooldown
  );

  return {
    interactionLowDetailModeActive,
    startInteractionLowDetail,
    endInteractionLowDetail,
  };
}
