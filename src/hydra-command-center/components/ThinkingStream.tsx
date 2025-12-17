import React, { useEffect, useRef } from 'react';
import { Brain, Wrench, Eye, CheckCircle, ChevronDown, ChevronUp } from 'lucide-react';

interface ThinkingStep {
  step_id: string;
  timestamp: string;
  content: string;
  step_type: string;
}

interface ThinkingStreamProps {
  steps: ThinkingStep[];
  agentName?: string;
  isExpanded?: boolean;
  onToggle?: () => void;
  maxHeight?: string;
  showHeader?: boolean;
}

const StepIcon: React.FC<{ type: string }> = ({ type }) => {
  switch (type) {
    case 'reasoning':
      return <Brain size={14} className="text-purple-400" />;
    case 'tool_call':
      return <Wrench size={14} className="text-amber-400" />;
    case 'observation':
      return <Eye size={14} className="text-cyan-400" />;
    case 'conclusion':
      return <CheckCircle size={14} className="text-emerald-400" />;
    default:
      return <Brain size={14} className="text-neutral-400" />;
  }
};

const StepTypeLabel: React.FC<{ type: string }> = ({ type }) => {
  const colors: Record<string, string> = {
    reasoning: 'text-purple-400 bg-purple-500/10',
    tool_call: 'text-amber-400 bg-amber-500/10',
    observation: 'text-cyan-400 bg-cyan-500/10',
    conclusion: 'text-emerald-400 bg-emerald-500/10',
  };

  const color = colors[type] || 'text-neutral-400 bg-neutral-500/10';

  return (
    <span className={`text-[10px] uppercase font-mono px-1.5 py-0.5 rounded ${color}`}>
      {type.replace('_', ' ')}
    </span>
  );
};

const formatTimestamp = (ts: string): string => {
  try {
    const date = new Date(ts);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return ts;
  }
};

export const ThinkingStream: React.FC<ThinkingStreamProps> = ({
  steps,
  agentName,
  isExpanded = true,
  onToggle,
  maxHeight = '300px',
  showHeader = true,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new steps arrive
  useEffect(() => {
    if (containerRef.current && isExpanded) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [steps, isExpanded]);

  if (!isExpanded && onToggle) {
    return (
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-3 bg-neutral-900/50 border border-neutral-800 rounded-lg hover:bg-neutral-800/50 transition-colors"
      >
        <div className="flex items-center gap-2 text-sm text-neutral-400">
          <Brain size={16} className="text-purple-400" />
          <span>Thinking Stream</span>
          {steps.length > 0 && (
            <span className="text-xs text-neutral-500">({steps.length} steps)</span>
          )}
        </div>
        <ChevronDown size={16} className="text-neutral-500" />
      </button>
    );
  }

  return (
    <div className="border border-neutral-800 rounded-lg overflow-hidden bg-neutral-900/30">
      {/* Header */}
      {showHeader && (
        <div
          className={`flex items-center justify-between p-3 bg-neutral-900 border-b border-neutral-800 ${onToggle ? 'cursor-pointer hover:bg-neutral-800/50' : ''}`}
          onClick={onToggle}
        >
          <div className="flex items-center gap-2">
            <Brain size={16} className="text-purple-400" />
            <span className="text-sm font-medium text-neutral-300">
              {agentName ? `${agentName} Thinking` : 'Thinking Stream'}
            </span>
            <span className="text-xs text-neutral-500 font-mono">({steps.length} steps)</span>
          </div>
          {onToggle && <ChevronUp size={16} className="text-neutral-500" />}
        </div>
      )}

      {/* Steps */}
      <div
        ref={containerRef}
        className="overflow-y-auto p-3 space-y-3"
        style={{ maxHeight }}
      >
        {steps.length === 0 ? (
          <div className="text-center py-6 text-neutral-600">
            <Brain size={24} className="mx-auto mb-2 opacity-50" />
            <p className="text-sm">No thinking steps yet</p>
            <p className="text-xs">Steps will appear as the agent processes</p>
          </div>
        ) : (
          steps.map((step, index) => (
            <div
              key={step.step_id}
              className="relative pl-6 animate-fade-in"
            >
              {/* Timeline */}
              <div className="absolute left-0 top-0 bottom-0 flex flex-col items-center">
                <div className="w-4 h-4 rounded-full bg-neutral-800 border border-neutral-700 flex items-center justify-center">
                  <StepIcon type={step.step_type} />
                </div>
                {index < steps.length - 1 && (
                  <div className="flex-1 w-px bg-neutral-800 mt-1" />
                )}
              </div>

              {/* Content */}
              <div className="ml-2">
                <div className="flex items-center gap-2 mb-1">
                  <StepTypeLabel type={step.step_type} />
                  <span className="text-[10px] text-neutral-600 font-mono">
                    {formatTimestamp(step.timestamp)}
                  </span>
                </div>
                <p className="text-sm text-neutral-300 leading-relaxed whitespace-pre-wrap">
                  {step.content}
                </p>
              </div>
            </div>
          ))
        )}

        {/* Live indicator if there are recent steps */}
        {steps.length > 0 && (
          <div className="flex items-center gap-2 text-xs text-neutral-500 pt-2">
            <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
            <span>Live stream active</span>
          </div>
        )}
      </div>
    </div>
  );
};

// Compact version for embedding in agent cards
export const ThinkingStreamCompact: React.FC<{
  steps: ThinkingStep[];
  limit?: number;
}> = ({ steps, limit = 3 }) => {
  const recentSteps = steps.slice(-limit);

  if (recentSteps.length === 0) {
    return null;
  }

  return (
    <div className="mt-3 pt-3 border-t border-neutral-800/50">
      <div className="flex items-center gap-2 mb-2">
        <Brain size={12} className="text-purple-400" />
        <span className="text-[10px] uppercase font-mono text-neutral-500">Latest Thinking</span>
      </div>
      <div className="space-y-1.5">
        {recentSteps.map((step) => (
          <div key={step.step_id} className="flex items-start gap-2">
            <StepIcon type={step.step_type} />
            <p className="text-xs text-neutral-400 line-clamp-2">{step.content}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ThinkingStream;
