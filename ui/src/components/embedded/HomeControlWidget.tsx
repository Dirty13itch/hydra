'use client';

import { useState, useEffect, useCallback } from 'react';

const HA_URL = 'http://192.168.1.244:8123';

// Scene definitions for quick access
const SCENES = {
  movieNight: {
    id: 'scene.movie_night',
    name: 'Movie Night',
    icon: '🎬',
    description: 'Dim lights, pause downloads, quiet mode',
  },
  workFocus: {
    id: 'scene.work_focus',
    name: 'Work Focus',
    icon: '💼',
    description: 'Optimal lighting, DND, inference priority',
  },
  partyMode: {
    id: 'scene.party_mode',
    name: 'Party Mode',
    icon: '🎉',
    description: 'Music routing, lighting effects',
  },
  goodnight: {
    id: 'scene.goodnight',
    name: 'Goodnight',
    icon: '🌙',
    description: 'Security check, energy savings',
  },
  allOff: {
    id: 'scene.all_off',
    name: 'All Off',
    icon: '⭕',
    description: 'Turn off all lights and devices',
  },
};

// Light groups for quick control
const LIGHT_GROUPS = {
  office: {
    id: 'light.office',
    name: 'Office',
    icon: '🖥️',
  },
  livingRoom: {
    id: 'light.living_room',
    name: 'Living Room',
    icon: '🛋️',
  },
  bedroom: {
    id: 'light.bedroom',
    name: 'Bedroom',
    icon: '🛏️',
  },
  kitchen: {
    id: 'light.kitchen',
    name: 'Kitchen',
    icon: '🍳',
  },
  all: {
    id: 'light.all_lights',
    name: 'All Lights',
    icon: '💡',
  },
};

// Climate entities
const CLIMATE = {
  main: {
    id: 'climate.main_thermostat',
    name: 'Thermostat',
    icon: '🌡️',
  },
};

type SceneKey = keyof typeof SCENES;
type LightGroupKey = keyof typeof LIGHT_GROUPS;

interface LightState {
  entityId: string;
  state: 'on' | 'off' | 'unavailable';
  brightness?: number; // 0-255
  colorTemp?: number;
}

interface ClimateState {
  entityId: string;
  state: 'heat' | 'cool' | 'auto' | 'off';
  currentTemp: number;
  targetTemp: number;
  humidity?: number;
}

interface HomeControlWidgetProps {
  // Show scenes section
  showScenes?: boolean;
  // Show lights section
  showLights?: boolean;
  // Show climate section
  showClimate?: boolean;
  // Compact mode
  compact?: boolean;
  // Height
  height?: number;
  // Show header
  showHeader?: boolean;
}

export function HomeControlWidget({
  showScenes = true,
  showLights = true,
  showClimate = true,
  compact = false,
  height = 350,
  showHeader = true,
}: HomeControlWidgetProps) {
  const [lightStates, setLightStates] = useState<Record<string, LightState>>({});
  const [climateState, setClimateState] = useState<ClimateState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeScene, setActiveScene] = useState<SceneKey | null>(null);
  const [isActivating, setIsActivating] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch current states from Home Assistant
  const fetchStates = useCallback(async () => {
    try {
      // In production, this would call Home Assistant API with long-lived access token
      // For now, simulate with mock data
      const mockLights: Record<string, LightState> = {};
      Object.entries(LIGHT_GROUPS).forEach(([key, config]) => {
        mockLights[config.id] = {
          entityId: config.id,
          state: Math.random() > 0.5 ? 'on' : 'off',
          brightness: Math.floor(Math.random() * 255),
        };
      });

      const mockClimate: ClimateState = {
        entityId: CLIMATE.main.id,
        state: 'heat',
        currentTemp: 68 + Math.floor(Math.random() * 5),
        targetTemp: 70,
        humidity: 35 + Math.floor(Math.random() * 15),
      };

      setLightStates(mockLights);
      setClimateState(mockClimate);
      setIsLoading(false);
      setError(null);
    } catch (err) {
      setError('Failed to connect to Home Assistant');
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStates();
    const interval = setInterval(fetchStates, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, [fetchStates]);

  // Activate a scene
  const activateScene = async (sceneKey: SceneKey) => {
    const scene = SCENES[sceneKey];
    setIsActivating(scene.id);
    try {
      // In production: POST to HA API
      // await fetch(`${HA_URL}/api/services/scene/turn_on`, {
      //   method: 'POST',
      //   headers: { Authorization: `Bearer ${HA_TOKEN}`, 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ entity_id: scene.id }),
      // });
      await new Promise((resolve) => setTimeout(resolve, 500));
      setActiveScene(sceneKey);
      fetchStates();
    } catch (err) {
      setError(`Failed to activate scene: ${scene.name}`);
    } finally {
      setIsActivating(null);
    }
  };

  // Toggle a light group
  const toggleLight = async (lightKey: LightGroupKey) => {
    const light = LIGHT_GROUPS[lightKey];
    const currentState = lightStates[light.id];
    setIsActivating(light.id);
    try {
      // In production: POST to HA API
      await new Promise((resolve) => setTimeout(resolve, 300));
      setLightStates((prev) => ({
        ...prev,
        [light.id]: {
          ...prev[light.id],
          state: currentState?.state === 'on' ? 'off' : 'on',
        },
      }));
    } catch (err) {
      setError(`Failed to toggle: ${light.name}`);
    } finally {
      setIsActivating(null);
    }
  };

  // Adjust thermostat
  const adjustTemp = async (delta: number) => {
    if (!climateState) return;
    const newTarget = climateState.targetTemp + delta;
    setIsActivating(CLIMATE.main.id);
    try {
      await new Promise((resolve) => setTimeout(resolve, 300));
      setClimateState((prev) =>
        prev ? { ...prev, targetTemp: newTarget } : null
      );
    } catch (err) {
      setError('Failed to adjust temperature');
    } finally {
      setIsActivating(null);
    }
  };

  // Count lights that are on
  const lightsOnCount = Object.values(lightStates).filter(
    (l) => l.state === 'on'
  ).length;

  if (compact) {
    return (
      <div className="home-control-compact flex items-center gap-3">
        {/* Quick scene buttons */}
        {showScenes && (
          <div className="flex gap-1">
            {Object.entries(SCENES)
              .slice(0, 3)
              .map(([key, scene]) => (
                <button
                  key={key}
                  onClick={() => activateScene(key as SceneKey)}
                  disabled={isActivating === scene.id}
                  className="px-2 py-1 rounded text-sm transition-all hover:scale-105"
                  style={{
                    backgroundColor:
                      activeScene === key
                        ? 'rgba(34, 197, 94, 0.2)'
                        : 'rgba(107, 114, 128, 0.1)',
                    border: '1px solid',
                    borderColor:
                      activeScene === key
                        ? 'var(--hydra-green)'
                        : 'var(--hydra-border)',
                  }}
                  title={scene.description}
                >
                  {scene.icon}
                </button>
              ))}
          </div>
        )}

        {/* Quick light toggle */}
        {showLights && (
          <button
            onClick={() => toggleLight('all')}
            className="flex items-center gap-1 px-2 py-1 rounded text-xs"
            style={{
              backgroundColor:
                lightsOnCount > 0
                  ? 'rgba(234, 179, 8, 0.2)'
                  : 'rgba(107, 114, 128, 0.1)',
              border: '1px solid',
              borderColor:
                lightsOnCount > 0 ? 'var(--hydra-yellow)' : 'var(--hydra-border)',
              color: lightsOnCount > 0 ? 'var(--hydra-yellow)' : 'var(--hydra-text-muted)',
            }}
          >
            <span>💡</span>
            <span>{lightsOnCount} on</span>
          </button>
        )}

        {/* Temperature */}
        {showClimate && climateState && (
          <div
            className="flex items-center gap-1 px-2 py-1 rounded text-xs"
            style={{
              backgroundColor: 'rgba(107, 114, 128, 0.1)',
              border: '1px solid var(--hydra-border)',
              color: 'var(--hydra-text)',
            }}
          >
            <span>🌡️</span>
            <span>{climateState.currentTemp}°F</span>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="home-control-widget flex flex-col" style={{ height }}>
      {showHeader && (
        <div
          className="flex items-center justify-between px-3 py-2 border-b"
          style={{ borderColor: 'var(--hydra-border)' }}
        >
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium" style={{ color: 'var(--hydra-text)' }}>
              Home Control
            </span>
            <span
              className="text-xs px-1.5 py-0.5 rounded"
              style={{
                backgroundColor: 'rgba(234, 179, 8, 0.1)',
                color: 'var(--hydra-yellow)',
              }}
            >
              {lightsOnCount} lights on
            </span>
          </div>
          <a
            href={HA_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-2 py-1 rounded transition-colors hover:bg-white/10"
            style={{ color: 'var(--hydra-cyan)' }}
          >
            Open HA →
          </a>
        </div>
      )}

      <div className="flex-1 overflow-auto p-3 space-y-4">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div
              className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin"
              style={{ borderColor: 'var(--hydra-cyan)', borderTopColor: 'transparent' }}
            />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-full gap-2">
            <span style={{ color: 'var(--hydra-red)' }}>⚠️ {error}</span>
            <button
              onClick={fetchStates}
              className="text-xs px-2 py-1 rounded"
              style={{ backgroundColor: 'var(--hydra-cyan)', color: 'var(--hydra-bg)' }}
            >
              Retry
            </button>
          </div>
        ) : (
          <>
            {/* Scenes */}
            {showScenes && (
              <div>
                <div
                  className="text-xs font-medium mb-2"
                  style={{ color: 'var(--hydra-text-muted)' }}
                >
                  Scenes
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {Object.entries(SCENES).map(([key, scene]) => (
                    <button
                      key={key}
                      onClick={() => activateScene(key as SceneKey)}
                      disabled={isActivating === scene.id}
                      className="flex flex-col items-center gap-1 p-2 rounded border transition-all hover:scale-105"
                      style={{
                        backgroundColor:
                          activeScene === key
                            ? 'rgba(34, 197, 94, 0.1)'
                            : 'var(--hydra-bg)',
                        borderColor:
                          activeScene === key
                            ? 'var(--hydra-green)'
                            : 'var(--hydra-border)',
                      }}
                    >
                      <span className="text-xl">{scene.icon}</span>
                      <span
                        className="text-xs truncate w-full text-center"
                        style={{ color: 'var(--hydra-text)' }}
                      >
                        {scene.name}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Lights */}
            {showLights && (
              <div>
                <div
                  className="text-xs font-medium mb-2"
                  style={{ color: 'var(--hydra-text-muted)' }}
                >
                  Lights
                </div>
                <div className="grid grid-cols-5 gap-2">
                  {Object.entries(LIGHT_GROUPS).map(([key, light]) => {
                    const state = lightStates[light.id];
                    const isOn = state?.state === 'on';
                    return (
                      <button
                        key={key}
                        onClick={() => toggleLight(key as LightGroupKey)}
                        disabled={isActivating === light.id}
                        className="flex flex-col items-center gap-1 p-2 rounded border transition-all hover:scale-105"
                        style={{
                          backgroundColor: isOn
                            ? 'rgba(234, 179, 8, 0.15)'
                            : 'var(--hydra-bg)',
                          borderColor: isOn
                            ? 'var(--hydra-yellow)'
                            : 'var(--hydra-border)',
                        }}
                      >
                        <span className="text-lg">{light.icon}</span>
                        <span
                          className="text-xs truncate w-full text-center"
                          style={{
                            color: isOn ? 'var(--hydra-yellow)' : 'var(--hydra-text-muted)',
                          }}
                        >
                          {light.name}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Climate */}
            {showClimate && climateState && (
              <div>
                <div
                  className="text-xs font-medium mb-2"
                  style={{ color: 'var(--hydra-text-muted)' }}
                >
                  Climate
                </div>
                <div
                  className="flex items-center justify-between p-3 rounded border"
                  style={{
                    backgroundColor: 'var(--hydra-bg)',
                    borderColor: 'var(--hydra-border)',
                  }}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">🌡️</span>
                    <div>
                      <div className="flex items-baseline gap-2">
                        <span
                          className="text-2xl font-bold"
                          style={{ color: 'var(--hydra-text)' }}
                        >
                          {climateState.currentTemp}°
                        </span>
                        <span
                          className="text-sm"
                          style={{ color: 'var(--hydra-text-muted)' }}
                        >
                          → {climateState.targetTemp}°
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-xs">
                        <span
                          className="px-1.5 py-0.5 rounded capitalize"
                          style={{
                            backgroundColor:
                              climateState.state === 'heat'
                                ? 'rgba(239, 68, 68, 0.2)'
                                : climateState.state === 'cool'
                                ? 'rgba(59, 130, 246, 0.2)'
                                : 'rgba(107, 114, 128, 0.2)',
                            color:
                              climateState.state === 'heat'
                                ? 'var(--hydra-red)'
                                : climateState.state === 'cool'
                                ? 'var(--hydra-cyan)'
                                : 'var(--hydra-text-muted)',
                          }}
                        >
                          {climateState.state}
                        </span>
                        {climateState.humidity && (
                          <span style={{ color: 'var(--hydra-text-muted)' }}>
                            💧 {climateState.humidity}%
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex flex-col gap-1">
                    <button
                      onClick={() => adjustTemp(1)}
                      disabled={isActivating === CLIMATE.main.id}
                      className="w-8 h-8 rounded flex items-center justify-center transition-colors hover:bg-white/10"
                      style={{
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        border: '1px solid var(--hydra-border)',
                        color: 'var(--hydra-red)',
                      }}
                    >
                      ▲
                    </button>
                    <button
                      onClick={() => adjustTemp(-1)}
                      disabled={isActivating === CLIMATE.main.id}
                      className="w-8 h-8 rounded flex items-center justify-center transition-colors hover:bg-white/10"
                      style={{
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        border: '1px solid var(--hydra-border)',
                        color: 'var(--hydra-cyan)',
                      }}
                    >
                      ▼
                    </button>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// Quick scene activation button
interface SceneButtonProps {
  scene: SceneKey;
  showLabel?: boolean;
}

export function SceneButton({ scene, showLabel = true }: SceneButtonProps) {
  const [isActivating, setIsActivating] = useState(false);
  const config = SCENES[scene];

  const activate = async () => {
    setIsActivating(true);
    try {
      await new Promise((resolve) => setTimeout(resolve, 500));
    } finally {
      setIsActivating(false);
    }
  };

  return (
    <button
      onClick={activate}
      disabled={isActivating}
      className="flex items-center gap-1.5 px-2 py-1 rounded text-xs transition-all hover:scale-105 disabled:opacity-50"
      style={{
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
        border: '1px solid var(--hydra-green)',
        color: 'var(--hydra-green)',
      }}
      title={config.description}
    >
      <span>{config.icon}</span>
      {showLabel && <span>{config.name}</span>}
    </button>
  );
}
