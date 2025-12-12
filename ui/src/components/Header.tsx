'use client';

import { useState, useEffect } from 'react';
import { useTheme } from './ThemeProvider';

interface HeaderProps {
  version?: string;
  uptime?: number;
  refreshInterval?: number;
  lastUpdate?: Date;
}

export function Header({ version, uptime, refreshInterval = 5000, lastUpdate }: HeaderProps) {
  const [secondsAgo, setSecondsAgo] = useState(0);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    if (!lastUpdate) return;

    const updateSecondsAgo = () => {
      const diff = Math.floor((Date.now() - lastUpdate.getTime()) / 1000);
      setSecondsAgo(diff);
    };

    updateSecondsAgo();
    const interval = setInterval(updateSecondsAgo, 1000);
    return () => clearInterval(interval);
  }, [lastUpdate]);

  const formatUptime = (seconds?: number) => {
    if (!seconds) return '--';
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${mins}m`;
  };

  const quickLinks = [
    { href: 'http://192.168.1.244:3003', label: 'Grafana', color: 'green', title: 'Open Grafana Dashboards' },
    { href: 'http://192.168.1.244:3004', label: 'Uptime', color: 'cyan', title: 'Open Uptime Kuma' },
    { href: 'http://192.168.1.244:3001', label: 'AI Chat', color: 'magenta', title: 'Open AI Chat (Open WebUI)' },
    { href: 'http://192.168.1.244:5678', label: 'n8n', color: 'blue', title: 'Open n8n Workflows' },
  ];

  const getLinkStyle = (color: string) => {
    const colors: Record<string, { bg: string; text: string }> = {
      green: { bg: 'rgba(0, 255, 136, 0.15)', text: 'var(--hydra-green)' },
      cyan: { bg: 'rgba(0, 255, 255, 0.15)', text: 'var(--hydra-cyan)' },
      magenta: { bg: 'rgba(255, 0, 255, 0.15)', text: 'var(--hydra-magenta)' },
      blue: { bg: 'rgba(96, 165, 250, 0.15)', text: '#60a5fa' },
    };
    return colors[color] || colors.cyan;
  };

  return (
    <header className="border-b border-hydra-cyan/30 bg-hydra-darker/80 backdrop-blur-sm sticky top-0 z-40" style={{ backgroundColor: 'var(--hydra-bg-secondary)', borderColor: 'var(--hydra-border)' }}>
      <div className="container mx-auto px-4 py-3 md:py-4">
        <div className="flex items-center justify-between">
          {/* Logo and Title */}
          <div className="flex items-center gap-2 md:gap-4">
            <h1 className="text-xl md:text-2xl font-bold tracking-wider">
              <span className="text-hydra-cyan neon-cyan" style={{ color: 'var(--hydra-cyan)' }}>HYDRA</span>
              <span className="text-sm md:text-lg ml-1 md:ml-2 hidden sm:inline" style={{ color: 'var(--hydra-text-muted)' }}>CONTROL PLANE</span>
              <span className="text-sm ml-1 sm:hidden" style={{ color: 'var(--hydra-text-muted)' }}>CP</span>
            </h1>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden lg:flex items-center gap-6 text-sm">
            <div className="flex items-center gap-2">
              <span style={{ color: 'var(--hydra-text-muted)' }}>MCP</span>
              <span style={{ color: 'var(--hydra-green)' }}>{version || '--'}</span>
            </div>
            <div className="flex items-center gap-2">
              <span style={{ color: 'var(--hydra-text-muted)' }}>UPTIME</span>
              <span style={{ color: 'var(--hydra-cyan)' }}>{formatUptime(uptime)}</span>
            </div>
            <div className="flex items-center gap-2 px-2 py-1 rounded border" style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'rgba(0, 255, 136, 0.3)' }}>
              <div className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: 'var(--hydra-green)', boxShadow: '0 0 10px var(--hydra-green)' }} />
              <span className="text-xs font-medium" style={{ color: 'var(--hydra-green)' }}>LIVE</span>
              <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>{refreshInterval / 1000}s</span>
              {lastUpdate && (
                <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                  {secondsAgo < 60 ? `${secondsAgo}s ago` : `${Math.floor(secondsAgo / 60)}m ago`}
                </span>
              )}
            </div>

            {/* Quick Links */}
            <div className="flex items-center gap-1 border-l pl-4" style={{ borderColor: 'var(--hydra-border)' }}>
              {quickLinks.map((link) => {
                const style = getLinkStyle(link.color);
                return (
                  <a
                    key={link.label}
                    href={link.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-2 py-1 rounded text-xs transition-colors hover:opacity-80"
                    style={{ backgroundColor: style.bg, color: style.text }}
                    title={link.title}
                  >
                    {link.label}
                  </a>
                );
              })}
            </div>

            {/* Theme Toggle Button */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg border transition-all hover:scale-105"
              style={{
                backgroundColor: 'var(--hydra-bg)',
                borderColor: 'var(--hydra-border)',
                color: 'var(--hydra-cyan)'
              }}
              title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {theme === 'dark' ? (
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="5"/>
                  <line x1="12" y1="1" x2="12" y2="3"/>
                  <line x1="12" y1="21" x2="12" y2="23"/>
                  <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
                  <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
                  <line x1="1" y1="12" x2="3" y2="12"/>
                  <line x1="21" y1="12" x2="23" y2="12"/>
                  <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
                  <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                </svg>
              )}
            </button>
          </div>

          {/* Mobile Status + Menu */}
          <div className="flex lg:hidden items-center gap-2">
            {/* Live indicator */}
            <div className="flex items-center gap-1 px-2 py-1 rounded border" style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'rgba(0, 255, 136, 0.3)' }}>
              <div className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: 'var(--hydra-green)', boxShadow: '0 0 10px var(--hydra-green)' }} />
              <span className="text-xs font-medium" style={{ color: 'var(--hydra-green)' }}>LIVE</span>
            </div>

            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg border transition-all min-w-[44px] min-h-[44px] flex items-center justify-center"
              style={{
                backgroundColor: 'var(--hydra-bg)',
                borderColor: 'var(--hydra-border)',
                color: 'var(--hydra-cyan)'
              }}
            >
              {theme === 'dark' ? (
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="5"/>
                  <line x1="12" y1="1" x2="12" y2="3"/>
                  <line x1="12" y1="21" x2="12" y2="23"/>
                  <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
                  <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
                  <line x1="1" y1="12" x2="3" y2="12"/>
                  <line x1="21" y1="12" x2="23" y2="12"/>
                  <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
                  <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                </svg>
              )}
            </button>

            {/* Hamburger Menu Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg border transition-all min-w-[44px] min-h-[44px] flex items-center justify-center"
              style={{
                backgroundColor: 'var(--hydra-bg)',
                borderColor: 'var(--hydra-border)',
                color: 'var(--hydra-cyan)'
              }}
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? (
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="3" y1="12" x2="21" y2="12"/>
                  <line x1="3" y1="6" x2="21" y2="6"/>
                  <line x1="3" y1="18" x2="21" y2="18"/>
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* Mobile Menu Dropdown */}
        {mobileMenuOpen && (
          <div className="lg:hidden mt-4 pt-4 border-t animate-in slide-in-from-top duration-200" style={{ borderColor: 'var(--hydra-border)' }}>
            {/* Status Info */}
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="p-3 rounded-lg border" style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}>
                <div className="text-xs uppercase tracking-wider mb-1" style={{ color: 'var(--hydra-text-muted)' }}>MCP Version</div>
                <div className="text-sm font-medium" style={{ color: 'var(--hydra-green)' }}>{version || '--'}</div>
              </div>
              <div className="p-3 rounded-lg border" style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}>
                <div className="text-xs uppercase tracking-wider mb-1" style={{ color: 'var(--hydra-text-muted)' }}>Uptime</div>
                <div className="text-sm font-medium" style={{ color: 'var(--hydra-cyan)' }}>{formatUptime(uptime)}</div>
              </div>
            </div>

            {/* Quick Links */}
            <div className="text-xs uppercase tracking-wider mb-2" style={{ color: 'var(--hydra-text-muted)' }}>Quick Links</div>
            <div className="grid grid-cols-2 gap-2">
              {quickLinks.map((link) => {
                const style = getLinkStyle(link.color);
                return (
                  <a
                    key={link.label}
                    href={link.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-3 rounded-lg text-sm font-medium transition-colors hover:opacity-80 text-center min-h-[48px] flex items-center justify-center"
                    style={{ backgroundColor: style.bg, color: style.text }}
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    {link.label}
                  </a>
                );
              })}
            </div>

            {/* Last Update */}
            {lastUpdate && (
              <div className="mt-4 text-center text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                Last update: {secondsAgo < 60 ? `${secondsAgo}s ago` : `${Math.floor(secondsAgo / 60)}m ago`}
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
