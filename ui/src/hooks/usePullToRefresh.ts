'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

interface PullToRefreshConfig {
  onRefresh: () => Promise<void> | void;
  threshold?: number;  // How far to pull before triggering (default 80px)
  resistance?: number; // How much to resist the pull (default 2.5)
}

interface PullToRefreshState {
  isPulling: boolean;
  pullDistance: number;
  isRefreshing: boolean;
}

export function usePullToRefresh({
  onRefresh,
  threshold = 80,
  resistance = 2.5
}: PullToRefreshConfig) {
  const [state, setState] = useState<PullToRefreshState>({
    isPulling: false,
    pullDistance: 0,
    isRefreshing: false,
  });

  const startY = useRef(0);
  const currentY = useRef(0);

  const handleTouchStart = useCallback((e: TouchEvent) => {
    // Only start pull if we're at the top of the page
    if (window.scrollY <= 0) {
      startY.current = e.touches[0].clientY;
      setState(prev => ({ ...prev, isPulling: true }));
    }
  }, []);

  const handleTouchMove = useCallback((e: TouchEvent) => {
    if (!state.isPulling || state.isRefreshing) return;

    currentY.current = e.touches[0].clientY;
    const rawDistance = currentY.current - startY.current;

    // Only track downward pulls
    if (rawDistance > 0 && window.scrollY <= 0) {
      // Apply resistance to make pull feel natural
      const pullDistance = Math.min(rawDistance / resistance, threshold * 1.5);
      setState(prev => ({ ...prev, pullDistance }));

      // Prevent default scroll while pulling
      if (pullDistance > 10) {
        e.preventDefault();
      }
    }
  }, [state.isPulling, state.isRefreshing, resistance, threshold]);

  const handleTouchEnd = useCallback(async () => {
    if (!state.isPulling) return;

    if (state.pullDistance >= threshold && !state.isRefreshing) {
      setState(prev => ({ ...prev, isRefreshing: true, pullDistance: threshold }));

      try {
        await onRefresh();
      } finally {
        // Delay hiding to show completion
        setTimeout(() => {
          setState({ isPulling: false, pullDistance: 0, isRefreshing: false });
        }, 300);
      }
    } else {
      setState({ isPulling: false, pullDistance: 0, isRefreshing: false });
    }
  }, [state.isPulling, state.pullDistance, state.isRefreshing, threshold, onRefresh]);

  useEffect(() => {
    // Only enable on touch devices
    const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    if (!isTouchDevice) return;

    document.addEventListener('touchstart', handleTouchStart, { passive: true });
    document.addEventListener('touchmove', handleTouchMove, { passive: false });
    document.addEventListener('touchend', handleTouchEnd, { passive: true });

    return () => {
      document.removeEventListener('touchstart', handleTouchStart);
      document.removeEventListener('touchmove', handleTouchMove);
      document.removeEventListener('touchend', handleTouchEnd);
    };
  }, [handleTouchStart, handleTouchMove, handleTouchEnd]);

  return state;
}
