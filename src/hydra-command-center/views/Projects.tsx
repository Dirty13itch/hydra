import React, { useState, useEffect } from 'react';
import { Card, StatusDot, ProgressBar, Badge, Button, Tabs, Modal } from '../components/UIComponents';
import { Plus, Filter, FolderKanban, ChevronLeft, CheckCircle2, Circle, AlertCircle, FileCode, Paperclip, User, Sparkles, Brain, RefreshCw, Loader2 } from 'lucide-react';
import { Project } from '../types';
import { useNotifications } from '../context/NotificationContext';
import { useAgents } from '../context/AgentContext';
import { useDashboardData } from '../context/DashboardDataContext';
import { generateProjectTasks } from '../services/geminiService';

// Mock Tasks for detail view
const INITIAL_TASKS = [
  { id: 't1', title: 'Define core architecture schemas', status: 'done', assignee: 'Research-Alpha', description: 'Create initial DB schema and API contracts.' },
  { id: 't2', title: 'Implement JWT authentication flow', status: 'in-progress', assignee: 'Code-Prime', description: 'Setup Passport.js strategies and token refresh.' },
  { id: 't3', title: 'Design database migration strategy', status: 'todo', assignee: 'Code-Prime', description: 'Plan migration from v1 legacy data.' },
  { id: 't4', title: 'Setup CI/CD pipeline actions', status: 'blocked', assignee: 'System-Coord', description: 'Waiting on registry credentials.' },
  { id: 't5', title: 'Generate initial UI mockups', status: 'todo', assignee: 'Creative-Director', description: 'Focus on dashboard components.' },
];

export const Projects: React.FC = () => {
  // Navigation & Data State
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const { projects: apiProjects, projectsLoading, refreshProjects } = useDashboardData();
  const [localProjects, setLocalProjects] = useState<Project[]>([]);

  // Merge API projects with local projects
  const projects = [...localProjects, ...apiProjects];

  // Modal State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDesc, setNewProjectDesc] = useState('');
  const [selectedAgentIds, setSelectedAgentIds] = useState<string[]>([]);

  const { addNotification } = useNotifications();
  const { agents } = useAgents();

  const selectedProject = projects.find(p => p.id === selectedProjectId);

  const handleCreateProject = () => {
    if (!newProjectName.trim()) {
      addNotification('warning', 'Validation Failed', 'Project name is required.');
      return;
    }

    const newProject: Project = {
      id: Date.now().toString(),
      name: newProjectName,
      description: newProjectDesc || 'No description provided.',
      status: 'active',
      agentCount: selectedAgentIds.length,
      agentIds: selectedAgentIds,
      progress: 0,
      lastUpdated: 'Just now'
    };

    setLocalProjects([newProject, ...localProjects]);
    addNotification('success', 'Project Initialized', `Project "${newProjectName}" has been created.`);
    
    // Reset form
    setNewProjectName('');
    setNewProjectDesc('');
    setSelectedAgentIds([]);
    setIsCreateModalOpen(false);
  };

  const toggleAgentSelection = (agentId: string) => {
    setSelectedAgentIds(prev => 
      prev.includes(agentId) 
        ? prev.filter(id => id !== agentId) 
        : [...prev, agentId]
    );
  };

  return (
    <div className="h-full flex flex-col">
      {/* Create Project Modal */}
      <Modal 
        isOpen={isCreateModalOpen} 
        onClose={() => setIsCreateModalOpen(false)}
        title="INITIALIZE NEW PROJECT"
      >
        <div className="space-y-6">
          
          {/* Project Name */}
          <div>
            <label className="block text-xs font-mono text-neutral-500 uppercase mb-2">Project Designation</label>
            <input 
              type="text" 
              className="w-full bg-surface-dim border border-neutral-700 rounded-lg px-4 py-3 text-sm text-neutral-200 focus:border-emerald-500 outline-none transition-colors"
              placeholder="e.g. Operation Chimera"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-mono text-neutral-500 uppercase mb-2">Mission Brief (Description)</label>
            <textarea 
              className="w-full bg-surface-dim border border-neutral-700 rounded-lg px-4 py-3 text-sm text-neutral-200 focus:border-emerald-500 outline-none transition-colors h-24 resize-none"
              placeholder="Describe objectives and scope..."
              value={newProjectDesc}
              onChange={(e) => setNewProjectDesc(e.target.value)}
            />
          </div>

          {/* Agent Selection */}
          <div>
            <label className="block text-xs font-mono text-neutral-500 uppercase mb-2">Assign Core Team</label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-48 overflow-y-auto pr-1">
               {agents.map(agent => {
                 const isSelected = selectedAgentIds.includes(agent.id);
                 return (
                   <div 
                     key={agent.id}
                     onClick={() => toggleAgentSelection(agent.id)}
                     className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-all ${
                       isSelected 
                         ? 'bg-emerald-900/20 border-emerald-500/50' 
                         : 'bg-surface-dim border-neutral-800 hover:border-neutral-700'
                     }`}
                   >
                      <div className="flex items-center gap-3">
                         <div className={`w-8 h-8 rounded flex items-center justify-center font-bold text-xs ${
                            isSelected ? 'bg-emerald-500 text-white' : 'bg-neutral-800 text-neutral-500'
                         }`}>
                           {agent.name.charAt(0)}
                         </div>
                         <div>
                           <p className={`text-sm font-medium ${isSelected ? 'text-emerald-400' : 'text-neutral-300'}`}>{agent.name}</p>
                           <p className="text-[10px] text-neutral-500 uppercase">{agent.type}</p>
                         </div>
                      </div>
                      {isSelected && <CheckCircle2 size={16} className="text-emerald-500" />}
                   </div>
                 );
               })}
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-neutral-800">
             <Button variant="ghost" onClick={() => setIsCreateModalOpen(false)}>Cancel</Button>
             <Button variant="primary" onClick={handleCreateProject}>Create Project</Button>
          </div>
        </div>
      </Modal>

      {selectedProject ? (
        <ProjectDetail project={selectedProject} onBack={() => setSelectedProjectId(null)} />
      ) : (
        <div className="p-6 h-full overflow-y-auto">
          {/* Header */}
          <div className="flex justify-between items-center mb-6">
            <div>
              <h2 className="text-2xl font-mono font-bold text-neutral-200">ACTIVE_PROJECTS</h2>
              <p className="text-sm text-neutral-500 font-mono">Mission critical objectives and workflows</p>
            </div>
            <div className="flex gap-3">
              <Button
                variant="secondary"
                icon={projectsLoading ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
                onClick={refreshProjects}
              >
                Refresh
              </Button>
              <Button variant="secondary" icon={<Filter size={16} />}>Filter</Button>
              <Button
                variant="primary"
                icon={<Plus size={16} />}
                onClick={() => setIsCreateModalOpen(true)}
              >
                New Project
              </Button>
            </div>
          </div>

          {/* Projects Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project) => (
              <Card 
                key={project.id} 
                className="hover:border-neutral-600 transition-colors group cursor-pointer"
                onClick={() => setSelectedProjectId(project.id)}
              >
                {/* Project Header */}
                <div className="flex justify-between items-start mb-3">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-neutral-800 rounded text-neutral-400 group-hover:text-cyan-400 transition-colors">
                      <FolderKanban size={20} />
                    </div>
                    <div>
                      <h3 className="font-bold text-neutral-200 group-hover:text-cyan-400 transition-colors">{project.name}</h3>
                      <div className="flex items-center gap-2 text-xs">
                        <StatusDot status={project.status === 'active' ? 'active' : project.status === 'blocked' ? 'blocked' : 'paused'} />
                        <span className="uppercase font-mono text-neutral-500">{project.status}</span>
                      </div>
                    </div>
                  </div>
                  <Badge variant={project.agentCount > 0 ? 'emerald' : 'neutral'}>
                    {project.agentCount} Agents
                  </Badge>
                </div>

                {/* Description */}
                <p className="text-sm text-neutral-400 mb-6 h-12 line-clamp-2">
                  {project.description}
                </p>

                {/* Progress Section */}
                <div className="space-y-2">
                  <div className="flex justify-between text-xs text-neutral-500 font-mono">
                    <span>COMPLETION</span>
                    <span>{project.progress}%</span>
                  </div>
                  <ProgressBar 
                    value={project.progress} 
                    colorClass={
                      project.status === 'blocked' ? 'bg-red-500' :
                      project.status === 'paused' ? 'bg-amber-500' : 
                      'bg-cyan-500'
                    } 
                  />
                </div>

                {/* Footer */}
                <div className="mt-4 pt-3 border-t border-neutral-800 flex justify-between items-center text-xs font-mono text-neutral-600">
                  <span>ID: PRJ-{project.id.length > 5 ? 'NEW' : project.id.padStart(3, '0')}</span>
                  <span>Updated {project.lastUpdated}</span>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const ProjectDetail: React.FC<{ project: Project; onBack: () => void }> = ({ project, onBack }) => {
  const [activeTab, setActiveTab] = useState('TASKS');
  const [tasks, setTasks] = useState(INITIAL_TASKS);
  
  // Task Modal State
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newTaskDesc, setNewTaskDesc] = useState('');
  const [newTaskAssignee, setNewTaskAssignee] = useState('');
  const [newTaskStatus, setNewTaskStatus] = useState('todo');
  
  // Auto-Plan State
  const [isPlanning, setIsPlanning] = useState(false);
  
  const { addNotification } = useNotifications();
  const { agents } = useAgents();

  // Set default assignee when modal opens or agents load
  React.useEffect(() => {
    if (!newTaskAssignee && agents.length > 0) {
      setNewTaskAssignee(agents[0].name);
    }
  }, [agents, newTaskAssignee]);

  const tabs = [
    { id: 'TASKS', label: 'Task List' },
    { id: 'TEAM', label: 'Assigned Agents' },
    { id: 'FILES', label: 'Artifacts & Files' }
  ];

  const handleAddTask = () => {
    if (!newTaskTitle.trim()) {
      addNotification('warning', 'Validation Failed', 'Task title is required.');
      return;
    }

    const newTask = {
      id: `t${Date.now()}`,
      title: newTaskTitle,
      description: newTaskDesc,
      status: newTaskStatus,
      assignee: newTaskAssignee
    };

    setTasks(prev => [newTask, ...prev]);
    addNotification('success', 'Task Created', `Task "${newTaskTitle}" added to the queue.`);
    
    // Reset
    setNewTaskTitle('');
    setNewTaskDesc('');
    setNewTaskStatus('todo');
    setIsTaskModalOpen(false);
  };
  
  const handleAutoPlan = async () => {
    setIsPlanning(true);
    addNotification('info', 'Auto-Plan Initiated', 'Coordinator agent is breaking down project requirements...');
    
    const newTasks = await generateProjectTasks(project, agents);
    
    if (newTasks.length > 0) {
       const formattedTasks = newTasks.map((t: any, idx) => ({
         id: `ap-${Date.now()}-${idx}`,
         title: t.title,
         description: t.description,
         status: 'todo',
         assignee: t.assignee || 'System-Coord'
       }));
       
       setTasks(prev => [...formattedTasks, ...prev]);
       addNotification('success', 'Planning Complete', `${newTasks.length} tasks generated and assigned.`);
    } else {
       addNotification('error', 'Planning Failed', 'Could not generate tasks. Check system logs.');
    }
    
    setIsPlanning(false);
  };
  
  const assignedAgents = agents.filter(a => project.agentIds?.includes(a.id));

  return (
    <div className="flex flex-col h-full bg-surface-base">
      
      {/* Create Task Modal */}
      <Modal 
        isOpen={isTaskModalOpen} 
        onClose={() => setIsTaskModalOpen(false)} 
        title="ADD NEW DIRECTIVE"
      >
         <div className="space-y-4">
            <div>
               <label className="block text-xs font-mono text-neutral-500 uppercase mb-2">Directive Title</label>
               <input 
                  type="text" 
                  value={newTaskTitle}
                  onChange={(e) => setNewTaskTitle(e.target.value)}
                  className="w-full bg-surface-dim border border-neutral-700 rounded-lg px-4 py-3 text-sm text-neutral-200 outline-none focus:border-emerald-500"
                  placeholder="Enter task name..."
               />
            </div>
            
            <div>
               <label className="block text-xs font-mono text-neutral-500 uppercase mb-2">Description</label>
               <textarea 
                  value={newTaskDesc}
                  onChange={(e) => setNewTaskDesc(e.target.value)}
                  className="w-full bg-surface-dim border border-neutral-700 rounded-lg px-4 py-3 text-sm text-neutral-200 outline-none focus:border-emerald-500 h-24 resize-none"
                  placeholder="Additional context or acceptance criteria..."
               />
            </div>

            <div className="grid grid-cols-2 gap-4">
               <div>
                  <label className="block text-xs font-mono text-neutral-500 uppercase mb-2">Assign Agent</label>
                  <div className="relative">
                     <select 
                        value={newTaskAssignee}
                        onChange={(e) => setNewTaskAssignee(e.target.value)}
                        className="w-full bg-surface-dim border border-neutral-700 rounded-lg px-4 py-3 text-sm text-neutral-200 outline-none focus:border-emerald-500 appearance-none"
                     >
                        {agents.map(agent => (
                           <option key={agent.id} value={agent.name}>{agent.name} ({agent.type})</option>
                        ))}
                     </select>
                     <User size={16} className="absolute right-3 top-3.5 text-neutral-500 pointer-events-none" />
                  </div>
               </div>
               
               <div>
                  <label className="block text-xs font-mono text-neutral-500 uppercase mb-2">Initial Status</label>
                  <select 
                     value={newTaskStatus}
                     onChange={(e) => setNewTaskStatus(e.target.value)}
                     className="w-full bg-surface-dim border border-neutral-700 rounded-lg px-4 py-3 text-sm text-neutral-200 outline-none focus:border-emerald-500 appearance-none"
                  >
                     <option value="todo">To Do</option>
                     <option value="in-progress">In Progress</option>
                     <option value="blocked">Blocked</option>
                     <option value="done">Done</option>
                  </select>
               </div>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-neutral-800">
               <Button variant="ghost" onClick={() => setIsTaskModalOpen(false)}>Cancel</Button>
               <Button variant="primary" onClick={handleAddTask}>Add Task</Button>
            </div>
         </div>
      </Modal>

      {/* Detail Header */}
      <div className="px-6 py-4 border-b border-neutral-800 flex items-center justify-between bg-surface-default">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="p-2 hover:bg-neutral-800 rounded-full text-neutral-400 hover:text-white transition-colors">
            <ChevronLeft size={20} />
          </button>
          <div>
            <h2 className="text-xl font-mono font-bold text-neutral-200 flex items-center gap-3">
              {project.name}
              <StatusDot status={project.status === 'active' ? 'active' : project.status === 'blocked' ? 'blocked' : 'paused'} />
            </h2>
            <div className="flex items-center gap-2 text-xs text-neutral-500 font-mono mt-1">
              <span>ID: PRJ-{project.id.length > 5 ? 'NEW' : project.id.padStart(3, '0')}</span>
              <span>•</span>
              <span>Last Updated: {project.lastUpdated}</span>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
           <Button 
             variant="secondary" 
             className={isPlanning ? "animate-pulse border-cyan-500 text-cyan-400" : ""}
             icon={isPlanning ? <Brain size={16} /> : <Sparkles size={16} />}
             onClick={handleAutoPlan}
             disabled={isPlanning}
            >
             {isPlanning ? 'Analyzing...' : 'Auto-Plan'}
           </Button>
           <Button variant="primary" icon={<Plus size={16} />} onClick={() => setIsTaskModalOpen(true)}>Add Task</Button>
        </div>
      </div>

      {/* Detail Content */}
      <div className="flex-1 overflow-hidden flex flex-col p-6">
        
        {/* Project Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <Card className="border-neutral-800">
             <div className="flex justify-between items-start mb-2">
               <h4 className="text-xs font-mono text-neutral-500 uppercase">Overall Progress</h4>
               <span className="text-lg font-bold text-cyan-400">{project.progress}%</span>
             </div>
             <ProgressBar value={project.progress} colorClass="bg-cyan-500" />
             <p className="text-xs text-neutral-500 mt-2">Estimated completion: 3 days</p>
          </Card>
          
          <Card className="border-neutral-800">
             <h4 className="text-xs font-mono text-neutral-500 uppercase mb-2">Task Health</h4>
             <div className="flex gap-4">
               <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                  <span className="text-sm text-neutral-300">12 Done</span>
               </div>
               <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse"></div>
                  <span className="text-sm text-neutral-300">3 Active</span>
               </div>
               <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-red-500"></div>
                  <span className="text-sm text-neutral-300">1 Blocked</span>
               </div>
             </div>
          </Card>

           <Card className="border-neutral-800">
             <h4 className="text-xs font-mono text-neutral-500 uppercase mb-2">Resource Usage</h4>
             <div className="flex justify-between items-center mb-1">
               <span className="text-sm text-neutral-400">Compute Budget</span>
               <span className="text-sm text-neutral-200 font-mono">15.4 / 100 hrs</span>
             </div>
             <div className="h-1 w-full bg-neutral-800 rounded-full overflow-hidden">
                <div className="h-full bg-purple-500" style={{ width: '15%' }} />
             </div>
          </Card>
        </div>

        <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} className="mb-4" />

        <div className="flex-1 min-h-0 overflow-y-auto">
          {activeTab === 'TASKS' && (
             <div className="space-y-2">
               {tasks.map(task => (
                 <div key={task.id} className="flex items-center justify-between p-4 bg-surface-default border border-neutral-800 rounded-lg hover:border-neutral-700 transition-colors group">
                    <div className="flex items-center gap-4">
                      {task.status === 'done' ? <CheckCircle2 className="text-emerald-500" size={20} /> :
                       task.status === 'in-progress' ? <Circle className="text-cyan-500" size={20} /> :
                       task.status === 'blocked' ? <AlertCircle className="text-red-500" size={20} /> :
                       <Circle className="text-neutral-600" size={20} />}
                      
                      <div>
                        <p className={`font-medium ${task.status === 'done' ? 'text-neutral-500 line-through' : 'text-neutral-200'}`}>{task.title}</p>
                        <p className="text-xs text-neutral-500 font-mono flex items-center gap-2 mt-1">
                          <span className="bg-neutral-800 px-1.5 py-0.5 rounded text-neutral-400">{task.id.toUpperCase()}</span>
                          <span>Assigned to {task.assignee}</span>
                        </p>
                      </div>
                    </div>
                    
                    <Badge variant={
                       task.status === 'done' ? 'emerald' : 
                       task.status === 'in-progress' ? 'cyan' : 
                       task.status === 'blocked' ? 'red' : 'neutral'
                    }>
                       {task.status.toUpperCase()}
                    </Badge>
                 </div>
               ))}
               {tasks.length === 0 && (
                 <div className="text-center py-12 text-neutral-600 border border-dashed border-neutral-800 rounded-lg">
                    <p>No active directives found.</p>
                 </div>
               )}
             </div>
          )}

          {activeTab === 'TEAM' && (
             <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {assignedAgents.length > 0 ? assignedAgents.map(agent => (
                   <Card key={agent.id} className="flex items-center gap-4">
                      <div className="h-10 w-10 bg-neutral-800 rounded-full flex items-center justify-center font-bold text-neutral-400">
                        {agent.name.charAt(0)}
                      </div>
                      <div>
                        <h4 className="font-bold text-neutral-200">{agent.name}</h4>
                        <p className="text-xs text-neutral-500 font-mono">{agent.type} Specialist</p>
                      </div>
                      <div className="ml-auto">
                        <StatusDot status={agent.status} />
                      </div>
                   </Card>
                )) : (
                  <div className="col-span-full text-center py-8 text-neutral-500 italic border border-dashed border-neutral-800 rounded-lg">
                    No agents assigned to this project.
                  </div>
                )}
             </div>
          )}

          {activeTab === 'FILES' && (
             <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[1,2,3].map(i => (
                  <Card key={i} className="hover:border-cyan-500/40 transition-colors cursor-pointer group">
                     <div className="flex items-center gap-3 mb-3">
                        <div className="p-2 bg-neutral-800 rounded text-cyan-400 group-hover:text-cyan-300">
                           {i === 2 ? <FileCode size={20} /> : <Paperclip size={20} />}
                        </div>
                        <div>
                           <p className="text-sm font-medium text-neutral-200 truncate">architecture_v{i}.pdf</p>
                           <p className="text-xs text-neutral-500">1.2 MB • 2h ago</p>
                        </div>
                     </div>
                  </Card>
                ))}
             </div>
          )}
        </div>
      </div>
    </div>
  );
};