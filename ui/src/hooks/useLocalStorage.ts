'use client';

import { useState, useEffect, useCallback } from 'react';

export function useLocalStorage<T>(key: string, initialValue: T): [T, (value: T | ((prev: T) => T)) => void] {
  // State to store our value
  // Pass initial state function to useState so logic is only executed once
  const [storedValue, setStoredValue] = useState<T>(() => {
    if (typeof window === 'undefined') {
      return initialValue;
    }
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.warn(`Error reading localStorage key "${key}":`, error);
      return initialValue;
    }
  });

  // Return a wrapped version of useState's setter function that persists to localStorage
  const setValue = useCallback((value: T | ((prev: T) => T)) => {
    try {
      // Allow value to be a function so we have same API as useState
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(key, JSON.stringify(valueToStore));
      }
    } catch (error) {
      console.warn(`Error setting localStorage key "${key}":`, error);
    }
  }, [key, storedValue]);

  return [storedValue, setValue];
}

// Hook for managing collapsed state of panels
export interface PanelCollapseState {
  services: boolean;
  containers: boolean;
  audit: boolean;
  storage: boolean;
  alerts: boolean;
  aiModels: boolean;
}

const defaultCollapseState: PanelCollapseState = {
  services: false,
  containers: false,
  audit: false,
  storage: false,
  alerts: false,
  aiModels: false,
};

export function usePanelCollapse() {
  const [collapsed, setCollapsed] = useLocalStorage<PanelCollapseState>('hydra-ui-collapsed-panels', defaultCollapseState);

  const togglePanel = useCallback((panel: keyof PanelCollapseState) => {
    setCollapsed(prev => ({
      ...prev,
      [panel]: !prev[panel]
    }));
  }, [setCollapsed]);

  const isCollapsed = useCallback((panel: keyof PanelCollapseState) => {
    return collapsed[panel] ?? false;
  }, [collapsed]);

  return { collapsed, togglePanel, isCollapsed };
}

// Hook for user preferences
export interface UserPreferences {
  refreshInterval: number;
  theme: 'dark' | 'light';
  showReasoning: boolean;  // For Letta chat
  compactMode: boolean;
}

const defaultPreferences: UserPreferences = {
  refreshInterval: 5000,
  theme: 'dark',
  showReasoning: false,
  compactMode: false,
};

export function useUserPreferences() {
  const [preferences, setPreferences] = useLocalStorage<UserPreferences>('hydra-ui-preferences', defaultPreferences);

  const updatePreference = useCallback(<K extends keyof UserPreferences>(
    key: K,
    value: UserPreferences[K]
  ) => {
    setPreferences(prev => ({
      ...prev,
      [key]: value
    }));
  }, [setPreferences]);

  return { preferences, updatePreference, setPreferences };
}
