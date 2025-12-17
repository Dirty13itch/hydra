import React, { useEffect, useState } from 'react';
import { X, CheckCircle, AlertTriangle, Info, AlertOctagon } from 'lucide-react';
import { Notification } from '../types';

// --- Status Dot ---
interface StatusDotProps {
  status: 'active' | 'idle' | 'thinking' | 'paused' | 'error' | 'online' | 'offline' | 'running' | 'stopped' | 'starting' | 'blocked' | 'done' | 'todo' | 'in-progress';
}

const statusColors: Record<string, string> = {
  active: 'bg-emerald-500 shadow-glow-emerald',
  running: 'bg-emerald-500 shadow-glow-emerald',
  online: 'bg-emerald-500 shadow-glow-emerald',
  idle: 'bg-amber-500',
  starting: 'bg-amber-500 animate-pulse',
  thinking: 'bg-cyan-500 shadow-glow-cyan',
  paused: 'bg-neutral-500',
  stopped: 'bg-neutral-500',
  offline: 'bg-neutral-600',
  error: 'bg-red-500',
  blocked: 'bg-red-500',
  done: 'bg-emerald-500',
  'in-progress': 'bg-cyan-500 animate-pulse',
  todo: 'bg-neutral-600',
};

export const StatusDot: React.FC<StatusDotProps> = ({ status }) => (
  <span className={`h-2.5 w-2.5 rounded-full inline-block ${statusColors[status] || 'bg-neutral-500'} ${['active', 'thinking', 'starting', 'in-progress'].includes(status) ? 'animate-pulse' : ''}`} />
);

// --- Badge ---
interface BadgeProps {
  children: React.ReactNode;
  variant?: 'emerald' | 'cyan' | 'amber' | 'neutral' | 'purple' | 'red';
}

const badgeStyles = {
  emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  cyan: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
  amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  neutral: 'bg-neutral-800 text-neutral-400 border-neutral-700',
  purple: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  red: 'bg-red-500/10 text-red-400 border-red-500/20',
};

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'neutral' }) => (
  <span className={`px-2 py-0.5 rounded text-xs font-mono border ${badgeStyles[variant]}`}>
    {children}
  </span>
);

// --- Card ---
interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  headerAction?: React.ReactNode;
  onClick?: () => void;
}

export const Card: React.FC<CardProps> = ({ children, className = '', title, headerAction, onClick }) => (
  <div 
    className={`bg-surface-default border border-neutral-800 rounded-xl overflow-hidden ${className}`}
    onClick={onClick}
  >
    {(title || headerAction) && (
      <div className="px-4 py-3 border-b border-neutral-800 flex justify-between items-center bg-surface-dim/50">
        {title && <h3 className="font-medium text-neutral-200">{title}</h3>}
        {headerAction && <div>{headerAction}</div>}
      </div>
    )}
    <div className="p-4">
      {children}
    </div>
  </div>
);

// --- ProgressBar ---
interface ProgressBarProps {
  value: number; // 0-100
  colorClass?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({ value, colorClass = 'bg-emerald-500' }) => (
  <div className="h-1.5 w-full bg-neutral-800 rounded-full overflow-hidden">
    <div 
      className={`h-full ${colorClass} transition-all duration-500 ease-out`} 
      style={{ width: `${value}%` }}
    />
  </div>
);

// --- Button ---
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  icon?: React.ReactNode;
}

const buttonVariants = {
  primary: 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm',
  secondary: 'bg-surface-raised border border-neutral-700 hover:bg-surface-highlight text-neutral-200',
  ghost: 'bg-transparent hover:bg-surface-raised text-neutral-400 hover:text-white',
  danger: 'bg-red-900/50 border border-red-900 text-red-400 hover:bg-red-900/80',
};

export const Button: React.FC<ButtonProps> = ({ children, variant = 'primary', size = 'md', icon, className = '', ...props }) => {
  const sizeClasses = size === 'sm' ? 'px-2 py-1 text-xs' : size === 'lg' ? 'px-6 py-3 text-lg' : 'px-4 py-2 text-sm';
  
  return (
    <button 
      className={`inline-flex items-center gap-2 rounded-md font-medium transition-colors ${buttonVariants[variant]} ${sizeClasses} ${className} disabled:opacity-50 disabled:cursor-not-allowed`}
      {...props}
    >
      {icon && <span className="w-4 h-4">{icon}</span>}
      {children}
    </button>
  );
};

// --- Tabs ---
interface TabsProps {
  tabs: { id: string; label: string }[];
  activeTab: string;
  onChange: (id: string) => void;
  className?: string;
  variant?: 'emerald' | 'purple'; // For different domain themes
}

export const Tabs: React.FC<TabsProps> = ({ tabs, activeTab, onChange, className = '', variant = 'emerald' }) => {
  const activeColorClass = variant === 'emerald' ? 'border-emerald-500 text-emerald-400' : 'border-purple-500 text-purple-400';
  
  return (
    <div className={`flex gap-1 border-b border-neutral-800 ${className}`}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === tab.id
              ? activeColorClass
              : 'border-transparent text-neutral-500 hover:text-neutral-300'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
};

// --- Toast ---
interface ToastProps {
  notification: Notification;
  onDismiss: (id: string) => void;
}

const toastIcons = {
  info: <Info size={18} className="text-cyan-400" />,
  success: <CheckCircle size={18} className="text-emerald-400" />,
  warning: <AlertTriangle size={18} className="text-amber-400" />,
  error: <AlertOctagon size={18} className="text-red-400" />,
};

const toastBorders = {
  info: 'border-cyan-500/20 bg-cyan-900/10',
  success: 'border-emerald-500/20 bg-emerald-900/10',
  warning: 'border-amber-500/20 bg-amber-900/10',
  error: 'border-red-500/20 bg-red-900/10',
};

export const Toast: React.FC<ToastProps> = ({ notification, onDismiss }) => {
  return (
    <div className={`flex items-start gap-3 p-4 rounded-lg border backdrop-blur-md shadow-lg min-w-[320px] max-w-[400px] animate-slide-in pointer-events-auto ${toastBorders[notification.type]}`}>
      <div className="mt-0.5 shrink-0">
        {toastIcons[notification.type]}
      </div>
      <div className="flex-1">
        <h4 className="text-sm font-bold text-neutral-200">{notification.title}</h4>
        {notification.message && (
          <p className="text-xs text-neutral-400 mt-1">{notification.message}</p>
        )}
      </div>
      <button 
        onClick={() => onDismiss(notification.id)}
        className="text-neutral-500 hover:text-neutral-300 transition-colors"
      >
        <X size={16} />
      </button>
    </div>
  );
};

interface ToastContainerProps {
  notifications: Notification[];
  removeNotification: (id: string) => void;
}

export const ToastContainer: React.FC<ToastContainerProps> = ({ notifications, removeNotification }) => {
  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 pointer-events-none">
      {notifications.map((n) => (
        <Toast key={n.id} notification={n} onDismiss={removeNotification} />
      ))}
    </div>
  );
};

// --- Modal ---
interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children, className = '' }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />
      
      {/* Content */}
      <div className={`relative bg-surface-base border border-neutral-700 rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden animate-scale-in ${className}`}>
        <div className="px-6 py-4 border-b border-neutral-800 flex justify-between items-center bg-surface-dim">
          <h3 className="text-lg font-mono font-bold text-neutral-200">{title}</h3>
          <button onClick={onClose} className="p-1 hover:bg-neutral-800 rounded text-neutral-400 hover:text-white transition-colors">
            <X size={20} />
          </button>
        </div>
        <div className="overflow-y-auto p-6">
          {children}
        </div>
      </div>
    </div>
  );
};
