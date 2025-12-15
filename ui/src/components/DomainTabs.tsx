'use client';

import { useState, useCallback } from 'react';

export type Domain = 'overview' | 'inference' | 'storage' | 'automation' | 'creative' | 'home' | 'intelligence';

interface DomainTabsProps {
  activeDomain: Domain;
  onDomainChange: (domain: Domain) => void;
}

const DOMAINS: { id: Domain; label: string; icon: string; color: string; description: string }[] = [
  { id: 'overview', label: 'Overview', icon: '📊', color: 'var(--hydra-cyan)', description: 'Cluster overview and quick actions' },
  { id: 'inference', label: 'Inference', icon: '🧠', color: 'var(--hydra-magenta)', description: 'Models, VRAM, and inference metrics' },
  { id: 'storage', label: 'Storage', icon: '💾', color: 'var(--hydra-yellow)', description: 'Pools, capacity, and backups' },
  { id: 'automation', label: 'Automation', icon: '⚙️', color: 'var(--hydra-green)', description: 'Workflows, agents, and alerts' },
  { id: 'creative', label: 'Creative', icon: '🎨', color: 'var(--hydra-magenta)', description: 'Image gen, TTS, and characters' },
  { id: 'intelligence', label: 'Intelligence', icon: '🔍', color: 'var(--hydra-purple)', description: 'Research, knowledge, and discovery' },
  { id: 'home', label: 'Home', icon: '🏠', color: 'var(--hydra-cyan)', description: 'Devices, scenes, and automation' },
];

export function DomainTabs({ activeDomain, onDomainChange }: DomainTabsProps) {
  return (
    <div
      className="border-b px-4 flex items-center gap-1 overflow-x-auto"
      style={{ borderColor: 'var(--hydra-border)' }}
    >
      {DOMAINS.map((domain) => {
        const isActive = domain.id === activeDomain;
        return (
          <button
            key={domain.id}
            onClick={() => onDomainChange(domain.id)}
            className={`
              flex items-center gap-2 px-4 py-3 text-sm font-medium transition-all
              border-b-2 whitespace-nowrap
              ${isActive ? '' : 'opacity-60 hover:opacity-100'}
            `}
            style={{
              borderColor: isActive ? domain.color : 'transparent',
              color: isActive ? domain.color : 'var(--hydra-text)',
            }}
            title={domain.description}
          >
            <span className="text-base">{domain.icon}</span>
            <span className="hidden sm:inline">{domain.label}</span>
          </button>
        );
      })}
    </div>
  );
}

// Domain view wrapper for consistent styling
interface DomainViewProps {
  children: React.ReactNode;
  title: string;
  icon: string;
  description?: string;
  actions?: React.ReactNode;
}

export function DomainView({ children, title, icon, description, actions }: DomainViewProps) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: 'var(--hydra-border)' }}>
        <div className="flex items-center gap-3">
          <span className="text-2xl">{icon}</span>
          <div>
            <h2 className="text-lg font-bold" style={{ color: 'var(--hydra-text)' }}>{title}</h2>
            {description && (
              <p className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>{description}</p>
            )}
          </div>
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
      <div className="flex-1 overflow-auto p-4">
        {children}
      </div>
    </div>
  );
}
