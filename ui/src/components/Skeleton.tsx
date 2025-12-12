'use client';

interface SkeletonProps {
  className?: string;
  width?: string | number;
  height?: string | number;
}

export function Skeleton({ className = '', width, height }: SkeletonProps) {
  const style: React.CSSProperties = {};
  if (width) style.width = typeof width === 'number' ? `${width}px` : width;
  if (height) style.height = typeof height === 'number' ? `${height}px` : height;

  return <div className={`skeleton ${className}`} style={style} />;
}

// Pre-built skeleton layouts for common components
export function StatsSkeleton() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4 mb-6">
      {[...Array(6)].map((_, i) => (
        <div key={i} className="panel p-4 text-center">
          <Skeleton className="h-8 w-16 mx-auto mb-2" />
          <Skeleton className="h-3 w-20 mx-auto" />
        </div>
      ))}
    </div>
  );
}

export function NodeCardSkeleton() {
  return (
    <div className="panel p-4 space-y-3">
      <div className="flex items-center justify-between">
        <Skeleton className="h-5 w-24" />
        <Skeleton className="h-4 w-16" />
      </div>
      <Skeleton className="h-3 w-32" />
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Skeleton className="h-2 flex-1" />
          <Skeleton className="h-4 w-8" />
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="h-2 flex-1" />
          <Skeleton className="h-4 w-8" />
        </div>
      </div>
      <div className="pt-2 border-t border-hydra-gray/30">
        <Skeleton className="h-3 w-full" />
      </div>
    </div>
  );
}

export function ServiceListSkeleton() {
  return (
    <div className="panel">
      <div className="panel-header flex items-center gap-2">
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-20" />
      </div>
      <div className="p-4 space-y-3">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="flex items-center justify-between py-1.5 border-b border-hydra-gray/30 last:border-0">
            <div className="flex items-center gap-3">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-3 w-12" />
            </div>
            <Skeleton className="h-5 w-10" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function ContainerListSkeleton() {
  return (
    <div className="panel h-full flex flex-col">
      <div className="panel-header flex items-center gap-2">
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-24" />
      </div>
      <div className="p-4 space-y-2 flex-1 overflow-hidden">
        {[...Array(10)].map((_, i) => (
          <div key={i} className="flex items-center justify-between py-2 border-b border-hydra-gray/30 last:border-0">
            <div className="flex items-center gap-2">
              <Skeleton className="h-3 w-3 rounded-full" />
              <Skeleton className="h-4 w-32" />
            </div>
            <Skeleton className="h-4 w-16" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function AuditLogSkeleton() {
  return (
    <div className="panel h-full flex flex-col">
      <div className="panel-header flex items-center gap-2">
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-16" />
      </div>
      <div className="p-4 space-y-3 flex-1 overflow-hidden">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="space-y-1">
            <div className="flex items-center gap-2">
              <Skeleton className="h-3 w-16" />
              <Skeleton className="h-3 w-12" />
            </div>
            <Skeleton className="h-4 w-full" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function AIModelsPanelSkeleton() {
  return (
    <div className="panel p-4">
      <Skeleton className="h-4 w-20 mb-3" />
      <div className="mb-4 p-3 rounded border border-hydra-gray/30">
        <div className="flex items-center justify-between mb-2">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-4 w-24" />
        </div>
        <Skeleton className="h-2 w-full rounded-full" />
      </div>
      <Skeleton className="h-3 w-24 mb-2" />
      <div className="space-y-2">
        {[...Array(2)].map((_, i) => (
          <div key={i} className="p-2 rounded border border-hydra-gray/30">
            <Skeleton className="h-4 w-28 mb-1" />
            <Skeleton className="h-3 w-20" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function QuickActionsSkeleton() {
  return (
    <div className="panel p-4">
      <Skeleton className="h-4 w-24 mb-3" />
      <div className="grid grid-cols-2 gap-2">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="p-3 rounded border border-hydra-gray/30">
            <div className="flex items-start gap-2">
              <Skeleton className="h-4 w-4 flex-shrink-0" />
              <div className="flex-1">
                <Skeleton className="h-3 w-20 mb-1" />
                <Skeleton className="h-2 w-full hidden sm:block" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
