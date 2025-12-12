'use client';

import { useState, useCallback, useRef } from 'react';

interface MetricsHistoryData {
  cpu: number[];
  memory: number[];
  disk: number[];
  gpuTemp: number[];
}

const MAX_HISTORY = 20; // Keep 20 data points (~100 seconds at 5s interval)

export function useMetricsHistory() {
  const [history, setHistory] = useState<MetricsHistoryData>({
    cpu: [],
    memory: [],
    disk: [],
    gpuTemp: [],
  });

  const lastValuesRef = useRef<{
    cpu: number | null;
    memory: number | null;
    disk: number | null;
    gpuTemp: number | null;
  }>({
    cpu: null,
    memory: null,
    disk: null,
    gpuTemp: null,
  });

  const addDataPoint = useCallback((
    cpu: number | null | undefined,
    memory: number | null | undefined,
    disk: number | null | undefined,
    gpuTemp: number | null | undefined
  ) => {
    // Only update if values have actually changed (avoid duplicates on mount)
    const cpuVal = cpu ?? null;
    const memVal = memory ?? null;
    const diskVal = disk ?? null;
    const gpuTempVal = gpuTemp ?? null;

    const last = lastValuesRef.current;

    // Skip if all values are the same as last time
    if (
      cpuVal === last.cpu &&
      memVal === last.memory &&
      diskVal === last.disk &&
      gpuTempVal === last.gpuTemp
    ) {
      return;
    }

    lastValuesRef.current = {
      cpu: cpuVal,
      memory: memVal,
      disk: diskVal,
      gpuTemp: gpuTempVal,
    };

    setHistory(prev => ({
      cpu: cpuVal !== null
        ? [...prev.cpu.slice(-MAX_HISTORY + 1), cpuVal]
        : prev.cpu,
      memory: memVal !== null
        ? [...prev.memory.slice(-MAX_HISTORY + 1), memVal]
        : prev.memory,
      disk: diskVal !== null
        ? [...prev.disk.slice(-MAX_HISTORY + 1), diskVal]
        : prev.disk,
      gpuTemp: gpuTempVal !== null
        ? [...prev.gpuTemp.slice(-MAX_HISTORY + 1), gpuTempVal]
        : prev.gpuTemp,
    }));
  }, []);

  return { history, addDataPoint };
}
