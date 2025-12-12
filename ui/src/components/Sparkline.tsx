'use client';

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  fillColor?: string;
  showDots?: boolean;
  className?: string;
}

export function Sparkline({
  data,
  width = 80,
  height = 24,
  color = 'var(--hydra-cyan)',
  fillColor,
  showDots = false,
  className = '',
}: SparklineProps) {
  if (!data || data.length < 2) {
    return (
      <div
        className={className}
        style={{ width, height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
      >
        <span className="text-gray-600 text-xs">--</span>
      </div>
    );
  }

  const padding = 2;
  const effectiveWidth = width - padding * 2;
  const effectiveHeight = height - padding * 2;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const points = data.map((value, index) => {
    const x = padding + (index / (data.length - 1)) * effectiveWidth;
    const y = padding + effectiveHeight - ((value - min) / range) * effectiveHeight;
    return { x, y };
  });

  const pathD = points
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`)
    .join(' ');

  // Area fill path
  const areaD = fillColor
    ? `${pathD} L ${points[points.length - 1].x} ${height - padding} L ${padding} ${height - padding} Z`
    : '';

  // Calculate trend
  const firstHalf = data.slice(0, Math.floor(data.length / 2));
  const secondHalf = data.slice(Math.floor(data.length / 2));
  const firstAvg = firstHalf.reduce((a, b) => a + b, 0) / firstHalf.length;
  const secondAvg = secondHalf.reduce((a, b) => a + b, 0) / secondHalf.length;
  const trend = secondAvg > firstAvg ? 'up' : secondAvg < firstAvg ? 'down' : 'stable';

  return (
    <div className={`flex items-center gap-1 ${className}`}>
      <svg width={width} height={height} className="overflow-visible">
        {fillColor && (
          <path
            d={areaD}
            fill={fillColor}
            opacity={0.2}
          />
        )}
        <path
          d={pathD}
          fill="none"
          stroke={color}
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {showDots && points.map((point, index) => (
          <circle
            key={index}
            cx={point.x}
            cy={point.y}
            r={index === points.length - 1 ? 2.5 : 1.5}
            fill={index === points.length - 1 ? color : 'transparent'}
            stroke={color}
            strokeWidth={1}
          />
        ))}
      </svg>
      <span className={`text-[10px] ${
        trend === 'up' ? 'text-hydra-green' :
        trend === 'down' ? 'text-hydra-red' :
        'text-gray-500'
      }`}>
        {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'}
      </span>
    </div>
  );
}

// UptimeSparkline - shows service uptime history as colored bars
interface UptimeSparklineProps {
  history: boolean[];
  width?: number;
  height?: number;
}

export function UptimeSparkline({
  history,
  width = 50,
  height = 10,
}: UptimeSparklineProps) {
  if (!history || history.length === 0) {
    return (
      <div style={{ width, height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span className="text-gray-600 text-xs">--</span>
      </div>
    );
  }

  const barWidth = Math.max(2, (width - (history.length - 1)) / history.length);
  const gap = 1;

  return (
    <svg width={width} height={height} className="overflow-visible">
      {history.map((isUp, index) => (
        <rect
          key={index}
          x={index * (barWidth + gap)}
          y={0}
          width={barWidth}
          height={height}
          rx={1}
          fill={isUp ? 'var(--hydra-green)' : 'var(--hydra-red)'}
          opacity={0.8}
        />
      ))}
    </svg>
  );
}
