import React, { useState, useEffect, useRef } from 'react';
import { Card, StatusDot, ProgressBar, Badge, Button, Tabs } from '../components/UIComponents';
import { Pause, Play, XCircle, Plus, ChevronLeft, Terminal, Activity, FileText, Eye, EyeOff, Sliders, Cpu, Link, Code, Settings, Save, RotateCcw, History, Trash2, CheckCircle, Network, Power, Search } from 'lucide-react';
import { Agent, LogEntry, AgentConfig } from '../types';
import { useAgentWatch } from '../context/AgentWatchContext';
import { useAgents } from '../context/AgentContext';

export const Agents: React.FC = () => {
  const { agents, updateAgentStatus, stopAgent } = useAgents();
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);

  const toggleAgentStatus = (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    const agent = agents.find(a => a.id === id);
    if (!agent) return;
    
    const isPausing = agent.status === 'active' || agent.status === 'thinking';
    updateAgentStatus(id, isPausing ? 'paused' : 'active');
  };

  const handleStopAgent = (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (confirm('Are you sure you want to stop this agent? Process context will be lost.')) {
      stopAgent(id);
    }
  };

  const selectedAgent = agents.find(a => a.id === selectedAgentId);

  return (
    <div className="h-full flex flex-col">
      {selectedAgent ? (
        <AgentDetail 
          agent={selectedAgent} 
          onBack={() => setSelectedAgentId(null)} 
          onToggleStatus={(id) => toggleAgentStatus(id)}
          onStop={(id) => handleStopAgent(id)}
        />
      ) : (
        <div className="p-6 h-full overflow-y-auto">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h2 className="text-2xl font-mono font-bold text-neutral-200">AGENTS_OVERVIEW</h2>
              <p className="text-sm text-neutral-500 font-mono">Orchestrate autonomous neural workers</p>
            </div>
            <Button variant="primary" icon={<Plus size={16} />}>Spawn New Agent</Button>
          </div>

          <div className="space-y-4">
            {agents.map((agent) => (
              <Card 
                key={agent.id} 
                className="group hover:border-emerald-500/40 transition-all cursor-pointer"
                onClick={() => setSelectedAgentId(agent.id)}
              >
                <div className="flex flex-col md:flex-row md:items-center gap-4">
                  
                  {/* Agent Status/Icon */}
                  <div className="flex items-center gap-4 min-w-[200px]">
                    <div className={`h-12 w-12 rounded-lg flex items-center justify-center text-lg font-bold bg-neutral-800 transition-colors ${
                      agent.status === 'active' || agent.status === 'thinking' ? 'text-emerald-400 border border-emerald-500/30 shadow-glow-emerald' : 
                      agent.status === 'paused' ? 'text-amber-400 border border-amber-500/30' :
                      'text-neutral-500'
                    }`}>
                      {agent.name.charAt(0)}
                    </div>
                    <div>
                      <h3 className="font-bold text-neutral-200 group-hover:text-emerald-400 transition-colors">{agent.name}</h3>
                      <div className="flex items-center gap-2 mt-1">
                        <StatusDot status={agent.status} />
                        <span className="text-xs text-neutral-500 uppercase font-mono">{agent.status}</span>
                      </div>
                    </div>
                  </div>

                  {/* Task Info */}
                  <div className="flex-1">
                    <p className="text-xs text-neutral-500 font-mono mb-1">CURRENT TASK</p>
                    <p className="text-sm text-neutral-300">{agent.task}</p>
                    <div className="mt-2 flex items-center gap-2">
                      <div className="flex-1 max-w-[200px]">
                        <ProgressBar 
                            value={agent.progress} 
                            colorClass={agent.status === 'paused' ? 'bg-amber-500' : 'bg-emerald-500'} 
                        />
                      </div>
                      <span className="text-xs font-mono text-neutral-500">{agent.progress}%</span>
                    </div>
                  </div>

                  {/* Model Info */}
                  <div className="min-w-[150px] hidden md:block">
                    <p className="text-xs text-neutral-500 font-mono mb-1">MODEL</p>
                    <Badge variant="purple">{agent.model}</Badge>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                    <Button 
                      variant="secondary" 
                      size="sm" 
                      className="!p-2" 
                      title={agent.status === 'paused' ? "Resume" : "Pause"}
                      onClick={(e) => toggleAgentStatus(agent.id, e)}
                    >
                      {agent.status === 'paused' ? <Play size={14} /> : <Pause size={14} />}
                    </Button>
                    <Button variant="danger" size="sm" className="!p-2" title="Stop Agent" onClick={(e) => handleStopAgent(agent.id, e)}><XCircle size={14} /></Button>
                  </div>

                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// --- Detail Component ---

interface AgentDetailProps {
  agent: Agent;
  onBack: () => void;
  onToggleStatus: (id: string) => void;
  onStop: (id: string) => void;
}

const AgentDetail: React.FC<AgentDetailProps> = ({ agent, onBack, onToggleStatus, onStop }) => {
  const [activeTab, setActiveTab] = useState('OVERVIEW');
  const [localLogs, setLocalLogs] = useState<LogEntry[]>([
    { id: '0', timestamp: new Date().toLocaleTimeString(), level: 'INFO', message: 'Session initialized.' },
    { id: '1', timestamp: new Date().toLocaleTimeString(), level: 'INFO', message: `Task started: ${agent.task}` },
  ]);
  const logEndRef = useRef<HTMLDivElement>(null);
  const { agents, updateAgentConfig } = useAgents();
  
  const { watchedAgentId, startWatching, stopWatching, streamLogs } = useAgentWatch();
  const isWatching = watchedAgentId === agent.id;

  // --- Configuration State ---
  const [isEditing, setIsEditing] = useState(false);
  const [configState, setConfigState] = useState<AgentConfig>(agent.config || {
    temperature: 0.7, topP: 0.9, topK: 40, maxOutputTokens: 2048, systemInstruction: ''
  });
  const [selectedModel, setSelectedModel] = useState(agent.model);
  const [editTools, setEditTools] = useState<string[]>(agent.tools || []);
  const [editDeps, setEditDeps] = useState<string[]>(agent.dependencies || []);
  
  // Adding State
  const [isAddingTool, setIsAddingTool] = useState(false);
  const [newToolName, setNewToolName] = useState('');
  const [isAddingDep, setIsAddingDep] = useState(false);
  const [newDepId, setNewDepId] = useState('');

  // Sync state when agent prop changes (if not editing)
  useEffect(() => {
     if (!isEditing) {
        if (agent.config) setConfigState(agent.config);
        setSelectedModel(agent.model);
        setEditTools(agent.tools || []);
        setEditDeps(agent.dependencies || []);
     }
  }, [agent, isEditing]);

  const handleSaveConfig = () => {
    // Generate history if prompt changed
    let updatedHistory = configState.promptHistory || [];
    if (configState.systemInstruction !== agent.config?.systemInstruction) {
       updatedHistory = [
         {
           version: (updatedHistory.length > 0 ? updatedHistory[0].version + 1 : 1),
           timestamp: new Date().toLocaleTimeString(),
           author: 'Previous State',
           content: agent.config?.systemInstruction || ''
         },
         ...updatedHistory
       ];
    }

    updateAgentConfig(agent.id, { 
       config: {
         ...configState,
         promptHistory: updatedHistory
       },
       model: selectedModel,
       tools: editTools,
       dependencies: editDeps
    });
    setIsEditing(false);
    setIsAddingTool(false);
    setIsAddingDep(false);
  };

  const handleRestorePrompt = (content: string) => {
    setConfigState(prev => ({ ...prev, systemInstruction: content }));
  };
  
  const handleAddTool = () => {
    if (newToolName && !editTools.includes(newToolName)) {
      setEditTools([...editTools, newToolName]);
      setNewToolName('');
      setIsAddingTool(false);
    }
  };

  const handleAddDep = () => {
    if (newDepId && !editDeps.includes(newDepId)) {
      setEditDeps([...editDeps, newDepId]);
      setNewDepId('');
      setIsAddingDep(false);
    }
  };

  const availableAgents = agents.filter(a => a.id !== agent.id && !editDeps.includes(a.id));

  // Use streamLogs if watching, otherwise localLogs
  const logs = isWatching ? streamLogs : localLogs;

  // Simulate thinking stream logs for local detail view
  useEffect(() => {
    // Skip local simulation if we are watching (global simulation takes over in context) or if inactive
    if ((agent.status !== 'active' && agent.status !== 'thinking') || isWatching) return;

    const phrases = agent.type === 'coding' 
      ? ['Analyzing abstract syntax tree...', 'Refactoring class hierarchy...', 'Running static analysis...', 'Resolving circular dependency...', 'Optimizing memory usage...'] 
      : ['Querying vector database...', 'Synthesizing search results...', 'Cross-referencing citations...', 'Generating summary statistics...', 'Validating hypothesis...'];

    const interval = setInterval(() => {
      const randomPhrase = phrases[Math.floor(Math.random() * phrases.length)];
      const newLog: LogEntry = {
        id: Date.now().toString(),
        timestamp: new Date().toLocaleTimeString(),
        level: 'DEBUG',
        message: randomPhrase
      };
      setLocalLogs(prev => [...prev.slice(-49), newLog]); // Keep last 50
    }, 2500);

    return () => clearInterval(interval);
  }, [agent.status, agent.type, isWatching]);

  // Auto-scroll logs
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const toggleWatch = () => {
    if (isWatching) {
      stopWatching();
    } else {
      startWatching(agent.id);
    }
  };

  const tabs = [
    { id: 'OVERVIEW', label: 'Thinking Stream' },
    { id: 'HISTORY', label: 'Action History' },
    { id: 'CONFIG', label: 'Configuration' }
  ];

  return (
    <div className="flex flex-col h-full bg-surface-base">
      {/* Header */}
      <div className="px-6 py-4 border-b border-neutral-800 flex items-center justify-between bg-surface-default">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="p-2 hover:bg-neutral-800 rounded-full text-neutral-400 hover:text-white transition-colors">
            <ChevronLeft size={20} />
          </button>
          <div>
            <h2 className="text-xl font-mono font-bold text-neutral-200 flex items-center gap-3">
              {agent.name}
              <StatusDot status={agent.status} />
              {isWatching && <div className="flex items-center gap-1 text-[10px] text-red-400 bg-red-900/20 px-2 py-0.5 rounded border border-red-900/50 animate-pulse"><Eye size={10} /> LIVE MONITOR</div>}
            </h2>
            <div className="flex items-center gap-2 text-xs text-neutral-500 font-mono mt-1">
              <Badge variant="neutral">{agent.type.toUpperCase()}</Badge>
              <span>ID: {agent.id}</span>
              <span>•</span>
              <span>Uptime: {agent.uptime}</span>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
           <Button 
             variant="secondary"
             className={isWatching ? "border-red-500 text-red-400 hover:bg-red-900/20" : ""}
             icon={isWatching ? <EyeOff size={16} /> : <Eye size={16} />}
             onClick={toggleWatch}
           >
             {isWatching ? 'Stop Watch' : 'Watch Mode'}
           </Button>
           <div className="w-px h-8 bg-neutral-800 mx-2" />
           <Button 
              variant="secondary" 
              icon={agent.status === 'paused' ? <Play size={16} /> : <Pause size={16} />}
              onClick={() => onToggleStatus(agent.id)}
           >
             {agent.status === 'paused' ? 'Resume' : 'Pause'}
           </Button>
           <Button variant="danger" icon={<XCircle size={16} />} onClick={() => onStop(agent.id)}>Stop</Button>
        </div>
      </div>

      {/* Detail Content */}
      <div className="flex-1 overflow-hidden flex flex-col p-6">
        
        {/* Only show top stats in Overview/History to save space in Config */}
        {activeTab !== 'CONFIG' && (
           <div className="mb-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
             <Card className="lg:col-span-2 border-neutral-800">
               <h3 className="text-sm font-mono text-neutral-500 mb-2 uppercase">Current Objective</h3>
               <p className="text-lg text-neutral-200 font-medium mb-4">{agent.task}</p>
               <div className="space-y-2">
                 <div className="flex justify-between text-xs text-neutral-500 font-mono">
                   <span>TASK COMPLETION</span>
                   <span>{agent.progress}%</span>
                 </div>
                 <ProgressBar value={agent.progress} colorClass="bg-emerald-500" />
               </div>
             </Card>
             <Card className="border-neutral-800">
               <h3 className="text-sm font-mono text-neutral-500 mb-4 uppercase">Resources</h3>
               <div className="space-y-4">
                 <div className="flex justify-between items-center">
                   <span className="text-sm text-neutral-300">Model</span>
                   <Badge variant="purple">{agent.model}</Badge>
                 </div>
                 <div className="flex justify-between items-center">
                   <span className="text-sm text-neutral-300">Context Usage</span>
                   <span className="text-sm font-mono text-cyan-400">12,405 / 32k</span>
                 </div>
               </div>
             </Card>
          </div>
        )}

        <div className="flex items-center justify-between mb-4">
           <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
           {activeTab === 'CONFIG' && (
              <div className="flex items-center gap-2">
                 {isEditing ? (
                    <>
                       <Button variant="ghost" size="sm" onClick={() => setIsEditing(false)}>Cancel</Button>
                       <Button variant="primary" size="sm" icon={<Save size={14} />} onClick={handleSaveConfig}>Save Changes</Button>
                    </>
                 ) : (
                    <Button variant="secondary" size="sm" icon={<Settings size={14} />} onClick={() => setIsEditing(true)}>Edit Config</Button>
                 )}
              </div>
           )}
        </div>

        <div className="flex-1 min-h-0 relative overflow-y-auto">
          {activeTab === 'OVERVIEW' && (
            <Card className="h-full border-neutral-800 flex flex-col bg-neutral-900/50 p-0 overflow-hidden">
               <div className="px-4 py-2 bg-surface-dim border-b border-neutral-800 flex justify-between items-center">
                 <div className="flex items-center gap-2 text-xs font-mono text-neutral-500">
                   <Terminal size={14} />
                   <span>THINKING_STREAM</span>
                 </div>
                 <div className="flex gap-2">
                   <div className="w-2 h-2 rounded-full bg-red-500" />
                   <div className="w-2 h-2 rounded-full bg-amber-500" />
                   <div className="w-2 h-2 rounded-full bg-emerald-500" />
                 </div>
               </div>
               <div className="flex-1 overflow-y-auto p-4 font-mono text-xs space-y-2">
                 {logs.map((log) => (
                   <div key={log.id} className="flex gap-3 text-neutral-300">
                     <span className="text-neutral-600 shrink-0">[{log.timestamp}]</span>
                     <span className={`shrink-0 w-12 ${
                       log.level === 'INFO' ? 'text-cyan-500' : 
                       log.level === 'WARN' ? 'text-amber-500' : 
                       log.level === 'ERROR' ? 'text-red-500' : 
                       'text-emerald-500'
                     }`}>{log.level}</span>
                     <span>{log.message}</span>
                   </div>
                 ))}
                 <div ref={logEndRef} />
                 {agent.status === 'active' && (
                   <div className="flex items-center gap-2 text-emerald-500/50 animate-pulse mt-2">
                     <span className="w-2 h-4 bg-emerald-500/50 block"></span>
                   </div>
                 )}
               </div>
            </Card>
          )}

          {activeTab === 'HISTORY' && (
             <div className="flex flex-col items-center justify-center h-full text-neutral-600 border border-dashed border-neutral-800 rounded-xl">
                <Activity size={32} className="mb-4" />
                <p>Action history log unavailable in simulation mode.</p>
             </div>
          )}
          
          {activeTab === 'CONFIG' && (
             <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pb-6 animate-slide-in">
                
                {/* Model Configuration */}
                <Card className={`border-neutral-800 transition-colors ${isEditing ? 'border-amber-500/30 bg-surface-raised' : ''}`}>
                   <div className="flex items-center gap-2 mb-4 text-cyan-400">
                      <Sliders size={18} />
                      <h3 className="text-sm font-bold font-mono uppercase">Model Parameters</h3>
                   </div>
                   
                   <div className="space-y-6">
                      {/* Model Selector */}
                      <div>
                         <label className="block text-xs font-mono text-neutral-500 uppercase mb-2">Base Model</label>
                         <div className="relative">
                            <select 
                               disabled={!isEditing}
                               value={selectedModel}
                               onChange={(e) => setSelectedModel(e.target.value)}
                               className="w-full bg-neutral-900 border border-neutral-700 rounded p-2 text-sm text-neutral-300 outline-none focus:border-cyan-500 appearance-none disabled:opacity-50"
                            >
                               <option value="gemini-2.5-flash">gemini-2.5-flash</option>
                               <option value="gemini-3-pro-preview">gemini-3-pro-preview</option>
                               <option value="gemini-3-pro-image-preview">gemini-3-pro-image-preview</option>
                            </select>
                            <Cpu size={14} className="absolute right-3 top-3 text-neutral-500 pointer-events-none" />
                         </div>
                      </div>

                      <div className="space-y-4">
                         {/* Temperature */}
                         <div className="space-y-2">
                            <div className="flex justify-between text-xs text-neutral-400 font-mono">
                               <span>Temperature</span>
                               <span>{configState.temperature}</span>
                            </div>
                            {isEditing ? (
                               <input 
                                  type="range" 
                                  min="0" max="2" step="0.1"
                                  value={configState.temperature}
                                  onChange={(e) => setConfigState({...configState, temperature: parseFloat(e.target.value)})}
                                  className="w-full accent-cyan-500 h-1.5 bg-neutral-800 rounded-lg appearance-none cursor-pointer"
                               />
                            ) : (
                               <ProgressBar value={(configState.temperature / 2) * 100} colorClass="bg-cyan-500" />
                            )}
                         </div>
                         
                         {/* Top P */}
                         <div className="space-y-2">
                            <div className="flex justify-between text-xs text-neutral-400 font-mono">
                               <span>Top P</span>
                               <span>{configState.topP}</span>
                            </div>
                            {isEditing ? (
                               <input 
                                  type="range" 
                                  min="0" max="1" step="0.05"
                                  value={configState.topP}
                                  onChange={(e) => setConfigState({...configState, topP: parseFloat(e.target.value)})}
                                  className="w-full accent-purple-500 h-1.5 bg-neutral-800 rounded-lg appearance-none cursor-pointer"
                               />
                            ) : (
                               <ProgressBar value={configState.topP * 100} colorClass="bg-purple-500" />
                            )}
                         </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                         <div className="bg-neutral-900/50 p-3 rounded border border-neutral-800">
                            <span className="text-[10px] text-neutral-500 font-mono uppercase block mb-1">Top K</span>
                            {isEditing ? (
                               <input 
                                  type="number" 
                                  value={configState.topK}
                                  onChange={(e) => setConfigState({...configState, topK: parseInt(e.target.value)})}
                                  className="bg-transparent border-b border-neutral-700 w-full text-sm font-mono focus:border-cyan-500 outline-none"
                               />
                            ) : (
                               <span className="text-lg font-mono text-neutral-200">{configState.topK}</span>
                            )}
                         </div>
                         <div className="bg-neutral-900/50 p-3 rounded border border-neutral-800">
                            <span className="text-[10px] text-neutral-500 font-mono uppercase block mb-1">Max Tokens</span>
                            {isEditing ? (
                               <input 
                                  type="number" 
                                  value={configState.maxOutputTokens}
                                  onChange={(e) => setConfigState({...configState, maxOutputTokens: parseInt(e.target.value)})}
                                  className="bg-transparent border-b border-neutral-700 w-full text-sm font-mono focus:border-cyan-500 outline-none"
                               />
                            ) : (
                               <span className="text-lg font-mono text-neutral-200">{configState.maxOutputTokens}</span>
                            )}
                         </div>
                      </div>
                   </div>
                </Card>

                {/* System Prompt & History */}
                <Card className={`lg:col-span-2 border-neutral-800 bg-neutral-900/30 flex flex-col md:flex-row gap-0 overflow-hidden ${isEditing ? 'border-amber-500/30' : ''}`}>
                   
                   {/* Main Editor */}
                   <div className="flex-1 p-4 flex flex-col gap-4">
                      <div className="flex items-center gap-2 text-amber-400">
                         <Code size={18} />
                         <h3 className="text-sm font-bold font-mono uppercase">System Instruction</h3>
                      </div>
                      
                      <textarea 
                         disabled={!isEditing}
                         value={configState.systemInstruction}
                         onChange={(e) => setConfigState({...configState, systemInstruction: e.target.value})}
                         className="flex-1 bg-neutral-950 p-4 rounded-lg border border-neutral-800 text-sm font-mono text-neutral-300 resize-none outline-none focus:border-amber-500/50 min-h-[200px]"
                         placeholder="Enter system prompts..."
                      />
                   </div>

                   {/* History Sidebar */}
                   <div className="w-full md:w-64 border-l border-neutral-800 bg-surface-dim flex flex-col">
                      <div className="p-3 border-b border-neutral-800 flex items-center gap-2 text-neutral-500">
                         <History size={14} />
                         <span className="text-xs font-mono uppercase">Version History</span>
                      </div>
                      <div className="flex-1 overflow-y-auto p-2 space-y-2 max-h-[300px] md:max-h-none">
                         {configState.promptHistory?.map((version) => (
                            <div 
                               key={version.version} 
                               onClick={() => isEditing && handleRestorePrompt(version.content)}
                               className={`p-3 rounded border text-left transition-all ${
                                  isEditing ? 'cursor-pointer hover:bg-neutral-800 hover:border-neutral-700' : 'cursor-default opacity-70'
                               } ${configState.systemInstruction === version.content ? 'bg-neutral-800 border-emerald-500/30' : 'bg-surface-base border-neutral-800'}`}
                            >
                               <div className="flex justify-between items-center mb-1">
                                  <Badge variant="neutral">v{version.version}</Badge>
                                  <span className="text-[10px] text-neutral-500">{version.timestamp}</span>
                               </div>
                               <p className="text-xs text-neutral-400 line-clamp-2">{version.content}</p>
                            </div>
                         ))}
                         {(!configState.promptHistory || configState.promptHistory.length === 0) && (
                            <div className="p-4 text-center text-xs text-neutral-600 italic">No history available</div>
                         )}
                      </div>
                   </div>
                </Card>

                {/* Tools & Dependencies */}
                <Card className={`border-neutral-800 ${isEditing ? 'border-emerald-500/30' : ''}`}>
                   <div className="flex items-center gap-2 mb-4 text-emerald-400">
                      <Network size={18} />
                      <h3 className="text-sm font-bold font-mono uppercase">Integration Matrix</h3>
                   </div>

                   <div className="space-y-6">
                      <div>
                         <h4 className="text-xs font-mono text-neutral-500 uppercase mb-3 flex justify-between items-center">
                            <span>Active Toolchain</span>
                            {isEditing && (
                              isAddingTool ? (
                                <div className="flex gap-2 items-center animate-slide-in">
                                  <input 
                                    autoFocus
                                    className="bg-neutral-900 border border-neutral-700 rounded px-2 py-0.5 text-xs text-white outline-none w-24"
                                    placeholder="Tool Name"
                                    value={newToolName}
                                    onChange={e => setNewToolName(e.target.value)}
                                    onKeyDown={e => e.key === 'Enter' && handleAddTool()}
                                  />
                                  <CheckCircle size={14} className="text-emerald-500 cursor-pointer" onClick={handleAddTool} />
                                  <XCircle size={14} className="text-neutral-500 cursor-pointer" onClick={() => setIsAddingTool(false)} />
                                </div>
                              ) : (
                                <span onClick={() => setIsAddingTool(true)} className="text-[10px] text-cyan-400 cursor-pointer hover:underline">+ Add Tool</span>
                              )
                            )}
                         </h4>
                         <div className="flex flex-wrap gap-2">
                            {editTools.length > 0 ? (
                               editTools.map(tool => (
                                  <div key={tool} className={`flex items-center gap-2 px-2 py-1 rounded border text-xs ${isEditing ? 'border-emerald-500/30 bg-emerald-900/10' : 'border-neutral-700 bg-neutral-800'}`}>
                                     <span className="text-neutral-300">{tool}</span>
                                     {isEditing && <XCircle size={12} className="text-neutral-500 hover:text-red-400 cursor-pointer" onClick={() => setEditTools(prev => prev.filter(t => t !== tool))} />}
                                  </div>
                               ))
                            ) : (
                               <span className="text-xs text-neutral-600 italic">No tools enabled.</span>
                            )}
                         </div>
                      </div>

                      <div className="pt-4 border-t border-neutral-800">
                         <h4 className="text-xs font-mono text-neutral-500 uppercase mb-3 flex justify-between items-center">
                            <span>Linked Agents</span>
                            {isEditing && (
                              isAddingDep ? (
                                <div className="flex gap-2 items-center animate-slide-in">
                                  <select 
                                    className="bg-neutral-900 border border-neutral-700 rounded px-2 py-0.5 text-xs text-white outline-none w-24"
                                    value={newDepId}
                                    onChange={e => setNewDepId(e.target.value)}
                                  >
                                    <option value="">Select...</option>
                                    {availableAgents.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                                  </select>
                                  <CheckCircle size={14} className="text-emerald-500 cursor-pointer" onClick={handleAddDep} />
                                  <XCircle size={14} className="text-neutral-500 cursor-pointer" onClick={() => setIsAddingDep(false)} />
                                </div>
                              ) : (
                                <span onClick={() => setIsAddingDep(true)} className="text-[10px] text-cyan-400 cursor-pointer hover:underline">+ Link Agent</span>
                              )
                            )}
                         </h4>
                         
                         {editDeps.length > 0 ? (
                            <div className="space-y-2">
                               {editDeps.map(depId => {
                                  const depAgent = agents.find(a => a.id === depId);
                                  return (
                                     <div key={depId} className="flex items-center gap-3 bg-neutral-900/50 p-2 rounded border border-neutral-800 hover:border-neutral-600 transition-colors group cursor-pointer">
                                        <div className="p-1.5 rounded bg-neutral-800 text-neutral-400 group-hover:text-white">
                                           <Link size={14} />
                                        </div>
                                        <div>
                                           <p className="text-xs font-bold text-neutral-300">{depAgent?.name || `Unknown (${depId})`}</p>
                                           <p className="text-[10px] text-neutral-500 uppercase">{depAgent?.type}</p>
                                        </div>
                                        <div className="ml-auto">
                                            {isEditing ? (
                                                <Trash2 size={14} className="text-neutral-600 hover:text-red-500" onClick={() => setEditDeps(prev => prev.filter(d => d !== depId))} />
                                            ) : (
                                                <StatusDot status={depAgent?.status || 'offline'} />
                                            )}
                                        </div>
                                     </div>
                                  );
                               })}
                            </div>
                         ) : (
                            <div className="text-xs text-neutral-600 italic bg-neutral-900/30 p-3 rounded border border-neutral-800/50 flex items-center justify-center gap-2">
                               <CheckCircle size={14} /> Independent Execution Mode
                            </div>
                         )}
                      </div>
                   </div>
                </Card>

                {/* Fine-Tuning */}
                <Card className="border-neutral-800">
                   <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2 text-neutral-400">
                         <Settings size={18} />
                         <h3 className="text-sm font-bold font-mono uppercase">Fine-Tuning</h3>
                      </div>
                      <Badge variant="neutral">EXPERIMENTAL</Badge>
                   </div>
                   
                   <div className="bg-surface-dim p-4 rounded-lg border border-neutral-800 border-dashed flex flex-col gap-4">
                      <div className="flex items-center gap-4">
                         <div className="w-10 h-10 rounded bg-neutral-800 flex items-center justify-center text-neutral-500">
                            <Activity size={20} />
                         </div>
                         <div>
                            <p className="text-sm font-medium text-neutral-300">LoRA Adapter State</p>
                            <p className="text-xs text-neutral-500">No active adapter loaded.</p>
                         </div>
                      </div>
                      
                      {isEditing && (
                         <div className="pt-2 border-t border-neutral-800">
                            <label className="block text-[10px] font-mono text-neutral-500 uppercase mb-2">Select Checkpoint</label>
                            <select className="w-full bg-neutral-900 border border-neutral-700 rounded p-2 text-xs text-neutral-300 outline-none">
                               <option>Base (v1.0)</option>
                               <option>Code-Instruct (v1.2)</option>
                               <option>Creative-Writing (v0.9)</option>
                            </select>
                         </div>
                      )}
                      
                      <Button variant="secondary" size="sm" className="w-full justify-center opacity-50 cursor-not-allowed">
                         {isEditing ? 'Attach Adapter' : 'Manage Adapters'}
                      </Button>
                   </div>
                </Card>

             </div>
          )}
        </div>
      </div>
    </div>
  );
};
