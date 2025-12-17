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
import { ViewState } from './types';
import { NotificationProvider, useNotifications } from './context/NotificationContext';
import { AgentWatchProvider } from './context/AgentWatchContext';
import { AgentProvider } from './context/AgentContext';
import { AuthProvider } from './context/AuthContext';
import { DashboardDataProvider } from './context/DashboardDataContext';
import { ToastContainer } from './components/UIComponents';

const AppContent: React.FC = () => {
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

const App: React.FC = () => {
  return (
    <AuthProvider>
      <DashboardDataProvider>
        <NotificationProvider>
          <AgentProvider>
            <AgentWatchProvider>
              <AppContent />
            </AgentWatchProvider>
          </AgentProvider>
        </NotificationProvider>
      </DashboardDataProvider>
    </AuthProvider>
  );
};

export default App;
