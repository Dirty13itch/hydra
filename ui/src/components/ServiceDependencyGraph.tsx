'use client';

import { useState, useMemo } from 'react';

interface ServiceNode {
  id: string;
  name: string;
  category: string;
  x: number;
  y: number;
}

interface ServiceDependency {
  from: string;
  to: string;
  type: 'hard' | 'soft';  // hard = required, soft = optional/uses
}

interface ServiceDependencyGraphProps {
  services: Record<string, string>;
  onServiceClick?: (serviceName: string) => void;
}

// Define service dependencies based on Hydra architecture
const dependencies: ServiceDependency[] = [
  // Letta (AI agent) dependencies
  { from: 'letta', to: 'ollama', type: 'hard' },
  { from: 'letta', to: 'qdrant', type: 'hard' },
  // LiteLLM proxy
  { from: 'litellm', to: 'ollama', type: 'hard' },
  // Open WebUI
  { from: 'open-webui', to: 'ollama', type: 'hard' },
  { from: 'openwebui', to: 'ollama', type: 'hard' },
  // Monitoring stack
  { from: 'grafana', to: 'prometheus', type: 'hard' },
  { from: 'alertmanager', to: 'prometheus', type: 'hard' },
  // Media
  { from: 'tautulli', to: 'plex', type: 'hard' },
  // N8N automation
  { from: 'n8n', to: 'letta', type: 'soft' },
  { from: 'n8n', to: 'litellm', type: 'soft' },
  // Hydra MCP
  { from: 'hydra-mcp', to: 'prometheus', type: 'soft' },
  { from: 'hydra-mcp', to: 'ollama', type: 'soft' },
];

// Category positions (radial layout)
const categoryPositions: Record<string, { angle: number; radius: number }> = {
  'Core': { angle: 270, radius: 0 },
  'AI': { angle: 0, radius: 110 },
  'Monitoring': { angle: 120, radius: 110 },
  'Automation': { angle: 180, radius: 110 },
  'Infrastructure': { angle: 240, radius: 100 },
  'Media': { angle: 300, radius: 110 },
};

const categoryColors: Record<string, string> = {
  'Core': '#0ff',
  'AI': '#ff00ff',
  'Monitoring': '#0ff',
  'Automation': '#ffcc00',
  'Infrastructure': '#00ff88',
  'Media': '#a855f7',
};

// Service to category mapping
const serviceCategories: Record<string, string> = {
  'hydra-mcp': 'Core',
  'prometheus': 'Monitoring',
  'alertmanager': 'Monitoring',
  'grafana': 'Monitoring',
  'uptime-kuma': 'Monitoring',
  'letta': 'AI',
  'ollama': 'AI',
  'litellm': 'AI',
  'qdrant': 'AI',
  'open-webui': 'AI',
  'openwebui': 'AI',
  'comfyui': 'AI',
  'a1111': 'AI',
  'invokeai': 'AI',
  'whisper': 'AI',
  'n8n': 'Automation',
  'watchtower': 'Infrastructure',
  'traefik': 'Infrastructure',
  'plex': 'Media',
  'tautulli': 'Media',
};

export function ServiceDependencyGraph({ services, onServiceClick }: ServiceDependencyGraphProps) {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  // Build nodes from services
  const nodes = useMemo(() => {
    const serviceList = Object.keys(services);
    const nodeMap: Record<string, ServiceNode> = {};

    // Group services by category
    const byCategory: Record<string, string[]> = {};
    serviceList.forEach(service => {
      const category = serviceCategories[service.toLowerCase()] || serviceCategories[service] || 'Infrastructure';
      if (!byCategory[category]) byCategory[category] = [];
      byCategory[category].push(service);
    });

    // Position nodes in a radial layout
    const centerX = 160;
    const centerY = 140;

    Object.entries(byCategory).forEach(([category, categoryServices]) => {
      const pos = categoryPositions[category] || { angle: 0, radius: 100 };
      const baseAngle = (pos.angle * Math.PI) / 180;

      categoryServices.forEach((service, idx) => {
        // Spread services in the category
        const spread = categoryServices.length > 1 ? 0.4 : 0;
        const angleOffset = (idx - (categoryServices.length - 1) / 2) * spread;
        const angle = baseAngle + angleOffset;

        nodeMap[service] = {
          id: service,
          name: service,
          category,
          x: centerX + Math.cos(angle) * pos.radius,
          y: centerY + Math.sin(angle) * pos.radius,
        };
      });
    });

    return nodeMap;
  }, [services]);

  // Get status color for a service
  const getStatusColor = (service: string): string => {
    const status = services[service];
    if (status === 'up') return '#00ff88';
    if (status === 'down') return '#ff4444';
    return '#666';
  };

  // Filter dependencies to only show existing services
  const visibleDependencies = useMemo(() => {
    return dependencies.filter(dep =>
      nodes[dep.from] && nodes[dep.to]
    );
  }, [nodes]);

  // Get connections for hovered node
  const hoveredConnections = useMemo(() => {
    if (!hoveredNode) return new Set<string>();
    const connected = new Set<string>();
    visibleDependencies.forEach(dep => {
      if (dep.from === hoveredNode) connected.add(dep.to);
      if (dep.to === hoveredNode) connected.add(dep.from);
    });
    return connected;
  }, [hoveredNode, visibleDependencies]);

  if (!isExpanded) {
    return (
      <div className="panel">
        <button
          onClick={() => setIsExpanded(true)}
          className="panel-header w-full flex items-center justify-between cursor-pointer hover:bg-hydra-gray/20 transition-colors"
        >
          <div className="flex items-center gap-2">
            <span className="text-hydra-magenta">&#9632;</span>
            <span>Service Dependencies</span>
            <span className="text-xs text-gray-500">
              ({visibleDependencies.length} connections)
            </span>
          </div>
          <svg
            className="w-4 h-4 text-gray-500 -rotate-90"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>
    );
  }

  return (
    <div className="panel">
      <button
        onClick={() => setIsExpanded(false)}
        className="panel-header w-full flex items-center justify-between cursor-pointer hover:bg-hydra-gray/20 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-hydra-magenta">&#9632;</span>
          <span>Service Dependencies</span>
        </div>
        <svg
          className="w-4 h-4 text-gray-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      <div className="p-2">
        <svg
          viewBox="0 0 320 280"
          className="w-full h-auto"
          style={{ maxHeight: '300px' }}
        >
          {/* Dependency lines */}
          {visibleDependencies.map((dep, idx) => {
            const from = nodes[dep.from];
            const to = nodes[dep.to];
            if (!from || !to) return null;

            const isHighlighted = hoveredNode === dep.from || hoveredNode === dep.to;
            const isDimmed = hoveredNode && !isHighlighted;

            return (
              <line
                key={`${dep.from}-${dep.to}-${idx}`}
                x1={from.x}
                y1={from.y}
                x2={to.x}
                y2={to.y}
                stroke={isHighlighted ? '#0ff' : isDimmed ? '#333' : '#444'}
                strokeWidth={dep.type === 'hard' ? 2 : 1}
                strokeDasharray={dep.type === 'soft' ? '4,4' : undefined}
                opacity={isDimmed ? 0.3 : 0.7}
                className="transition-all duration-200"
              />
            );
          })}

          {/* Service nodes */}
          {Object.values(nodes).map(node => {
            const isHovered = hoveredNode === node.id;
            const isConnected = hoveredConnections.has(node.id);
            const isDimmed = hoveredNode && !isHovered && !isConnected;
            const statusColor = getStatusColor(node.id);
            const categoryColor = categoryColors[node.category] || '#666';

            return (
              <g
                key={node.id}
                transform={`translate(${node.x}, ${node.y})`}
                className="cursor-pointer"
                onMouseEnter={() => setHoveredNode(node.id)}
                onMouseLeave={() => setHoveredNode(null)}
                onClick={() => onServiceClick?.(node.id)}
                style={{ opacity: isDimmed ? 0.3 : 1 }}
              >
                {/* Glow effect for hovered */}
                {isHovered && (
                  <circle
                    r={16}
                    fill={categoryColor}
                    opacity={0.3}
                    className="animate-pulse"
                  />
                )}

                {/* Node circle */}
                <circle
                  r={isHovered ? 12 : 10}
                  fill="#0a0a0a"
                  stroke={isHovered ? categoryColor : statusColor}
                  strokeWidth={2}
                  className="transition-all duration-200"
                />

                {/* Status indicator */}
                <circle
                  r={3}
                  fill={statusColor}
                  cx={6}
                  cy={-6}
                />

                {/* Label */}
                <text
                  y={22}
                  textAnchor="middle"
                  fill={isHovered ? '#fff' : '#888'}
                  fontSize="8"
                  fontFamily="monospace"
                  className="select-none"
                >
                  {node.name.length > 10 ? node.name.slice(0, 10) + '..' : node.name}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Legend */}
        <div className="flex flex-wrap gap-3 justify-center mt-2 text-[10px]">
          {Object.entries(categoryColors).map(([cat, color]) => (
            <div key={cat} className="flex items-center gap-1">
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: color }}
              />
              <span className="text-gray-500">{cat}</span>
            </div>
          ))}
        </div>

        {/* Hovered info */}
        {hoveredNode && (
          <div className="mt-2 p-2 bg-hydra-gray/20 rounded text-xs text-center">
            <span className="text-white font-mono">{hoveredNode}</span>
            <span className="text-gray-500 ml-2">
              {visibleDependencies.filter(d => d.from === hoveredNode).length} depends on /
              {visibleDependencies.filter(d => d.to === hoveredNode).length} used by
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
