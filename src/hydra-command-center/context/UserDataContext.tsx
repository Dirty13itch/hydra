import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { CredentialStatus, UserProfile, ServiceCredentialStatus } from '../types';
import { useNotifications } from './NotificationContext';

const API_BASE = 'http://192.168.1.244:8700';

// Feature to credential mapping
const FEATURE_REQUIREMENTS: Record<string, string[]> = {
  calendar: ['google'],
  email: ['google'],
  home_automation: ['home_assistant'],
  presence: ['home_assistant'],
  news: ['miniflux'],
  discord_alerts: ['discord'],
  weather: ['weather'],
  voice: [],  // Local, no credentials needed
  inference: [],  // Internal
  image_generation: [],  // Internal
};

// Service definitions for UI
export const SERVICE_DEFINITIONS: Record<string, {
  name: string;
  description: string;
  type: 'oauth' | 'api_key';
  features: string[];
  setupInstructions?: string;
}> = {
  google: {
    name: 'Google',
    description: 'Calendar and Gmail integration for schedule awareness and email summaries.',
    type: 'oauth',
    features: ['Calendar events', 'Email summary', 'Meeting detection', 'Schedule-aware inference'],
    setupInstructions: 'Click Connect to authorize access to Google Calendar and Gmail.',
  },
  home_assistant: {
    name: 'Home Assistant',
    description: 'Smart home control and presence-based automation.',
    type: 'api_key',
    features: ['Device control', 'Presence detection', 'Scene activation', 'Entity monitoring'],
    setupInstructions: 'Create a Long-Lived Access Token in Home Assistant: Profile > Security > Long-Lived Access Tokens.',
  },
  miniflux: {
    name: 'Miniflux (News)',
    description: 'RSS feed aggregation and news topic monitoring.',
    type: 'api_key',
    features: ['News headlines', 'Topic monitoring', 'Feed aggregation'],
    setupInstructions: 'Get your API key from Miniflux: Settings > API Keys.',
  },
  discord: {
    name: 'Discord',
    description: 'Send notifications and alerts to Discord channels.',
    type: 'api_key',
    features: ['Alert notifications', 'Briefing delivery', 'Status updates'],
    setupInstructions: 'Create a webhook in Discord: Server Settings > Integrations > Webhooks.',
  },
  weather: {
    name: 'Weather',
    description: 'Weather forecasts in morning briefings.',
    type: 'api_key',
    features: ['Weather forecast', 'Temperature alerts'],
    setupInstructions: 'Get a free API key from OpenWeatherMap.org.',
  },
};

interface UserDataContextType {
  // Profile
  profile: UserProfile | null;
  profileLoading: boolean;
  updateProfile: (updates: Partial<UserProfile>) => Promise<void>;
  refreshProfile: () => Promise<void>;

  // Credentials
  credentialStatus: CredentialStatus | null;
  credentialsLoading: boolean;
  refreshCredentialStatus: () => Promise<void>;
  testCredential: (service: string) => Promise<{ valid: boolean; message: string }>;
  setApiKey: (service: string, apiKey: string) => Promise<{ success: boolean; message: string }>;
  removeCredential: (service: string) => Promise<{ success: boolean; message: string }>;

  // OAuth
  startOAuthFlow: (provider: string) => void;

  // Feature checks
  isFeatureEnabled: (feature: string) => boolean;
  getMissingCredentials: (feature: string) => string[];
  getServiceStatus: (service: string) => ServiceCredentialStatus | null;

  // Error
  error: string | null;
  clearError: () => void;
}

const UserDataContext = createContext<UserDataContextType | null>(null);

// Default profile values
const DEFAULT_PROFILE: UserProfile = {
  userId: 'default',
  displayName: 'Hydra User',
  timezone: 'America/Chicago',
  theme: 'dark',
  preferences: {
    notifications: {
      enabled: true,
      types: ['alerts', 'briefings', 'research'],
    },
    dashboard: {
      defaultView: 'MISSION',
      refreshInterval: 30,
    },
    ai: {
      preferredModel: 'auto',
      temperature: 0.7,
      maxTokens: 4096,
    },
  },
  contacts: [],
  locations: [],
  schedules: [],
};

export const UserDataProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const [credentialStatus, setCredentialStatus] = useState<CredentialStatus | null>(null);
  const [credentialsLoading, setCredentialsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { addNotification } = useNotifications();

  // Fetch user profile
  const refreshProfile = useCallback(async () => {
    try {
      setProfileLoading(true);
      const response = await fetch(`${API_BASE}/user-data/profile`);
      if (response.ok) {
        const data = await response.json();
        setProfile(data);
      } else if (response.status === 404) {
        // Profile doesn't exist yet, use defaults
        setProfile(DEFAULT_PROFILE);
      } else {
        throw new Error('Failed to load profile');
      }
    } catch (err) {
      console.error('Failed to load profile:', err);
      // Use defaults on error
      setProfile(DEFAULT_PROFILE);
    } finally {
      setProfileLoading(false);
    }
  }, []);

  // Fetch credential status
  const refreshCredentialStatus = useCallback(async () => {
    try {
      setCredentialsLoading(true);
      const response = await fetch(`${API_BASE}/credentials/status`);
      if (response.ok) {
        const data = await response.json();
        setCredentialStatus(data);
      } else {
        // Create default status if endpoint doesn't exist yet
        const defaultStatus: CredentialStatus = {
          services: {},
          summary: {
            configured: 0,
            total: Object.keys(SERVICE_DEFINITIONS).length,
            valid: 0,
            featuresEnabled: [],
            featuresDisabled: Object.keys(FEATURE_REQUIREMENTS),
          },
        };

        // Try to get status from existing endpoints
        const statuses = await Promise.allSettled([
          fetch(`${API_BASE}/google/status`).then(r => r.ok ? r.json() : null),
          fetch(`${API_BASE}/gmail/status`).then(r => r.ok ? r.json() : null),
          fetch(`${API_BASE}/news/status`).then(r => r.ok ? r.json() : null),
          fetch(`${API_BASE}/home/status`).then(r => r.ok ? r.json() : null),
        ]);

        // Google (Calendar + Gmail)
        const googleStatus = statuses[0].status === 'fulfilled' ? statuses[0].value : null;
        const gmailStatus = statuses[1].status === 'fulfilled' ? statuses[1].value : null;
        const configured = googleStatus?.configured || gmailStatus?.authenticated;
        defaultStatus.services.google = {
          configured: !!configured,
          valid: googleStatus?.authenticated || gmailStatus?.authenticated || null,
          lastValidated: null,
          type: 'oauth',
          featuresUnlocked: configured ? ['calendar', 'email'] : [],
        };

        // News (Miniflux)
        const newsStatus = statuses[2].status === 'fulfilled' ? statuses[2].value : null;
        defaultStatus.services.miniflux = {
          configured: !!newsStatus?.configured,
          valid: newsStatus?.configured ? true : null,
          lastValidated: null,
          type: 'api_key',
          featuresUnlocked: newsStatus?.configured ? ['news'] : [],
        };

        // Home Assistant
        const homeStatus = statuses[3].status === 'fulfilled' ? statuses[3].value : null;
        defaultStatus.services.home_assistant = {
          configured: !!homeStatus?.connected,
          valid: homeStatus?.connected || null,
          lastValidated: null,
          type: 'api_key',
          featuresUnlocked: homeStatus?.connected ? ['home_automation', 'presence'] : [],
        };

        // Discord, Weather (defaults - not configured)
        defaultStatus.services.discord = {
          configured: false,
          valid: null,
          lastValidated: null,
          type: 'api_key',
          featuresUnlocked: [],
        };
        defaultStatus.services.weather = {
          configured: false,
          valid: null,
          lastValidated: null,
          type: 'api_key',
          featuresUnlocked: [],
        };

        // Update summary
        defaultStatus.summary.configured = Object.values(defaultStatus.services).filter(s => s.configured).length;
        defaultStatus.summary.valid = Object.values(defaultStatus.services).filter(s => s.valid).length;
        defaultStatus.summary.featuresEnabled = Object.values(defaultStatus.services).flatMap(s => s.featuresUnlocked);
        defaultStatus.summary.featuresDisabled = Object.keys(FEATURE_REQUIREMENTS).filter(
          f => !defaultStatus.summary.featuresEnabled.includes(f)
        );

        setCredentialStatus(defaultStatus);
      }
    } catch (err) {
      console.error('Failed to load credential status:', err);
    } finally {
      setCredentialsLoading(false);
    }
  }, []);

  // Update profile
  const updateProfile = useCallback(async (updates: Partial<UserProfile>) => {
    try {
      const response = await fetch(`${API_BASE}/user-data/profile`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (response.ok) {
        const data = await response.json();
        setProfile(data);
        addNotification('success', 'Profile Updated', 'Your profile has been saved.');
      } else {
        throw new Error('Failed to update profile');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Update failed';
      setError(message);
      addNotification('error', 'Update Failed', message);
      throw err;
    }
  }, [addNotification]);

  // Test a credential
  const testCredential = useCallback(async (service: string): Promise<{ valid: boolean; message: string }> => {
    try {
      const response = await fetch(`${API_BASE}/credentials/test/${service}`, {
        method: 'POST',
      });
      const data = await response.json();

      // Refresh status after test
      await refreshCredentialStatus();

      if (data.valid) {
        addNotification('success', 'Connection Valid', `${SERVICE_DEFINITIONS[service]?.name || service} is working correctly.`);
      } else {
        addNotification('warning', 'Connection Failed', data.message || 'Could not validate credentials.');
      }

      return data;
    } catch (err) {
      const message = 'Test failed - could not connect to service';
      addNotification('error', 'Test Failed', message);
      return { valid: false, message };
    }
  }, [refreshCredentialStatus, addNotification]);

  // Set an API key
  const setApiKey = useCallback(async (service: string, apiKey: string): Promise<{ success: boolean; message: string }> => {
    try {
      const response = await fetch(`${API_BASE}/credentials/api-key/${service}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey }),
      });

      if (response.ok) {
        await refreshCredentialStatus();
        addNotification('success', 'Credential Saved', `${SERVICE_DEFINITIONS[service]?.name || service} API key has been saved.`);
        return { success: true, message: 'Credential saved successfully' };
      } else {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to save credential');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to save credential';
      addNotification('error', 'Save Failed', message);
      return { success: false, message };
    }
  }, [refreshCredentialStatus, addNotification]);

  // Remove a credential
  const removeCredential = useCallback(async (service: string): Promise<{ success: boolean; message: string }> => {
    try {
      const response = await fetch(`${API_BASE}/credentials/api-key/${service}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        await refreshCredentialStatus();
        addNotification('info', 'Credential Removed', `${SERVICE_DEFINITIONS[service]?.name || service} has been disconnected.`);
        return { success: true, message: 'Credential removed' };
      } else {
        throw new Error('Failed to remove credential');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to remove credential';
      addNotification('error', 'Remove Failed', message);
      return { success: false, message };
    }
  }, [refreshCredentialStatus, addNotification]);

  // Start OAuth flow
  const startOAuthFlow = useCallback((provider: string) => {
    // Open OAuth in popup window for better UX
    const width = 600;
    const height = 700;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;

    const popup = window.open(
      `${API_BASE}/google/auth`,
      `oauth_${provider}`,
      `width=${width},height=${height},left=${left},top=${top},toolbar=no,menubar=no`
    );

    // Poll for popup close
    const checkClosed = setInterval(() => {
      if (popup?.closed) {
        clearInterval(checkClosed);
        // Refresh status after OAuth completes
        setTimeout(() => {
          refreshCredentialStatus();
          addNotification('info', 'OAuth Complete', 'Checking connection status...');
        }, 1000);
      }
    }, 500);

    // Timeout after 5 minutes
    setTimeout(() => {
      clearInterval(checkClosed);
    }, 300000);
  }, [refreshCredentialStatus, addNotification]);

  // Check if a feature is enabled
  const isFeatureEnabled = useCallback((feature: string): boolean => {
    if (!credentialStatus) return false;
    const requirements = FEATURE_REQUIREMENTS[feature] || [];
    if (requirements.length === 0) return true; // No requirements = always enabled
    return requirements.every(
      req => credentialStatus.services[req]?.configured &&
             credentialStatus.services[req]?.valid !== false
    );
  }, [credentialStatus]);

  // Get missing credentials for a feature
  const getMissingCredentials = useCallback((feature: string): string[] => {
    if (!credentialStatus) return [];
    const requirements = FEATURE_REQUIREMENTS[feature] || [];
    return requirements.filter(
      req => !credentialStatus.services[req]?.configured ||
             credentialStatus.services[req]?.valid === false
    );
  }, [credentialStatus]);

  // Get status for a specific service
  const getServiceStatus = useCallback((service: string): ServiceCredentialStatus | null => {
    return credentialStatus?.services[service] || null;
  }, [credentialStatus]);

  const clearError = useCallback(() => setError(null), []);

  // Initial load
  useEffect(() => {
    refreshProfile();
    refreshCredentialStatus();
  }, [refreshProfile, refreshCredentialStatus]);

  return (
    <UserDataContext.Provider
      value={{
        profile,
        profileLoading,
        updateProfile,
        refreshProfile,
        credentialStatus,
        credentialsLoading,
        refreshCredentialStatus,
        testCredential,
        setApiKey,
        removeCredential,
        startOAuthFlow,
        isFeatureEnabled,
        getMissingCredentials,
        getServiceStatus,
        error,
        clearError,
      }}
    >
      {children}
    </UserDataContext.Provider>
  );
};

export const useUserData = () => {
  const context = useContext(UserDataContext);
  if (!context) {
    throw new Error('useUserData must be used within a UserDataProvider');
  }
  return context;
};
