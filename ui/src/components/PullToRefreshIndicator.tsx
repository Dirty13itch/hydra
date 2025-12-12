'use client';

interface PullToRefreshIndicatorProps {
  pullDistance: number;
  isRefreshing: boolean;
  threshold: number;
}

export function PullToRefreshIndicator({
  pullDistance,
  isRefreshing,
  threshold,
}: PullToRefreshIndicatorProps) {
  if (pullDistance <= 0 && !isRefreshing) return null;

  const progress = Math.min(pullDistance / threshold, 1);
  const rotation = progress * 360;
  const isTriggered = pullDistance >= threshold;

  return (
    <div
      className="fixed left-0 right-0 flex justify-center pointer-events-none z-50 transition-transform duration-200"
      style={{
        top: Math.max(0, pullDistance - 50),
        transform: `translateY(${Math.min(pullDistance, threshold)}px)`,
      }}
    >
      <div
        className={`
          flex items-center justify-center w-10 h-10 rounded-full
          bg-hydra-darker border border-hydra-cyan/30
          shadow-lg shadow-hydra-cyan/20
          transition-all duration-200
          ${isTriggered ? 'scale-110' : ''}
        `}
      >
        {isRefreshing ? (
          // Spinning loader
          <svg
            className="w-5 h-5 text-hydra-cyan animate-spin"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="3"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        ) : (
          // Arrow that rotates as you pull
          <svg
            className={`w-5 h-5 transition-all duration-150 ${isTriggered ? 'text-hydra-green' : 'text-hydra-cyan'}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            style={{ transform: `rotate(${rotation}deg)` }}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 14l-7 7m0 0l-7-7m7 7V3"
            />
          </svg>
        )}
      </div>

      {/* Pull instruction text */}
      {pullDistance > 20 && !isRefreshing && (
        <div
          className={`
            absolute top-12 text-xs whitespace-nowrap
            transition-colors duration-200
            ${isTriggered ? 'text-hydra-green' : 'text-gray-500'}
          `}
        >
          {isTriggered ? 'Release to refresh' : 'Pull to refresh'}
        </div>
      )}
    </div>
  );
}
