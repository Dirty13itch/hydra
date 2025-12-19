import React, { useState } from 'react';
import { ViewState } from '../types';
import { ConversationBridge } from '../features/bridge/ConversationBridge';
import { useAuth, AUTH_ENABLED } from '../context/AuthContext';
import { useDashboardData } from '../context/DashboardDataContext';
import { useAgents } from '../context/AgentContext';
import {
  LayoutDashboard,
  Users,
  Briefcase,
  Palette,
  Database,
  FlaskConical,
  Server,
  Home as HomeIcon,
  Settings as SettingsIcon,
  Bell,
  MessageSquare,
  X,
  LogOut,
  Shield,
  BookOpen,
  ThumbsUp,
  Sun,
  Cog,
  Brain,
  Gamepad2
} from 'lucide-react';

interface MasterLayoutProps {
  currentView: ViewState;
  onNavigate: (view: ViewState) => void;
  children: React.ReactNode;
}

export const MasterLayout: React.FC<MasterLayoutProps> = ({ currentView, onNavigate, children }) => {
  const [isMobileChatOpen, setIsMobileChatOpen] = useState(false);
  const { user, logout, authEnabled } = useAuth();
  const { stats, nodes } = useDashboardData();
  const { agents } = useAgents();

  // Calculate dynamic stats
  const activeAgentsCount = agents.filter(a => a.status === 'active' || a.status === 'thinking').length;
  const totalPower = stats?.systemPower ?? 0;
  const nodeCount = nodes.length || 3;

  const navItems: { id: ViewState; label: string; icon: React.ReactNode }[] = [
    { id: 'MISSION', label: 'Mission', icon: <LayoutDashboard size={20} /> },
    { id: 'AGENTS', label: 'Agents', icon: <Users size={20} /> },
    { id: 'CHAT', label: 'Chat', icon: <MessageSquare size={20} /> },
    { id: 'PROJECTS', label: 'Projects', icon: <Briefcase size={20} /> },
    { id: 'STUDIO', label: 'Studio', icon: <Palette size={20} /> },
    { id: 'KNOWLEDGE', label: 'Knowl.', icon: <Database size={20} /> },
    { id: 'RESEARCH', label: 'Research', icon: <BookOpen size={20} /> },
    { id: 'FEEDBACK', label: 'Feedback', icon: <ThumbsUp size={20} /> },
    { id: 'BRIEFING', label: 'Briefing', icon: <Sun size={20} /> },
    { id: 'LAB', label: 'Lab', icon: <FlaskConical size={20} /> },
    { id: 'INFRA', label: 'Infra', icon: <Server size={20} /> },
    { id: 'HOME', label: 'Home', icon: <HomeIcon size={20} /> },
    { id: 'AUTONOMY', label: 'Autonomy', icon: <Brain size={20} /> },
    { id: 'GAMES', label: 'Games', icon: <Gamepad2 size={20} /> },
    { id: 'SETTINGS', label: 'Settings', icon: <Cog size={20} /> },
  ];

  return (
    <div className="flex flex-col h-screen w-screen bg-surface-base text-neutral-200 overflow-hidden">
      
      {/* HEADER */}
      <header className="h-16 flex-none bg-surface-base border-b border-neutral-800 flex items-center justify-between px-6 z-20">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-gradient-to-br from-emerald-500 to-cyan-500 flex items-center justify-center shadow-glow-emerald">
             <span className="font-bold text-white text-lg">H</span>
          </div>
          <h1 className="text-xl font-mono font-bold tracking-tight">
            <span className="text-emerald-500">HYDRA</span>
            <span className="text-neutral-500">_COMMAND</span>
          </h1>
        </div>

        <div className="flex items-center gap-6 text-sm font-mono text-neutral-500 hidden lg:flex">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${activeAgentsCount > 0 ? 'bg-emerald-500 animate-pulse' : 'bg-neutral-600'}`}></span>
            <span className="text-neutral-300">{activeAgentsCount} AGENT{activeAgentsCount !== 1 ? 'S' : ''} ACTIVE</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`${totalPower > 1000 ? 'text-amber-500' : totalPower > 500 ? 'text-yellow-500' : 'text-emerald-500'}`}>
              ⚡ {totalPower > 0 ? totalPower.toLocaleString() : '---'}W
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-neutral-300">{nodeCount} NODE{nodeCount !== 1 ? 'S' : ''}</span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button
             className="xl:hidden p-2 text-neutral-400 hover:text-white transition-colors"
             onClick={() => setIsMobileChatOpen(!isMobileChatOpen)}
          >
             <MessageSquare size={20} className={isMobileChatOpen ? 'text-emerald-400' : ''} />
          </button>
          <button className="p-2 text-neutral-400 hover:text-white transition-colors relative">
            <Bell size={20} />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border border-surface-base"></span>
          </button>
          <button className="p-2 text-neutral-400 hover:text-white transition-colors">
            <SettingsIcon size={20} />
          </button>

          {/* User Profile Section */}
          {user && (
            <div className="hidden md:flex items-center gap-3 pl-3 border-l border-neutral-700">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-600 to-cyan-600 flex items-center justify-center">
                  <span className="text-white text-xs font-bold uppercase">
                    {user.username.charAt(0)}
                  </span>
                </div>
                <div className="hidden lg:block">
                  <p className="text-xs font-medium text-neutral-200">{user.username}</p>
                  <p className="text-[10px] text-neutral-500 uppercase flex items-center gap-1">
                    <Shield size={10} className={user.role === 'admin' ? 'text-amber-500' : 'text-neutral-500'} />
                    {user.role}
                  </p>
                </div>
              </div>
              {authEnabled && (
                <button
                  onClick={logout}
                  className="p-2 text-neutral-400 hover:text-red-400 transition-colors"
                  title="Logout"
                >
                  <LogOut size={18} />
                </button>
              )}
            </div>
          )}
        </div>
      </header>

      {/* MAIN BODY */}
      <div className="flex flex-1 overflow-hidden relative">
        
        {/* SIDE NAV */}
        <nav className="w-16 md:w-20 flex-none bg-surface-dim border-r border-neutral-800 flex flex-col items-center py-6 gap-2 z-10 overflow-y-auto no-scrollbar">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`flex flex-col items-center justify-center w-full h-16 gap-1 transition-all relative shrink-0 ${
                currentView === item.id 
                  ? 'text-emerald-400 bg-emerald-900/10' 
                  : 'text-neutral-500 hover:text-neutral-200 hover:bg-neutral-800/50'
              }`}
            >
              {currentView === item.id && (
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-emerald-500 shadow-glow-emerald" />
              )}
              {item.icon}
              <span className="text-[10px] font-medium tracking-wide hidden md:block">{item.label}</span>
            </button>
          ))}
        </nav>

        {/* CONTENT AREA */}
        <main className="flex-1 bg-surface-base relative overflow-hidden flex">
          <div className="flex-1 h-full overflow-hidden relative z-0">
            {children}
          </div>
          
          {/* RIGHT BRIDGE PANEL (Desktop) */}
          <aside className="hidden xl:flex h-full border-l border-neutral-800 z-10">
             <ConversationBridge />
          </aside>

          {/* MOBILE BRIDGE DRAWER */}
          {isMobileChatOpen && (
             <div className="absolute inset-0 z-50 bg-surface-base xl:hidden flex flex-col animate-slide-in">
                <div className="flex justify-end p-2 border-b border-neutral-800 bg-surface-default">
                   <button onClick={() => setIsMobileChatOpen(false)} className="p-2 text-neutral-400">
                      <X size={24} />
                   </button>
                </div>
                <div className="flex-1 overflow-hidden">
                   <ConversationBridge />
                </div>
             </div>
          )}
        </main>
      </div>
    </div>
  );
};