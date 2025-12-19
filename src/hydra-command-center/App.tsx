import React, { useState } from 'react';
import { MasterLayout } from './templates/MasterLayout';
import { Mission } from './views/Mission';
import { Agents } from './views/Agents';
import { Projects } from './views/Projects';
import { Studio } from './views/Studio';
import { Infra } from './views/Infra';
import { Knowledge } from './views/Knowledge';
import { Lab } from './views/Lab';
import { Home } from './views/Home';
import { Chat } from './views/Chat';
import { Research } from './views/Research';
import { Feedback } from './views/Feedback';
import Briefing from './views/Briefing';
import Settings from './views/Settings';
import { Autonomy } from './views/Autonomy';
import { Games } from './views/Games';
import { Login } from './views/Login';
import { ViewState } from './types';
import { NotificationProvider, useNotifications } from './context/NotificationContext';
import { AgentWatchProvider } from './context/AgentWatchContext';
import { AgentProvider } from './context/AgentContext';
import { DashboardDataProvider } from './context/DashboardDataContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { UserDataProvider } from './context/UserDataContext';
import { ToastContainer } from './components/UIComponents';

// Loading screen component
const LoadingScreen: React.FC = () => (
  <div className="h-screen w-screen flex flex-col items-center justify-center bg-surface-base">
    <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-emerald-500 to-cyan-500 flex items-center justify-center shadow-glow-emerald mb-4 animate-pulse">
      <span className="font-bold text-white text-2xl">H</span>
    </div>
    <div className="text-emerald-500 font-mono text-sm">INITIALIZING HYDRA_COMMAND...</div>
  </div>
);

// Main authenticated app content
const AuthenticatedApp: React.FC = () => {
  const [currentView, setCurrentView] = useState<ViewState>('MISSION');
  const { notifications, removeNotification } = useNotifications();

  const renderView = () => {
    switch (currentView) {
      case 'MISSION':
        return <Mission />;
      case 'AGENTS':
        return <Agents />;
      case 'PROJECTS':
        return <Projects />;
      case 'STUDIO':
        return <Studio />;
      case 'KNOWLEDGE':
        return <Knowledge />;
      case 'LAB':
        return <Lab />;
      case 'INFRA':
        return <Infra />;
      case 'HOME':
        return <Home />;
      case 'CHAT':
        return <Chat />;
      case 'RESEARCH':
        return <Research />;
      case 'FEEDBACK':
        return <Feedback />;
      case 'BRIEFING':
        return <Briefing />;
      case 'SETTINGS':
        return <Settings />;
      case 'AUTONOMY':
        return <Autonomy />;
      case 'GAMES':
        return <Games />;
      default:
        return <Mission />;
    }
  };

  return (
    <MasterLayout currentView={currentView} onNavigate={setCurrentView}>
      {renderView()}
      <ToastContainer notifications={notifications} removeNotification={removeNotification} />
    </MasterLayout>
  );
};

// App content wrapper that handles auth state
const AppContent: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <LoadingScreen />;
  }

  if (!isAuthenticated) {
    return <Login />;
  }

  return <AuthenticatedApp />;
};

const App: React.FC = () => {
  return (
    <AuthProvider>
      <NotificationProvider>
        <UserDataProvider>
          <DashboardDataProvider>
            <AgentProvider>
              <AgentWatchProvider>
                <AppContent />
              </AgentWatchProvider>
            </AgentProvider>
          </DashboardDataProvider>
        </UserDataProvider>
      </NotificationProvider>
    </AuthProvider>
  );
};

export default App;
