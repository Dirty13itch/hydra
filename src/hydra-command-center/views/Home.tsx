import React, { useState, useEffect, useCallback } from 'react';
import { Card, Button, Tabs, Badge } from '../components/UIComponents';
import { Lightbulb, Thermometer, Lock, Wifi, Sun, Moon, Film, Power, RefreshCw, Loader2, WifiOff, Home as HomeIcon, Droplets } from 'lucide-react';
import {
  getHomeStatus,
  getHomeRooms,
  getHomeDevices,
  getHomeScenes,
  controlRoomLights,
  activateScene,
  Room,
  HomeDevice,
  HomeScene,
} from '../services/hydraApi';
import { useNotifications } from '../context/NotificationContext';

export const Home: React.FC = () => {
  const [activeTab, setActiveTab] = useState('ROOMS');
  const [rooms, setRooms] = useState<Room[]>([]);
  const [devices, setDevices] = useState<HomeDevice[]>([]);
  const [scenes, setScenes] = useState<HomeScene[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isControlling, setIsControlling] = useState<string | null>(null);
  const { addNotification } = useNotifications();

  const tabs = [
    { id: 'ROOMS', label: 'Rooms' },
    { id: 'DEVICES', label: 'Devices' },
    { id: 'SCENES', label: 'Scenes' }
  ];

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      // Fetch status, rooms, devices, and scenes in parallel
      const [statusResult, roomsResult, devicesResult, scenesResult] = await Promise.all([
        getHomeStatus(),
        getHomeRooms(),
        getHomeDevices(),
        getHomeScenes(),
      ]);

      setIsConnected(statusResult.data?.connected ?? false);

      if (roomsResult.data?.rooms) {
        setRooms(roomsResult.data.rooms);
      }

      if (devicesResult.data?.devices) {
        setDevices(devicesResult.data.devices);
      }

      if (scenesResult.data?.scenes) {
        setScenes(scenesResult.data.scenes);
      }
    } catch (err) {
      console.error('Failed to fetch home data:', err);
      addNotification('error', 'Connection Error', 'Failed to connect to Home Assistant');
    } finally {
      setIsLoading(false);
    }
  }, [addNotification]);

  useEffect(() => {
    fetchData();
    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleToggleRoomLights = async (roomId: string, currentState: boolean) => {
    setIsControlling(roomId);
    try {
      const action = currentState ? 'off' : 'on';
      const result = await controlRoomLights(roomId, action);

      if (result.data) {
        // Update local state optimistically
        setRooms(prev => prev.map(room =>
          room.id === roomId ? { ...room, lights_on: !currentState, active: !currentState } : room
        ));
        addNotification('success', 'Lights Controlled', `${roomId.replace('_', ' ')} lights turned ${action}`);
      }
    } catch (err) {
      addNotification('error', 'Control Failed', 'Failed to control room lights');
    } finally {
      setIsControlling(null);
    }
  };

  const handleActivateScene = async (scene: HomeScene) => {
    setIsControlling(scene.id);
    try {
      const result = await activateScene(scene.entity_id);
      if (result.data?.success) {
        addNotification('success', 'Scene Activated', `${scene.name} scene activated`);
        // Refresh room states after scene activation
        setTimeout(fetchData, 1000);
      }
    } catch (err) {
      addNotification('error', 'Scene Failed', 'Failed to activate scene');
    } finally {
      setIsControlling(null);
    }
  };

  const getRoomIcon = (roomName: string) => {
    const name = roomName.toLowerCase();
    if (name.includes('living')) return <Film size={20} />;
    if (name.includes('kitchen')) return <Wifi size={20} />;
    if (name.includes('bedroom')) return <Moon size={20} />;
    if (name.includes('office')) return <Power size={20} />;
    if (name.includes('bathroom')) return <Droplets size={20} />;
    return <Lightbulb size={20} />;
  };

  const getSceneIcon = (sceneName: string) => {
    const name = sceneName.toLowerCase();
    if (name.includes('morning') || name.includes('rise')) return <Sun size={24} />;
    if (name.includes('night') || name.includes('evening')) return <Moon size={24} />;
    if (name.includes('movie') || name.includes('cinema')) return <Film size={24} />;
    if (name.includes('lock') || name.includes('away')) return <Lock size={24} />;
    return <HomeIcon size={24} />;
  };

  const getSceneColor = (sceneName: string) => {
    const name = sceneName.toLowerCase();
    if (name.includes('morning') || name.includes('rise')) return { text: 'text-amber-400', border: 'hover:border-amber-500' };
    if (name.includes('night') || name.includes('evening')) return { text: 'text-purple-400', border: 'hover:border-purple-500' };
    if (name.includes('movie') || name.includes('cinema')) return { text: 'text-red-400', border: 'hover:border-red-500' };
    if (name.includes('lock') || name.includes('away')) return { text: 'text-emerald-400', border: 'hover:border-emerald-500' };
    return { text: 'text-cyan-400', border: 'hover:border-cyan-500' };
  };

  return (
    <div className="flex flex-col h-full bg-surface-base">
      <div className="px-6 pt-6 pb-2 border-b border-neutral-800 flex justify-between items-end">
        <div>
          <h2 className="text-2xl font-mono font-bold text-neutral-200 flex items-center gap-2">
            <span className="text-amber-500">HOME_CONTROL</span>
          </h2>
          <Tabs
            tabs={tabs}
            activeTab={activeTab}
            onChange={setActiveTab}
            className="mt-4"
            variant="emerald"
          />
        </div>
        <div className="pb-2 flex items-center gap-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={fetchData}
            icon={isLoading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
          >
            Refresh
          </Button>
          <Badge variant={isConnected ? 'emerald' : 'red'}>
            {isConnected ? (
              <>
                <Wifi size={12} className="mr-1" />
                HA ONLINE
              </>
            ) : (
              <>
                <WifiOff size={12} className="mr-1" />
                HA OFFLINE
              </>
            )}
          </Badge>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">

        {activeTab === 'ROOMS' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {isLoading && rooms.length === 0 ? (
              <div className="col-span-full flex items-center justify-center py-12 text-neutral-500">
                <Loader2 className="animate-spin mr-2" />
                Loading rooms...
              </div>
            ) : rooms.length === 0 ? (
              <div className="col-span-full flex flex-col items-center justify-center py-12 text-neutral-500">
                <HomeIcon size={48} className="mb-4 opacity-50" />
                <p>No rooms found</p>
                <p className="text-sm text-neutral-600">Configure rooms in Home Assistant</p>
              </div>
            ) : (
              rooms.map(room => (
                <Card key={room.id} className={`group transition-all ${room.active ? 'border-amber-500/40 bg-surface-default' : 'border-neutral-800 bg-surface-dim'}`}>
                  <div className="flex justify-between items-start mb-4">
                    <div className="p-3 rounded-full bg-neutral-800 text-neutral-400 group-hover:text-amber-400 transition-colors">
                      {getRoomIcon(room.name)}
                    </div>
                    <div className="text-right">
                      <p className="text-xl font-mono font-bold text-neutral-200">
                        {room.temp !== null ? `${room.temp}°` : '--°'}
                      </p>
                      <p className="text-[10px] text-neutral-500 font-mono uppercase">Temperature</p>
                    </div>
                  </div>

                  <h3 className="text-lg font-bold text-neutral-200 mb-4">{room.name}</h3>

                  <div className="space-y-4">
                    <div className="flex justify-between items-center text-sm p-3 bg-neutral-900/50 rounded-lg border border-neutral-800">
                      <div className="flex items-center gap-2 text-neutral-400">
                        <Lightbulb size={16} />
                        <span>Lights</span>
                      </div>
                      <button
                        onClick={() => handleToggleRoomLights(room.id, room.lights_on)}
                        disabled={isControlling === room.id}
                        className={`w-10 h-5 rounded-full relative transition-colors ${room.lights_on ? 'bg-amber-500' : 'bg-neutral-700'} ${isControlling === room.id ? 'opacity-50' : ''}`}
                      >
                        {isControlling === room.id ? (
                          <div className="absolute inset-0 flex items-center justify-center">
                            <Loader2 size={12} className="animate-spin text-white" />
                          </div>
                        ) : (
                          <div className={`absolute top-1 w-3 h-3 rounded-full bg-white transition-all ${room.lights_on ? 'left-6' : 'left-1'}`} />
                        )}
                      </button>
                    </div>

                    <div className="flex justify-between text-xs text-neutral-500 font-mono px-1">
                      <span>{room.devices} Devices</span>
                      <span className="flex items-center gap-1">
                        <Wifi size={10} />
                        {room.active ? 'Active' : 'Idle'}
                      </span>
                    </div>
                  </div>
                </Card>
              ))
            )}
          </div>
        )}

        {activeTab === 'DEVICES' && (
          <div className="space-y-4">
            {isLoading && devices.length === 0 ? (
              <div className="flex items-center justify-center py-12 text-neutral-500">
                <Loader2 className="animate-spin mr-2" />
                Loading devices...
              </div>
            ) : devices.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-neutral-500">
                <Power size={48} className="mb-4 opacity-50" />
                <p>No controllable devices found</p>
                <p className="text-sm text-neutral-600">Devices will appear here when Home Assistant is configured</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {devices.map(device => (
                  <Card key={device.id} className="hover:border-cyan-500/30 transition-colors">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${device.state === 'on' ? 'bg-amber-500/10 text-amber-500' : 'bg-neutral-800 text-neutral-500'}`}>
                          {device.device_type === 'light' && <Lightbulb size={18} />}
                          {device.device_type === 'switch' && <Power size={18} />}
                          {device.device_type === 'climate' && <Thermometer size={18} />}
                          {device.device_type === 'lock' && <Lock size={18} />}
                          {!['light', 'switch', 'climate', 'lock'].includes(device.device_type) && <Wifi size={18} />}
                        </div>
                        <div>
                          <h4 className="font-medium text-neutral-200">{device.name}</h4>
                          <p className="text-xs text-neutral-500 font-mono">{device.device_type}</p>
                        </div>
                      </div>
                      <Badge variant={device.state === 'on' ? 'emerald' : 'neutral'}>
                        {device.state}
                      </Badge>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'SCENES' && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {isLoading && scenes.length === 0 ? (
              <div className="col-span-full flex items-center justify-center py-12 text-neutral-500">
                <Loader2 className="animate-spin mr-2" />
                Loading scenes...
              </div>
            ) : scenes.length === 0 ? (
              <div className="col-span-full flex flex-col items-center justify-center py-12 text-neutral-500">
                <Film size={48} className="mb-4 opacity-50" />
                <p>No scenes configured</p>
                <p className="text-sm text-neutral-600">Create scenes in Home Assistant</p>
              </div>
            ) : (
              scenes.map(scene => {
                const colors = getSceneColor(scene.name);
                return (
                  <button
                    key={scene.id}
                    onClick={() => handleActivateScene(scene)}
                    disabled={isControlling === scene.id}
                    className={`p-6 bg-surface-default border border-neutral-800 rounded-xl flex flex-col items-center justify-center gap-4 transition-all hover:bg-surface-raised ${colors.border} group disabled:opacity-50`}
                  >
                    <div className={`p-4 bg-neutral-900 rounded-full ${colors.text} group-hover:scale-110 transition-transform`}>
                      {isControlling === scene.id ? (
                        <Loader2 size={24} className="animate-spin" />
                      ) : (
                        getSceneIcon(scene.name)
                      )}
                    </div>
                    <span className="font-mono font-bold text-neutral-300">{scene.name}</span>
                  </button>
                );
              })
            )}
          </div>
        )}

      </div>
    </div>
  );
};
