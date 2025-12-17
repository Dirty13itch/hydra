import React, { useState } from 'react';
import { Card, Badge, ProgressBar, StatusDot, Tabs, Button } from '../components/UIComponents';
import { MOCK_NODES, MOCK_SERVICES } from '../constants';
import { Server, Activity, HardDrive, RefreshCw, Power } from 'lucide-react';

export const Infra: React.FC = () => {
  const [activeTab, setActiveTab] = useState('NODES');
  const tabs = [
    { id: 'NODES', label: 'Nodes & Resources' },
    { id: 'SERVICES', label: 'Services & Containers' },
    { id: 'LOGS', label: 'Cluster Logs' }
  ];

  return (
    <div className="flex flex-col h-full">
       <div className="px-6 pt-6 pb-2 flex justify-between items-end border-b border-neutral-800">
         <div>
            <h2 className="text-2xl font-mono font-bold text-neutral-200">INFRASTRUCTURE</h2>
            <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} className="mt-4" />
         </div>
         <div className="pb-2 flex gap-2">
           <Button variant="secondary" size="sm" icon={<RefreshCw size={14} />}>Refresh</Button>
         </div>
       </div>

       <div className="p-6 overflow-y-auto flex-1">
         
         {/* NODES TAB */}
         {activeTab === 'NODES' && (
           <div className="space-y-6">
             {MOCK_NODES.map(node => (
               <Card key={node.id} className="border-neutral-800">
                 {/* Node Header */}
                 <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 border-b border-neutral-800 pb-4">
                   <div className="flex items-center gap-4">
                      <div className="p-3 bg-neutral-800 rounded-lg text-neutral-400">
                        <Server size={24} />
                      </div>
                      <div>
                        <div className="flex items-center gap-3">
                           <h3 className="text-lg font-bold font-mono text-neutral-200">{node.name}</h3>
                           <Badge variant={node.status === 'online' ? 'emerald' : 'neutral'}>{node.status.toUpperCase()}</Badge>
                        </div>
                        <p className="text-sm text-neutral-500 font-mono">{node.ip} • Uptime: {node.uptime}</p>
                      </div>
                   </div>
                   <div className="flex gap-2">
                      <Button variant="secondary" size="sm" icon={<Power size={14} />}>Actions</Button>
                   </div>
                 </div>

                 {/* Resources Grid */}
                 <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                   
                   {/* CPU & RAM */}
                   <div className="space-y-4">
                      <h4 className="text-xs font-mono text-neutral-500 uppercase">Compute Resources</h4>
                      
                      <div className="space-y-1">
                        <div className="flex justify-between text-xs">
                           <span>CPU Load</span>
                           <span className={node.cpu > 80 ? 'text-red-400' : 'text-emerald-400'}>{node.cpu}%</span>
                        </div>
                        <ProgressBar value={node.cpu} colorClass={node.cpu > 80 ? 'bg-red-500' : 'bg-emerald-500'} />
                      </div>

                      <div className="space-y-1">
                        <div className="flex justify-between text-xs">
                           <span>RAM ({node.ram.used} / {node.ram.total} GB)</span>
                           <span className={(node.ram.used/node.ram.total) > 0.8 ? 'text-amber-400' : 'text-cyan-400'}>
                             {Math.round((node.ram.used / node.ram.total) * 100)}%
                           </span>
                        </div>
                        <ProgressBar 
                          value={(node.ram.used / node.ram.total) * 100} 
                          colorClass={(node.ram.used/node.ram.total) > 0.8 ? 'bg-amber-500' : 'bg-cyan-500'} 
                        />
                      </div>
                   </div>

                   {/* GPU Grid */}
                   <div className="lg:col-span-2 space-y-4">
                      <h4 className="text-xs font-mono text-neutral-500 uppercase">GPU Acceleration</h4>
                      {node.gpus.length === 0 && <p className="text-sm text-neutral-600 italic">No GPUs detected on this node.</p>}
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {node.gpus.map((gpu, idx) => (
                          <div key={idx} className="bg-neutral-900/50 rounded p-3 border border-neutral-800">
                             <div className="flex justify-between items-center mb-2">
                               <span className="font-semibold text-sm text-neutral-300">{gpu.name}</span>
                               <span className="text-xs font-mono text-neutral-500">{gpu.temp}°C • {gpu.power}W</span>
                             </div>
                             
                             <div className="space-y-3">
                               <div className="space-y-1">
                                  <div className="flex justify-between text-[10px] text-neutral-500 uppercase">
                                     <span>Core Load</span>
                                     <span>{gpu.util}%</span>
                                  </div>
                                  <div className="h-1 w-full bg-neutral-800 rounded-full overflow-hidden">
                                     <div className="h-full bg-purple-500" style={{ width: `${gpu.util}%` }} />
                                  </div>
                               </div>

                               <div className="space-y-1">
                                  <div className="flex justify-between text-[10px] text-neutral-500 uppercase">
                                     <span>VRAM ({gpu.vram}/{gpu.totalVram}GB)</span>
                                     <span>{Math.round((gpu.vram/gpu.totalVram)*100)}%</span>
                                  </div>
                                  <div className="h-1 w-full bg-neutral-800 rounded-full overflow-hidden">
                                     <div className="h-full bg-amber-500" style={{ width: `${(gpu.vram/gpu.totalVram)*100}%` }} />
                                  </div>
                               </div>
                             </div>
                          </div>
                        ))}
                      </div>
                   </div>

                 </div>
               </Card>
             ))}
           </div>
         )}

         {/* SERVICES TAB */}
         {activeTab === 'SERVICES' && (
           <Card className="border-neutral-800">
             <table className="w-full text-left border-collapse">
               <thead>
                 <tr className="text-xs font-mono text-neutral-500 border-b border-neutral-800">
                   <th className="p-3 font-medium">STATUS</th>
                   <th className="p-3 font-medium">SERVICE NAME</th>
                   <th className="p-3 font-medium">NODE</th>
                   <th className="p-3 font-medium">PORT</th>
                   <th className="p-3 font-medium">UPTIME</th>
                   <th className="p-3 font-medium text-right">ACTIONS</th>
                 </tr>
               </thead>
               <tbody className="text-sm">
                 {MOCK_SERVICES.map(svc => (
                   <tr key={svc.id} className="border-b border-neutral-800/50 hover:bg-neutral-800/30 transition-colors">
                     <td className="p-3">
                        <StatusDot status={svc.status} />
                     </td>
                     <td className="p-3 font-medium text-neutral-300">{svc.name}</td>
                     <td className="p-3 text-neutral-400">{svc.node}</td>
                     <td className="p-3 font-mono text-neutral-500">:{svc.port}</td>
                     <td className="p-3 text-neutral-400">{svc.uptime}</td>
                     <td className="p-3 text-right">
                       <button className="text-neutral-500 hover:text-white">•••</button>
                     </td>
                   </tr>
                 ))}
               </tbody>
             </table>
           </Card>
         )}

       </div>
    </div>
  );
};
