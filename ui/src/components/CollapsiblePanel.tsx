'use client';

import { ReactNode } from 'react';

interface CollapsiblePanelProps {
  title: string;
  icon?: ReactNode;
  iconColor?: string;
  isCollapsed: boolean;
  onToggle: () => void;
  children: ReactNode;
  headerRight?: ReactNode;
  className?: string;
}

export function CollapsiblePanel({
  title,
  icon,
  iconColor = 'text-hydra-cyan',
  isCollapsed,
  onToggle,
  children,
  headerRight,
  className = '',
}: CollapsiblePanelProps) {
  return (
    <div className={`panel overflow-hidden ${className}`}>
      <button
        onClick={onToggle}
        className="panel-header w-full flex items-center justify-between cursor-pointer hover:bg-hydra-gray/20 transition-colors"
      >
        <div className="flex items-center gap-2">
          {icon ? (
            <span className={iconColor}>{icon}</span>
          ) : (
            <span className={iconColor}>&#9632;</span>
          )}
          <span>{title}</span>
        </div>
        <div className="flex items-center gap-2">
          {headerRight}
          <svg
            className={`w-4 h-4 text-gray-500 transition-transform duration-200 ${isCollapsed ? '-rotate-90' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      <div
        className={`transition-all duration-200 overflow-hidden ${
          isCollapsed ? 'max-h-0' : 'max-h-[2000px]'
        }`}
      >
        {children}
      </div>
    </div>
  );
}
