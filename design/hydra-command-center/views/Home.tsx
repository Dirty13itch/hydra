import React, { useState } from 'react';
import { Card, Button, Tabs, Badge } from '../components/UIComponents';
import { Lightbulb, Thermometer, Lock, Wifi, Sun, Moon, Film, Power } from 'lucide-react';

interface Room {
  id: string;
  name: string;
  temp: number;
  devices: number;
  lights: boolean;
  active: boolean;
}

const MOCK_ROOMS: Room[] = [
  { id: '1', name: 'Living Room', temp: 72, devices: 4, lights: true, active: true },
  { id: '2', name: 'Office', temp: 70, devices: 2, lights: true, active: true },
  { id: '3', name: 'Bedroom', temp: 68, devices: 3, lights: false, active: false },
  { id: '4', name: 'Kitchen', temp: 71, devices: 5, lights: true, active: true },
  { id: '5', name: 'Entryway', temp: 69, devices: 1, lights: false, active: false },
];

export const Home: React.FC = () => {
  const [activeTab, setActiveTab] = useState('ROOMS');
  const [rooms, setRooms] = useState(MOCK_ROOMS);

  const tabs = [
    { id: 'ROOMS', label: 'Rooms' },
    { id: 'DEVICES', label: 'Devices' },
    { id: 'SCENES', label: 'Scenes' }
  ];

  const toggleRoomLights = (id: string) => {
    setRooms(prev => prev.map(room => 
      room.id === id ? { ...room, lights: !room.lights, active: !room.lights } : room
    ));
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
        <div className="pb-2">
           <Badge variant="amber">HA ONLINE</Badge>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        
        {activeTab === 'ROOMS' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {rooms.map(room => (
              <Card key={room.id} className={`group transition-all ${room.active ? 'border-amber-500/40 bg-surface-default' : 'border-neutral-800 bg-surface-dim'}`}>
                <div className="flex justify-between items-start mb-4">
                   <div className="p-3 rounded-full bg-neutral-800 text-neutral-400 group-hover:text-amber-400 transition-colors">
                     {room.name.includes('Living') ? <Film size={20} /> : 
                      room.name.includes('Kitchen') ? <Wifi size={20} /> :
                      room.name.includes('Bedroom') ? <Moon size={20} /> : 
                      <Lightbulb size={20} />}
                   </div>
                   <div className="text-right">
                     <p className="text-xl font-mono font-bold text-neutral-200">{room.temp}°</p>
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
                      onClick={() => toggleRoomLights(room.id)}
                      className={`w-10 h-5 rounded-full relative transition-colors ${room.lights ? 'bg-amber-500' : 'bg-neutral-700'}`}
                    >
                      <div className={`absolute top-1 w-3 h-3 rounded-full bg-white transition-all ${room.lights ? 'left-6' : 'left-1'}`} />
                    </button>
                  </div>
                  
                  <div className="flex justify-between text-xs text-neutral-500 font-mono px-1">
                     <span>{room.devices} Devices</span>
                     <span className="flex items-center gap-1"><Wifi size={10} /> Online</span>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

        {activeTab === 'SCENES' && (
           <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { name: 'Morning Rise', icon: <Sun size={24} />, color: 'text-amber-400', border: 'hover:border-amber-500' },
                { name: 'Night Mode', icon: <Moon size={24} />, color: 'text-purple-400', border: 'hover:border-purple-500' },
                { name: 'Movie Time', icon: <Film size={24} />, color: 'text-red-400', border: 'hover:border-red-500' },
                { name: 'Lockdown', icon: <Lock size={24} />, color: 'text-emerald-400', border: 'hover:border-emerald-500' },
              ].map(scene => (
                <button key={scene.name} className={`p-6 bg-surface-default border border-neutral-800 rounded-xl flex flex-col items-center justify-center gap-4 transition-all hover:bg-surface-raised ${scene.border} group`}>
                   <div className={`p-4 bg-neutral-900 rounded-full ${scene.color} group-hover:scale-110 transition-transform`}>
                     {scene.icon}
                   </div>
                   <span className="font-mono font-bold text-neutral-300">{scene.name}</span>
                </button>
              ))}
           </div>
        )}

      </div>
    </div>
  );
};
