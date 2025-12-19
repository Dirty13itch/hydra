import React, { useState, useEffect } from 'react';
import {
  User, Key, Bell, Sliders, Database, Shield,
  Check, X, RefreshCw, ExternalLink, ChevronRight,
  Eye, EyeOff, Trash2, TestTube, Settings as SettingsIcon,
  Globe, Clock, Palette, Cpu, Save, AlertCircle, Info
} from 'lucide-react';
import { useUserData, SERVICE_DEFINITIONS } from '../context/UserDataContext';
import { useNotifications } from '../context/NotificationContext';
import { ServiceCredentialStatus, ViewState } from '../types';

// Integration Card Component
const IntegrationCard: React.FC<{
  serviceKey: string;
  name: string;
  description: string;
  features: string[];
  type: 'oauth' | 'api_key';
  setupInstructions?: string;
  status: ServiceCredentialStatus | null;
}> = ({ serviceKey, name, description, features, type, setupInstructions, status }) => {
  const { startOAuthFlow, testCredential, setApiKey, removeCredential } = useUserData();
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [showKeyInput, setShowKeyInput] = useState(false);
  const [showKey, setShowKey] = useState(false);
  const [showInstructions, setShowInstructions] = useState(false);

  const isConfigured = status?.configured || false;
  const isValid = status?.valid;

  const handleTest = async () => {
    setTesting(true);
    await testCredential(serviceKey);
    setTesting(false);
  };

  const handleConnect = () => {
    if (type === 'oauth') {
      startOAuthFlow(serviceKey);
    } else {
      setShowKeyInput(true);
    }
  };

  const handleSaveApiKey = async () => {
    if (!apiKeyInput.trim()) return;
    setSaving(true);
    const result = await setApiKey(serviceKey, apiKeyInput.trim());
    setSaving(false);
    if (result.success) {
      setApiKeyInput('');
      setShowKeyInput(false);
    }
  };

  const handleRemove = async () => {
    if (window.confirm(`Disconnect ${name}? This will remove your saved credentials.`)) {
      await removeCredential(serviceKey);
    }
  };

  const getStatusBadge = () => {
    if (!isConfigured) {
      return (
        <span className="flex items-center gap-1 text-xs px-2 py-1 rounded bg-neutral-800 text-neutral-400">
          Not Configured
        </span>
      );
    }
    if (isValid === true) {
      return (
        <span className="flex items-center gap-1 text-xs px-2 py-1 rounded bg-emerald-900/30 text-emerald-400">
          <Check size={12} /> Connected
        </span>
      );
    }
    if (isValid === false) {
      return (
        <span className="flex items-center gap-1 text-xs px-2 py-1 rounded bg-red-900/30 text-red-400">
          <X size={12} /> Invalid
        </span>
      );
    }
    return (
      <span className="flex items-center gap-1 text-xs px-2 py-1 rounded bg-yellow-900/30 text-yellow-400">
        <AlertCircle size={12} /> Not Tested
      </span>
    );
  };

  return (
    <div className="bg-surface-dim border border-neutral-800 rounded-lg p-4 hover:border-neutral-700 transition-colors">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-medium text-neutral-200">{name}</h3>
        {getStatusBadge()}
      </div>

      {/* Description */}
      <p className="text-sm text-neutral-400 mb-3">{description}</p>

      {/* Features */}
      {features.length > 0 && (
        <div className="mb-4">
          <p className="text-xs text-neutral-500 mb-1">Unlocks:</p>
          <div className="flex flex-wrap gap-1">
            {features.map(f => (
              <span key={f} className="text-xs px-2 py-0.5 rounded bg-neutral-800 text-neutral-300">
                {f}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Setup Instructions (collapsible) */}
      {setupInstructions && (
        <div className="mb-3">
          <button
            onClick={() => setShowInstructions(!showInstructions)}
            className="flex items-center gap-1 text-xs text-neutral-500 hover:text-neutral-300"
          >
            <Info size={12} />
            {showInstructions ? 'Hide setup instructions' : 'Show setup instructions'}
          </button>
          {showInstructions && (
            <p className="mt-2 text-xs text-neutral-400 bg-neutral-900/50 p-2 rounded">
              {setupInstructions}
            </p>
          )}
        </div>
      )}

      {/* API Key Input */}
      {showKeyInput && (
        <div className="mb-3 space-y-2">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                type={showKey ? 'text' : 'password'}
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSaveApiKey()}
                placeholder="Enter API key or token..."
                className="w-full bg-surface-base border border-neutral-700 rounded px-3 py-2 pr-10 text-sm text-neutral-200 focus:border-emerald-500 focus:outline-none"
                autoFocus
              />
              <button
                onClick={() => setShowKey(!showKey)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-neutral-300"
              >
                {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleSaveApiKey}
              disabled={!apiKeyInput.trim() || saving}
              className="flex items-center gap-1 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-neutral-700 disabled:text-neutral-500 text-white text-sm rounded transition-colors"
            >
              {saving ? <RefreshCw size={14} className="animate-spin" /> : <Save size={14} />}
              Save
            </button>
            <button
              onClick={() => { setShowKeyInput(false); setApiKeyInput(''); }}
              className="px-3 py-1.5 bg-neutral-700 hover:bg-neutral-600 text-neutral-200 text-sm rounded transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      {!showKeyInput && (
        <div className="flex gap-2 flex-wrap">
          {isConfigured ? (
            <>
              <button
                onClick={handleTest}
                disabled={testing}
                className="flex items-center gap-1 px-3 py-1.5 bg-neutral-700 hover:bg-neutral-600 text-neutral-200 text-sm rounded transition-colors disabled:opacity-50"
              >
                {testing ? <RefreshCw size={14} className="animate-spin" /> : <TestTube size={14} />}
                Test
              </button>
              <button
                onClick={handleConnect}
                className="flex items-center gap-1 px-3 py-1.5 bg-neutral-700 hover:bg-neutral-600 text-neutral-200 text-sm rounded transition-colors"
              >
                <RefreshCw size={14} />
                {type === 'oauth' ? 'Reconnect' : 'Update'}
              </button>
              <button
                onClick={handleRemove}
                className="flex items-center gap-1 px-3 py-1.5 bg-neutral-700 hover:bg-red-900/50 hover:text-red-400 text-neutral-400 text-sm rounded transition-colors"
              >
                <Trash2 size={14} />
              </button>
            </>
          ) : (
            <button
              onClick={handleConnect}
              className="flex items-center gap-1 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-sm rounded transition-colors"
            >
              {type === 'oauth' ? (
                <>
                  <ExternalLink size={14} />
                  Connect with {name}
                </>
              ) : (
                <>
                  <Key size={14} />
                  Add API Key
                </>
              )}
            </button>
          )}
        </div>
      )}

      {/* Last Validated */}
      {status?.lastValidated && (
        <p className="mt-2 text-xs text-neutral-600">
          Last validated: {new Date(status.lastValidated).toLocaleString()}
        </p>
      )}
    </div>
  );
};

// Timezone options
const TIMEZONES = [
  { value: 'America/New_York', label: 'Eastern Time (ET)' },
  { value: 'America/Chicago', label: 'Central Time (CT)' },
  { value: 'America/Denver', label: 'Mountain Time (MT)' },
  { value: 'America/Los_Angeles', label: 'Pacific Time (PT)' },
  { value: 'America/Phoenix', label: 'Arizona (no DST)' },
  { value: 'America/Anchorage', label: 'Alaska Time' },
  { value: 'Pacific/Honolulu', label: 'Hawaii Time' },
  { value: 'UTC', label: 'UTC' },
  { value: 'Europe/London', label: 'London (GMT/BST)' },
  { value: 'Europe/Paris', label: 'Central European' },
  { value: 'Asia/Tokyo', label: 'Japan' },
];

// Main Settings Component
export const Settings: React.FC = () => {
  const {
    profile, profileLoading, updateProfile, refreshProfile,
    credentialStatus, credentialsLoading, refreshCredentialStatus,
    getServiceStatus
  } = useUserData();
  const { addNotification } = useNotifications();

  const [activeSection, setActiveSection] = useState<'integrations' | 'profile' | 'preferences' | 'data'>('integrations');
  const [editedProfile, setEditedProfile] = useState<Partial<typeof profile>>({});
  const [saving, setSaving] = useState(false);

  // Sync edited profile when profile loads
  useEffect(() => {
    if (profile) {
      setEditedProfile({
        displayName: profile.displayName,
        timezone: profile.timezone,
        theme: profile.theme,
      });
    }
  }, [profile]);

  const handleSaveProfile = async () => {
    if (!editedProfile.displayName?.trim()) {
      addNotification('warning', 'Invalid Name', 'Please enter a display name.');
      return;
    }
    setSaving(true);
    try {
      await updateProfile(editedProfile);
    } catch {
      // Error handled in context
    }
    setSaving(false);
  };

  const sections = [
    { id: 'integrations' as const, label: 'Integrations', icon: Key, description: 'Connect external services' },
    { id: 'profile' as const, label: 'Profile', icon: User, description: 'Your personal settings' },
    { id: 'preferences' as const, label: 'Preferences', icon: Sliders, description: 'Customize behavior' },
    { id: 'data' as const, label: 'Data', icon: Database, description: 'Manage your data' },
  ];

  const integrations = Object.entries(SERVICE_DEFINITIONS).map(([key, def]) => ({
    serviceKey: key,
    ...def,
    status: getServiceStatus(key),
  }));

  return (
    <div className="h-full flex bg-surface-base overflow-hidden">
      {/* Sidebar */}
      <div className="w-56 flex-none bg-surface-dim border-r border-neutral-800 p-4 overflow-y-auto">
        <div className="flex items-center gap-2 mb-6">
          <SettingsIcon size={20} className="text-emerald-500" />
          <h2 className="text-lg font-semibold text-neutral-200">Settings</h2>
        </div>

        <nav className="space-y-1">
          {sections.map((section) => (
            <button
              key={section.id}
              onClick={() => setActiveSection(section.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                activeSection === section.id
                  ? 'bg-emerald-900/20 text-emerald-400 border border-emerald-900/30'
                  : 'text-neutral-400 hover:text-neutral-200 hover:bg-neutral-800/50'
              }`}
            >
              <section.icon size={18} />
              <div className="text-left">
                <div className="font-medium">{section.label}</div>
                <div className="text-xs text-neutral-500">{section.description}</div>
              </div>
            </button>
          ))}
        </nav>

        {/* Integration Status Summary */}
        {credentialStatus && (
          <div className="mt-6 pt-4 border-t border-neutral-800">
            <p className="text-xs text-neutral-500 mb-2 uppercase tracking-wider">Integration Status</p>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-neutral-400">Connected</span>
                <span className="text-emerald-400 font-medium">
                  {credentialStatus.summary.configured}/{credentialStatus.summary.total}
                </span>
              </div>
              <div className="h-2 bg-neutral-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-emerald-600 to-emerald-400 rounded-full transition-all duration-500"
                  style={{
                    width: `${(credentialStatus.summary.configured / credentialStatus.summary.total) * 100}%`
                  }}
                />
              </div>
              {credentialStatus.summary.featuresEnabled.length > 0 && (
                <div className="text-xs text-neutral-500">
                  {credentialStatus.summary.featuresEnabled.length} features enabled
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* Integrations Section */}
        {activeSection === 'integrations' && (
          <div className="max-w-4xl">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-xl font-semibold text-neutral-200 mb-1">External Integrations</h1>
                <p className="text-sm text-neutral-400">
                  Connect external services to unlock additional features in Hydra.
                </p>
              </div>
              <button
                onClick={() => refreshCredentialStatus()}
                disabled={credentialsLoading}
                className="flex items-center gap-2 px-3 py-2 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 text-sm rounded-lg transition-colors"
              >
                <RefreshCw size={16} className={credentialsLoading ? 'animate-spin' : ''} />
                Refresh
              </button>
            </div>

            {credentialsLoading ? (
              <div className="flex items-center justify-center py-12">
                <RefreshCw className="animate-spin text-neutral-500" size={32} />
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {integrations.map((integration) => (
                  <IntegrationCard key={integration.serviceKey} {...integration} />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Profile Section */}
        {activeSection === 'profile' && (
          <div className="max-w-xl">
            <div className="mb-6">
              <h1 className="text-xl font-semibold text-neutral-200 mb-1">Profile</h1>
              <p className="text-sm text-neutral-400">
                Manage your personal information and display preferences.
              </p>
            </div>

            {profileLoading ? (
              <div className="flex items-center justify-center py-12">
                <RefreshCw className="animate-spin text-neutral-500" size={32} />
              </div>
            ) : (
              <div className="space-y-6">
                {/* Display Name */}
                <div className="bg-surface-dim border border-neutral-800 rounded-lg p-4">
                  <label className="flex items-center gap-2 text-sm font-medium text-neutral-300 mb-2">
                    <User size={16} />
                    Display Name
                  </label>
                  <input
                    type="text"
                    value={editedProfile.displayName || ''}
                    onChange={(e) => setEditedProfile({ ...editedProfile, displayName: e.target.value })}
                    className="w-full bg-surface-base border border-neutral-700 rounded-lg px-4 py-2.5 text-neutral-200 focus:border-emerald-500 focus:outline-none"
                    placeholder="Enter your name..."
                  />
                </div>

                {/* Timezone */}
                <div className="bg-surface-dim border border-neutral-800 rounded-lg p-4">
                  <label className="flex items-center gap-2 text-sm font-medium text-neutral-300 mb-2">
                    <Globe size={16} />
                    Timezone
                  </label>
                  <select
                    value={editedProfile.timezone || 'America/Chicago'}
                    onChange={(e) => setEditedProfile({ ...editedProfile, timezone: e.target.value })}
                    className="w-full bg-surface-base border border-neutral-700 rounded-lg px-4 py-2.5 text-neutral-200 focus:border-emerald-500 focus:outline-none"
                  >
                    {TIMEZONES.map(tz => (
                      <option key={tz.value} value={tz.value}>{tz.label}</option>
                    ))}
                  </select>
                </div>

                {/* Theme */}
                <div className="bg-surface-dim border border-neutral-800 rounded-lg p-4">
                  <label className="flex items-center gap-2 text-sm font-medium text-neutral-300 mb-3">
                    <Palette size={16} />
                    Theme
                  </label>
                  <div className="flex gap-3">
                    {(['dark', 'light', 'system'] as const).map((theme) => (
                      <button
                        key={theme}
                        onClick={() => setEditedProfile({ ...editedProfile, theme })}
                        className={`flex-1 px-4 py-2.5 rounded-lg text-sm font-medium capitalize transition-colors ${
                          editedProfile.theme === theme
                            ? 'bg-emerald-600 text-white'
                            : 'bg-surface-base border border-neutral-700 text-neutral-300 hover:border-neutral-600'
                        }`}
                      >
                        {theme}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Save Button */}
                <button
                  onClick={handleSaveProfile}
                  disabled={saving}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-emerald-600 hover:bg-emerald-500 disabled:bg-neutral-700 text-white font-medium rounded-lg transition-colors"
                >
                  {saving ? <RefreshCw size={18} className="animate-spin" /> : <Save size={18} />}
                  Save Profile
                </button>
              </div>
            )}
          </div>
        )}

        {/* Preferences Section */}
        {activeSection === 'preferences' && (
          <div className="max-w-xl">
            <div className="mb-6">
              <h1 className="text-xl font-semibold text-neutral-200 mb-1">Preferences</h1>
              <p className="text-sm text-neutral-400">
                Customize how Hydra behaves and interacts with you.
              </p>
            </div>

            <div className="space-y-4">
              {/* Notifications */}
              <div className="bg-surface-dim border border-neutral-800 rounded-lg p-4">
                <h3 className="font-medium text-neutral-200 mb-4 flex items-center gap-2">
                  <Bell size={18} />
                  Notifications
                </h3>
                <div className="space-y-3">
                  <label className="flex items-center justify-between cursor-pointer">
                    <span className="text-sm text-neutral-300">Enable notifications</span>
                    <input
                      type="checkbox"
                      defaultChecked={true}
                      className="w-5 h-5 rounded bg-surface-base border-neutral-600 text-emerald-500 focus:ring-emerald-500 focus:ring-offset-0"
                    />
                  </label>
                  <label className="flex items-center justify-between cursor-pointer">
                    <span className="text-sm text-neutral-300">Alert sounds</span>
                    <input
                      type="checkbox"
                      defaultChecked={false}
                      className="w-5 h-5 rounded bg-surface-base border-neutral-600 text-emerald-500 focus:ring-emerald-500 focus:ring-offset-0"
                    />
                  </label>
                  <label className="flex items-center justify-between cursor-pointer">
                    <span className="text-sm text-neutral-300">Research updates</span>
                    <input
                      type="checkbox"
                      defaultChecked={true}
                      className="w-5 h-5 rounded bg-surface-base border-neutral-600 text-emerald-500 focus:ring-emerald-500 focus:ring-offset-0"
                    />
                  </label>
                </div>
              </div>

              {/* AI Preferences */}
              <div className="bg-surface-dim border border-neutral-800 rounded-lg p-4">
                <h3 className="font-medium text-neutral-200 mb-4 flex items-center gap-2">
                  <Cpu size={18} />
                  AI Preferences
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm text-neutral-300 mb-2">Preferred Model</label>
                    <select className="w-full bg-surface-base border border-neutral-700 rounded-lg px-4 py-2.5 text-sm text-neutral-200 focus:border-emerald-500 focus:outline-none">
                      <option value="auto">Auto (recommended)</option>
                      <option value="midnight-miqu-70b">Midnight Miqu 70B (best quality)</option>
                      <option value="qwen2.5-7b">Qwen 2.5 7B (fastest)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-neutral-300 mb-2">
                      Temperature: <span className="text-emerald-400">0.7</span>
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      defaultValue="70"
                      className="w-full h-2 bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
                    />
                    <div className="flex justify-between text-xs text-neutral-500 mt-1">
                      <span>Precise</span>
                      <span>Creative</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Dashboard */}
              <div className="bg-surface-dim border border-neutral-800 rounded-lg p-4">
                <h3 className="font-medium text-neutral-200 mb-4 flex items-center gap-2">
                  <Clock size={18} />
                  Dashboard
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm text-neutral-300 mb-2">Default View</label>
                    <select className="w-full bg-surface-base border border-neutral-700 rounded-lg px-4 py-2.5 text-sm text-neutral-200 focus:border-emerald-500 focus:outline-none">
                      <option value="MISSION">Mission (Dashboard)</option>
                      <option value="BRIEFING">Briefing</option>
                      <option value="AGENTS">Agents</option>
                      <option value="CHAT">Chat</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-neutral-300 mb-2">Auto-refresh interval</label>
                    <select className="w-full bg-surface-base border border-neutral-700 rounded-lg px-4 py-2.5 text-sm text-neutral-200 focus:border-emerald-500 focus:outline-none">
                      <option value="15">15 seconds</option>
                      <option value="30">30 seconds</option>
                      <option value="60">1 minute</option>
                      <option value="0">Disabled</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Data Management Section */}
        {activeSection === 'data' && (
          <div className="max-w-xl">
            <div className="mb-6">
              <h1 className="text-xl font-semibold text-neutral-200 mb-1">Data Management</h1>
              <p className="text-sm text-neutral-400">
                Manage your personal data stored in Hydra.
              </p>
            </div>

            <div className="space-y-3">
              {[
                { title: 'Priority Contacts', desc: 'Email contacts for priority filtering', icon: User },
                { title: 'Locations', desc: 'Home, work, and other places', icon: Globe },
                { title: 'News Topics', desc: 'Keywords to monitor in news feeds', icon: Bell },
                { title: 'Schedules', desc: 'Work hours and quiet times', icon: Clock },
                { title: 'Conversation History', desc: 'Chat logs and context', icon: Database },
              ].map((item) => (
                <button
                  key={item.title}
                  className="w-full flex items-center justify-between p-4 bg-surface-dim border border-neutral-800 rounded-lg hover:border-neutral-700 transition-colors group"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-neutral-800 group-hover:bg-neutral-700 transition-colors">
                      <item.icon size={18} className="text-neutral-400" />
                    </div>
                    <div className="text-left">
                      <h3 className="font-medium text-neutral-200">{item.title}</h3>
                      <p className="text-sm text-neutral-500">{item.desc}</p>
                    </div>
                  </div>
                  <ChevronRight size={20} className="text-neutral-600 group-hover:text-neutral-400 transition-colors" />
                </button>
              ))}

              {/* Danger Zone */}
              <div className="mt-8 pt-6 border-t border-neutral-800">
                <h3 className="text-sm font-medium text-red-400 mb-3 flex items-center gap-2">
                  <Shield size={16} />
                  Danger Zone
                </h3>
                <button className="w-full flex items-center justify-between p-4 bg-red-900/10 border border-red-900/30 rounded-lg hover:bg-red-900/20 transition-colors">
                  <div className="text-left">
                    <h3 className="font-medium text-red-400">Clear All Data</h3>
                    <p className="text-sm text-red-400/70">Remove all personal data and reset settings</p>
                  </div>
                  <Trash2 size={20} className="text-red-400" />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Settings;
