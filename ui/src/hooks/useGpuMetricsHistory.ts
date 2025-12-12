'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { GpuInfo } from '@/lib/api';

interface GpuHistoryEntry {
  utilization: number[];
  memoryUsedPct: number[];
  temperature: number[];
  powerDraw: number[];
}

interface GpuMetricsHistory {
  [gpuKey: string]: GpuHistoryEntry;
}

const MAX_HISTORY = 30; // Keep 30 data points (~150 seconds at 5s interval)

export function useGpuMetricsHistory() {
  const [history, setHistory] = useState<GpuMetricsHistory>({});
  const lastUpdateRef = useRef<number>(0);
  const MIN_UPDATE_INTERVAL = 4000; // Minimum 4 seconds between updates

  const updateHistory = useCallback((gpus: GpuInfo[]) => {
    const now = Date.now();

    // Throttle updates to avoid too frequent re-renders
    if (now - lastUpdateRef.current < MIN_UPDATE_INTERVAL) {
      return;
    }
    lastUpdateRef.current = now;

    setHistory(prev => {
      const newHistory = { ...prev };

      gpus.forEach(gpu => {
        const key = `${gpu.node}-${gpu.index}`;
        const existing = newHistory[key] || {
          utilization: [],
          memoryUsedPct: [],
          temperature: [],
          powerDraw: [],
        };

        const memoryUsedPct = gpu.memory_total_gb && gpu.memory_total_gb > 0
          ? (gpu.memory_used_gb || 0) / gpu.memory_total_gb * 100
          : 0;

        newHistory[key] = {
          utilization: [...existing.utilization.slice(-MAX_HISTORY + 1), gpu.utilization || 0],
          memoryUsedPct: [...existing.memoryUsedPct.slice(-MAX_HISTORY + 1), memoryUsedPct],
          temperature: [...existing.temperature.slice(-MAX_HISTORY + 1), gpu.temp_c || 0],
          powerDraw: [...existing.powerDraw.slice(-MAX_HISTORY + 1), gpu.power_w || 0],
        };
      });

      return newHistory;
    });
  }, []);

  const getGpuHistory = useCallback((node: string, index: string): GpuHistoryEntry | null => {
    const key = `${node}-${index}`;
    return history[key] || null;
  }, [history]);

  return { history, updateHistory, getGpuHistory };
}
