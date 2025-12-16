'use client';

import { DomainView } from '../DomainTabs';
import { GrafanaEmbed } from '../embedded';
import { StoragePools } from '../StoragePools';
import type { StoragePoolsData } from '@/lib/api';

interface StorageViewProps {
  storagePools: StoragePoolsData | null;
}

export function StorageView({ storagePools }: StorageViewProps) {
  return (
    <DomainView
      title="Storage"
      icon="💾"
      description="Pools, capacity, backups, and data management"
      actions={
        <div className="flex items-center gap-2">
          <a
            href="http://192.168.1.244"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-3 py-1.5 rounded transition-colors"
            style={{
              backgroundColor: 'rgba(234, 179, 8, 0.1)',
              color: 'var(--hydra-yellow)',
              border: '1px solid var(--hydra-yellow)',
            }}
          >
            Unraid →
          </a>
          <a
            href="http://192.168.1.244:9001"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-3 py-1.5 rounded transition-colors"
            style={{
              backgroundColor: 'rgba(6, 182, 212, 0.1)',
              color: 'var(--hydra-cyan)',
              border: '1px solid var(--hydra-cyan)',
            }}
          >
            MinIO →
          </a>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Storage Summary */}
        <div className="grid grid-cols-4 gap-4">
          <div
            className="p-4 rounded-lg border"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="text-xs uppercase tracking-wider mb-1" style={{ color: 'var(--hydra-text-muted)' }}>
              Total Capacity
            </div>
            <div className="text-lg font-bold" style={{ color: 'var(--hydra-cyan)' }}>
              {storagePools?.summary?.total_bytes ? (storagePools.summary.total_bytes / 1e12).toFixed(1) : '150'} TB
            </div>
            <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
              Across all pools
            </div>
          </div>
          <div
            className="p-4 rounded-lg border"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="text-xs uppercase tracking-wider mb-1" style={{ color: 'var(--hydra-text-muted)' }}>
              Used
            </div>
            <div className="text-lg font-bold" style={{ color: 'var(--hydra-yellow)' }}>
              {storagePools?.summary?.used_bytes ? (storagePools.summary.used_bytes / 1e12).toFixed(1) : '95'} TB
            </div>
            <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
              {storagePools?.summary?.percent_used?.toFixed(0) || '63'}% utilized
            </div>
          </div>
          <div
            className="p-4 rounded-lg border"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="text-xs uppercase tracking-wider mb-1" style={{ color: 'var(--hydra-text-muted)' }}>
              Free
            </div>
            <div className="text-lg font-bold" style={{ color: 'var(--hydra-green)' }}>
              {storagePools?.summary?.free_bytes ? (storagePools.summary.free_bytes / 1e12).toFixed(1) : '55'} TB
            </div>
            <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
              Available
            </div>
          </div>
          <div
            className="p-4 rounded-lg border"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="text-xs uppercase tracking-wider mb-1" style={{ color: 'var(--hydra-text-muted)' }}>
              Parity Status
            </div>
            <div className="text-lg font-bold" style={{ color: 'var(--hydra-green)' }}>
              SYNCED
            </div>
            <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
              Last check: 2 days ago
            </div>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-3 gap-6">
          {/* Left Column: Pools */}
          <div className="col-span-1 space-y-4">
            <StoragePools data={storagePools} isCollapsed={false} onToggle={() => {}} />

            {/* Database Storage */}
            <div
              className="rounded-lg border p-4"
              style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
            >
              <div className="text-sm font-medium mb-3" style={{ color: 'var(--hydra-text)' }}>
                Databases
              </div>
              <div className="space-y-2">
                {[
                  { name: 'PostgreSQL', size: '2.4 GB', tables: 42 },
                  { name: 'Qdrant', size: '8.1 GB', collections: 6 },
                  { name: 'Redis', size: '512 MB', keys: '~15K' },
                ].map((db) => (
                  <div
                    key={db.name}
                    className="flex items-center justify-between p-2 rounded"
                    style={{ backgroundColor: 'rgba(0,0,0,0.2)' }}
                  >
                    <span className="text-sm" style={{ color: 'var(--hydra-text)' }}>
                      {db.name}
                    </span>
                    <div className="text-xs text-right">
                      <div style={{ color: 'var(--hydra-cyan)' }}>{db.size}</div>
                      <div style={{ color: 'var(--hydra-text-muted)' }}>
                        {db.tables || db.collections || db.keys}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Model Storage */}
            <div
              className="rounded-lg border p-4"
              style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
            >
              <div className="text-sm font-medium mb-3" style={{ color: 'var(--hydra-text)' }}>
                Model Storage
              </div>
              <div className="space-y-2">
                {[
                  { name: 'EXL2 Models', size: '180 GB', path: '/mnt/models/exl2' },
                  { name: 'GGUF Models', size: '45 GB', path: '/mnt/models/gguf' },
                  { name: 'Diffusion', size: '28 GB', path: '/mnt/models/diffusion' },
                  { name: 'Embeddings', size: '4 GB', path: '/mnt/models/embeddings' },
                ].map((store) => (
                  <div
                    key={store.name}
                    className="flex items-center justify-between p-2 rounded"
                    style={{ backgroundColor: 'rgba(0,0,0,0.2)' }}
                  >
                    <div>
                      <div className="text-sm" style={{ color: 'var(--hydra-text)' }}>
                        {store.name}
                      </div>
                      <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                        {store.path}
                      </div>
                    </div>
                    <span className="text-sm" style={{ color: 'var(--hydra-cyan)' }}>
                      {store.size}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Column: Grafana */}
          <div className="col-span-2">
            <div
              className="rounded-lg border overflow-hidden"
              style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
            >
              <GrafanaEmbed dashboard="storage" height={500} showHeader={true} />
            </div>
          </div>
        </div>

        {/* Share Details */}
        <div>
          <div className="text-xs uppercase tracking-wider mb-3" style={{ color: 'var(--hydra-text-muted)' }}>
            Network Shares
          </div>
          <div className="grid grid-cols-5 gap-3">
            {[
              { name: 'models', size: '257 GB', access: 'NFS', clients: 2 },
              { name: 'media', size: '45 TB', access: 'SMB', clients: 3 },
              { name: 'appdata', size: '120 GB', access: 'Local', clients: 0 },
              { name: 'backups', size: '8 TB', access: 'NFS', clients: 1 },
              { name: 'downloads', size: '2 TB', access: 'SMB', clients: 1 },
            ].map((share) => (
              <div
                key={share.name}
                className="p-3 rounded-lg border"
                style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium" style={{ color: 'var(--hydra-text)' }}>
                    {share.name}
                  </span>
                  <span
                    className="text-xs px-1.5 py-0.5 rounded"
                    style={{
                      backgroundColor:
                        share.access === 'NFS'
                          ? 'rgba(6, 182, 212, 0.1)'
                          : share.access === 'SMB'
                          ? 'rgba(139, 92, 246, 0.1)'
                          : 'rgba(107, 114, 128, 0.1)',
                      color:
                        share.access === 'NFS'
                          ? 'var(--hydra-cyan)'
                          : share.access === 'SMB'
                          ? 'var(--hydra-purple)'
                          : 'var(--hydra-text-muted)',
                    }}
                  >
                    {share.access}
                  </span>
                </div>
                <div className="text-lg font-bold" style={{ color: 'var(--hydra-yellow)' }}>
                  {share.size}
                </div>
                <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                  {share.clients} active clients
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Backup Status */}
        <div className="grid grid-cols-2 gap-6">
          <div
            className="rounded-lg border p-4"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="text-sm font-medium mb-3" style={{ color: 'var(--hydra-text)' }}>
              Backup Schedule
            </div>
            <div className="space-y-2 text-sm">
              {[
                { name: 'PostgreSQL', schedule: 'Daily 2:00 AM', last: '6h ago', status: 'success' },
                { name: 'Qdrant Snapshots', schedule: 'Daily 3:00 AM', last: '5h ago', status: 'success' },
                { name: 'Config Backup', schedule: 'Weekly Sun', last: '2d ago', status: 'success' },
                { name: 'Media Parity', schedule: 'Monthly', last: '12d ago', status: 'success' },
              ].map((backup) => (
                <div key={backup.name} className="flex items-center justify-between">
                  <span style={{ color: 'var(--hydra-text)' }}>{backup.name}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                      {backup.schedule}
                    </span>
                    <span
                      className="text-xs px-1.5 py-0.5 rounded"
                      style={{
                        backgroundColor:
                          backup.status === 'success' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                        color: backup.status === 'success' ? 'var(--hydra-green)' : 'var(--hydra-red)',
                      }}
                    >
                      {backup.last}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div
            className="rounded-lg border p-4"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="text-sm font-medium mb-3" style={{ color: 'var(--hydra-text)' }}>
              Disk Health
            </div>
            <div className="space-y-2 text-sm">
              {[
                { disk: 'Parity 1', size: '20TB', temp: '34°C', smart: 'PASSED' },
                { disk: 'Parity 2', size: '20TB', temp: '33°C', smart: 'PASSED' },
                { disk: 'Disk 1', size: '18TB', temp: '35°C', smart: 'PASSED' },
                { disk: 'Disk 2', size: '18TB', temp: '34°C', smart: 'PASSED' },
                { disk: 'Cache', size: '2TB NVMe', temp: '42°C', smart: 'PASSED' },
              ].map((disk) => (
                <div key={disk.disk} className="flex items-center justify-between">
                  <span style={{ color: 'var(--hydra-text)' }}>{disk.disk}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                      {disk.size}
                    </span>
                    <span className="text-xs" style={{ color: 'var(--hydra-cyan)' }}>
                      {disk.temp}
                    </span>
                    <span
                      className="text-xs px-1.5 py-0.5 rounded"
                      style={{
                        backgroundColor: 'rgba(34, 197, 94, 0.1)',
                        color: 'var(--hydra-green)',
                      }}
                    >
                      {disk.smart}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </DomainView>
  );
}
