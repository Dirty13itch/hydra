'use client';

interface StatusIndicatorProps {
  status: 'online' | 'offline' | 'warning' | 'unknown';
  label?: string;
  pulse?: boolean;
}

export function StatusIndicator({ status, label, pulse = true }: StatusIndicatorProps) {
  const colors = {
    online: 'bg-hydra-green',
    offline: 'bg-hydra-red',
    warning: 'bg-hydra-yellow',
    unknown: 'bg-gray-500',
  };

  const glows = {
    online: 'shadow-[0_0_10px_rgba(0,255,136,0.8)]',
    offline: 'shadow-[0_0_10px_rgba(255,51,102,0.8)]',
    warning: 'shadow-[0_0_10px_rgba(255,204,0,0.8)]',
    unknown: '',
  };

  return (
    <div className="flex items-center gap-2">
      <div
        className={`w-3 h-3 rounded-full ${colors[status]} ${glows[status]} ${
          pulse && status === 'online' ? 'animate-pulse-slow' : ''
        }`}
      />
      {label && (
        <span className="text-sm text-gray-300 uppercase tracking-wider">{label}</span>
      )}
    </div>
  );
}
