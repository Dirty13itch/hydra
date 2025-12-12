'use client';

interface StoragePool {
  name: string;
  type: string;
  total_bytes: number;
  used_bytes: number;
  free_bytes: number;
  percent_used: number;
  disk_count?: number;
  status: string;
}

interface StoragePoolsData {
  timestamp: string;
  pools: StoragePool[];
  summary: {
    total_bytes: number;
    used_bytes: number;
    free_bytes: number;
    percent_used: number;
  };
}

interface StoragePoolsProps {
  data: StoragePoolsData | null;
  isCollapsed?: boolean;
  onToggle?: () => void;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export function StoragePools({ data, isCollapsed = false, onToggle }: StoragePoolsProps) {
  if (!data || !data.pools || data.pools.length === 0) {
    return null;
  }

  return (
    <div className="panel">
      <button
        onClick={onToggle}
        className="panel-header w-full flex items-center justify-between cursor-pointer hover:bg-hydra-gray/20 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-hydra-yellow">&#9632;</span>
          <span>Storage Pools</span>
          <span className="text-xs text-gray-500">
            ({data.summary.percent_used}% used)
          </span>
        </div>
        <svg
          className={`w-4 h-4 text-gray-500 transition-transform duration-200 ${isCollapsed ? '-rotate-90' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      <div className={`transition-all duration-200 overflow-hidden ${isCollapsed ? 'max-h-0' : 'max-h-[1000px]'}`}>
      <div className="p-4 space-y-4">
        {data.pools.map((pool) => {
          const progressColor = pool.percent_used >= 95
            ? 'var(--hydra-red)'
            : pool.percent_used >= 80
              ? 'var(--hydra-yellow)'
              : 'var(--hydra-green)';

          return (
            <div key={pool.name} className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-medium" style={{ color: 'var(--hydra-text)' }}>{pool.name}</span>
                  {pool.disk_count && (
                    <span className="text-xs px-2 py-0.5 rounded" style={{ backgroundColor: 'var(--hydra-panel-bg)', color: 'var(--hydra-text-muted)' }}>
                      {pool.disk_count} disks
                    </span>
                  )}
                  <span
                    className="text-xs px-2 py-0.5 rounded uppercase"
                    style={{
                      backgroundColor: pool.status === 'healthy' ? 'rgba(0, 255, 136, 0.2)' : 'rgba(255, 204, 0, 0.2)',
                      color: pool.status === 'healthy' ? 'var(--hydra-green)' : 'var(--hydra-yellow)'
                    }}
                  >
                    {pool.status}
                  </span>
                </div>
                <span className="text-sm" style={{ color: 'var(--hydra-text-muted)' }}>
                  {formatBytes(pool.used_bytes)} / {formatBytes(pool.total_bytes)}
                </span>
              </div>

              <div className="relative h-2 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--hydra-bg)' }}>
                <div
                  className="absolute h-full rounded-full transition-all duration-300"
                  style={{
                    width: `${pool.percent_used}%`,
                    backgroundColor: progressColor,
                    boxShadow: `0 0 10px ${progressColor}`
                  }}
                />
              </div>

              <div className="flex justify-between text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                <span>{pool.percent_used}% used</span>
                <span>{formatBytes(pool.free_bytes)} free</span>
              </div>
            </div>
          );
        })}

        {/* Summary */}
        <div className="pt-4 mt-4 border-t" style={{ borderColor: 'var(--hydra-border)' }}>
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium" style={{ color: 'var(--hydra-text-muted)' }}>Total Storage</span>
            <span className="text-lg font-bold" style={{ color: 'var(--hydra-cyan)' }}>
              {formatBytes(data.summary.total_bytes)}
            </span>
          </div>
          <div className="flex justify-between items-center mt-1">
            <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
              {data.summary.percent_used}% used
            </span>
            <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
              {formatBytes(data.summary.free_bytes)} free
            </span>
          </div>
        </div>
      </div>
      </div>
    </div>
  );
}
