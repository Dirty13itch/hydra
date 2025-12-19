import React, { useState, useEffect, useCallback } from 'react';
import { Card, Button, Tabs, Badge, Modal, ProgressBar } from '../components/UIComponents';
import {
  ThumbsUp, ThumbsDown, RefreshCw, Eye, AlertTriangle,
  CheckCircle, XCircle, BarChart3, Image as ImageIcon,
  Star, Loader2, Filter, Download
} from 'lucide-react';
import { FeedbackStats, QualityReport } from '../types';
import { useNotifications } from '../context/NotificationContext';

const API_BASE = 'http://192.168.1.244:8700';

type FeedbackRating = 'excellent' | 'good' | 'acceptable' | 'poor' | 'rejected';

interface PendingAsset {
  asset_id: string;
  asset_path: string;
  overall_score: number;
  tier: string;
  character_name?: string;
  prompt_used?: string;
  model_used?: string;
}

export const Feedback: React.FC = () => {
  const [activeTab, setActiveTab] = useState('REVIEW');
  const [stats, setStats] = useState<FeedbackStats | null>(null);
  const [pendingReviews, setPendingReviews] = useState<PendingAsset[]>([]);
  const [qualityStats, setQualityStats] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedAsset, setSelectedAsset] = useState<PendingAsset | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { addNotification } = useNotifications();

  const tabs = [
    { id: 'REVIEW', label: 'Review Queue' },
    { id: 'STATS', label: 'Statistics' },
    { id: 'QUALITY', label: 'Quality Scores' },
  ];

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [statsRes, pendingRes, qualityRes] = await Promise.all([
        fetch(`${API_BASE}/feedback/stats`),
        fetch(`${API_BASE}/quality/pending-reviews`),
        fetch(`${API_BASE}/quality/statistics`),
      ]);

      if (statsRes.ok) setStats(await statsRes.json());
      if (pendingRes.ok) {
        const data = await pendingRes.json();
        setPendingReviews(data.reports || []);
      }
      if (qualityRes.ok) setQualityStats(await qualityRes.json());
    } catch (e) {
      console.error('Failed to fetch feedback data:', e);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const submitFeedback = async (assetId: string, rating: FeedbackRating, regenerate: boolean = false) => {
    setIsSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/feedback/asset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          asset_id: assetId,
          asset_type: 'character_portrait',
          rating: rating,
          should_regenerate: regenerate,
        }),
      });

      if (res.ok) {
        addNotification('success', 'Feedback Recorded', `Asset ${rating === 'rejected' ? 'rejected' : 'approved'}`);
        setPendingReviews(prev => prev.filter(a => a.asset_id !== assetId));
        setSelectedAsset(null);
        fetchData();
      } else {
        addNotification('error', 'Feedback Failed', 'Could not submit feedback');
      }
    } catch (e) {
      addNotification('error', 'Error', 'Network error submitting feedback');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getTierColor = (tier: string) => {
    switch (tier) {
      case 'excellent': return 'text-emerald-400';
      case 'good': return 'text-cyan-400';
      case 'acceptable': return 'text-yellow-400';
      case 'poor': return 'text-orange-400';
      case 'reject': return 'text-red-400';
      default: return 'text-neutral-400';
    }
  };

  const getTierBadge = (tier: string): 'emerald' | 'cyan' | 'amber' | 'neutral' | 'purple' | 'red' => {
    const colors: Record<string, 'emerald' | 'cyan' | 'amber' | 'neutral' | 'purple' | 'red'> = {
      excellent: 'emerald',
      good: 'cyan',
      acceptable: 'amber',
      poor: 'amber',
      reject: 'red',
    };
    return colors[tier] || 'cyan';
  };

  const getProgressColor = (score: number): string => {
    if (score >= 75) return 'bg-emerald-500';
    if (score >= 50) return 'bg-amber-500';
    return 'bg-red-500';
  };

  const renderReviewQueue = () => (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium text-neutral-300">Pending Reviews</h3>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" icon={<RefreshCw size={14} />} onClick={fetchData}>
            Refresh
          </Button>
          <span className="text-xs font-mono text-neutral-500 self-center">
            {pendingReviews.length} PENDING
          </span>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="animate-spin text-cyan-500" size={24} />
        </div>
      ) : pendingReviews.length === 0 ? (
        <Card className="p-8 text-center">
          <CheckCircle className="mx-auto text-emerald-500 mb-4" size={48} />
          <h4 className="text-xl font-medium text-neutral-200 mb-2">All Caught Up!</h4>
          <p className="text-neutral-500">No assets pending review. Quality scoring will add items here automatically.</p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {pendingReviews.map((asset) => (
            <Card key={asset.asset_id} className="group hover:border-cyan-500/50 transition-colors">
              <div className="aspect-square bg-neutral-900 rounded-lg mb-3 overflow-hidden relative">
                {asset.asset_path ? (
                  <img
                    src={`${API_BASE}/files/${encodeURIComponent(asset.asset_path)}`}
                    alt="Asset preview"
                    className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect fill="%23374151" width="100" height="100"/><text x="50%" y="50%" fill="%239ca3af" text-anchor="middle" dy=".3em">No Preview</text></svg>';
                    }}
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <ImageIcon className="text-neutral-600" size={48} />
                  </div>
                )}
                <div className="absolute top-2 right-2">
                  <Badge variant={getTierBadge(asset.tier)}>{asset.tier.toUpperCase()}</Badge>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-mono text-neutral-400">Score</span>
                  <span className={`text-lg font-bold ${getTierColor(asset.tier)}`}>
                    {asset.overall_score.toFixed(1)}
                  </span>
                </div>

                <ProgressBar
                  value={asset.overall_score}
                  colorClass={getProgressColor(asset.overall_score)}
                />

                {asset.character_name && (
                  <p className="text-xs text-neutral-500">Character: {asset.character_name}</p>
                )}
              </div>

              <div className="mt-4 pt-3 border-t border-neutral-800 flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  className="flex-1 hover:bg-emerald-900/30 hover:text-emerald-400"
                  icon={<ThumbsUp size={14} />}
                  onClick={() => submitFeedback(asset.asset_id, 'good')}
                  disabled={isSubmitting}
                >
                  Approve
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="flex-1 hover:bg-red-900/30 hover:text-red-400"
                  icon={<ThumbsDown size={14} />}
                  onClick={() => submitFeedback(asset.asset_id, 'rejected', true)}
                  disabled={isSubmitting}
                >
                  Reject
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  icon={<Eye size={14} />}
                  onClick={() => setSelectedAsset(asset)}
                >
                  View
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );

  const renderStats = () => (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium text-neutral-300">Feedback Statistics</h3>
        <Button variant="ghost" size="sm" icon={<Download size={14} />}>
          Export
        </Button>
      </div>

      {!stats ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="animate-spin text-cyan-500" size={24} />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="p-4">
              <div className="text-xs font-mono text-neutral-500 uppercase mb-1">Total Feedback</div>
              <div className="text-3xl font-bold text-cyan-400">{stats.total_feedback}</div>
            </Card>
            <Card className="p-4">
              <div className="text-xs font-mono text-neutral-500 uppercase mb-1">Asset Reviews</div>
              <div className="text-3xl font-bold text-purple-400">{stats.asset_feedback}</div>
            </Card>
            <Card className="p-4">
              <div className="text-xs font-mono text-neutral-500 uppercase mb-1">Avg Rating</div>
              <div className="text-3xl font-bold text-emerald-400">
                {stats.avg_asset_rating > 0 ? stats.avg_asset_rating.toFixed(1) : 'N/A'}
              </div>
            </Card>
            <Card className="p-4">
              <div className="text-xs font-mono text-neutral-500 uppercase mb-1">Needs Regen</div>
              <div className="text-3xl font-bold text-orange-400">{stats.needs_regeneration}</div>
            </Card>
          </div>

          {stats.top_issues && stats.top_issues.length > 0 && (
            <Card className="p-4">
              <h4 className="text-sm font-mono text-neutral-400 uppercase mb-3">Top Issues</h4>
              <div className="space-y-2">
                {stats.top_issues.map((issue: any, i: number) => (
                  <div key={i} className="flex justify-between items-center">
                    <span className="text-neutral-300">{issue.issue || issue}</span>
                    <Badge variant="red">{issue.count || 1}</Badge>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );

  const renderQualityStats = () => (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium text-neutral-300">Quality Scoring Summary</h3>
        <Button variant="ghost" size="sm" icon={<RefreshCw size={14} />} onClick={fetchData}>
          Refresh
        </Button>
      </div>

      {!qualityStats ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="animate-spin text-cyan-500" size={24} />
        </div>
      ) : qualityStats.total === 0 ? (
        <Card className="p-8 text-center">
          <BarChart3 className="mx-auto text-neutral-600 mb-4" size={48} />
          <h4 className="text-xl font-medium text-neutral-200 mb-2">No Quality Reports Yet</h4>
          <p className="text-neutral-500">Quality scoring will analyze generated assets automatically.</p>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="p-4">
              <div className="text-xs font-mono text-neutral-500 uppercase mb-1">Total Scored</div>
              <div className="text-3xl font-bold text-cyan-400">{qualityStats.total}</div>
            </Card>
            <Card className="p-4">
              <div className="text-xs font-mono text-neutral-500 uppercase mb-1">Average Score</div>
              <div className="text-3xl font-bold text-purple-400">{qualityStats.average_score?.toFixed(1) || 'N/A'}</div>
            </Card>
            <Card className="p-4">
              <div className="text-xs font-mono text-neutral-500 uppercase mb-1">Pass Rate</div>
              <div className="text-3xl font-bold text-emerald-400">{qualityStats.pass_rate?.toFixed(0) || 0}%</div>
            </Card>
            <Card className="p-4">
              <div className="text-xs font-mono text-neutral-500 uppercase mb-1">Score Range</div>
              <div className="text-xl font-bold text-neutral-300">
                {qualityStats.min_score?.toFixed(0) || 0} - {qualityStats.max_score?.toFixed(0) || 100}
              </div>
            </Card>
          </div>

          {qualityStats.tier_distribution && (
            <Card className="p-4">
              <h4 className="text-sm font-mono text-neutral-400 uppercase mb-3">Tier Distribution</h4>
              <div className="space-y-3">
                {Object.entries(qualityStats.tier_distribution).map(([tier, count]) => {
                  const percentage = qualityStats.total > 0 ? ((count as number) / qualityStats.total) * 100 : 0;
                  const colorClass = tier === 'excellent' || tier === 'good' ? 'bg-emerald-500' : tier === 'acceptable' ? 'bg-amber-500' : 'bg-red-500';
                  return (
                    <div key={tier} className="flex items-center gap-3">
                      <span className={`w-24 text-sm capitalize ${getTierColor(tier)}`}>{tier}</span>
                      <div className="flex-1">
                        <ProgressBar
                          value={percentage}
                          colorClass={colorClass}
                        />
                      </div>
                      <span className="text-neutral-400 text-sm w-12 text-right">{count as number}</span>
                    </div>
                  );
                })}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );

  return (
    <div className="flex flex-col h-full bg-surface-base">
      {/* Asset Detail Modal */}
      <Modal
        isOpen={!!selectedAsset}
        onClose={() => setSelectedAsset(null)}
        title="ASSET REVIEW"
      >
        {selectedAsset && (
          <div className="space-y-4">
            <div className="aspect-video bg-neutral-900 rounded-lg overflow-hidden">
              <img
                src={`${API_BASE}/files/${encodeURIComponent(selectedAsset.asset_path)}`}
                alt="Asset preview"
                className="w-full h-full object-contain"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none';
                }}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-xs text-neutral-500 uppercase">Quality Score</span>
                <div className={`text-2xl font-bold ${getTierColor(selectedAsset.tier)}`}>
                  {selectedAsset.overall_score.toFixed(1)}
                </div>
              </div>
              <div>
                <span className="text-xs text-neutral-500 uppercase">Tier</span>
                <div className="mt-1">
                  <Badge variant={getTierBadge(selectedAsset.tier)}>{selectedAsset.tier.toUpperCase()}</Badge>
                </div>
              </div>
            </div>

            {selectedAsset.prompt_used && (
              <div>
                <span className="text-xs text-neutral-500 uppercase">Prompt</span>
                <p className="text-sm text-neutral-300 mt-1">{selectedAsset.prompt_used}</p>
              </div>
            )}

            <div className="flex gap-2 pt-4 border-t border-neutral-800">
              <Button
                variant="primary"
                className="flex-1 bg-emerald-600 hover:bg-emerald-500"
                icon={<Star size={16} />}
                onClick={() => submitFeedback(selectedAsset.asset_id, 'excellent')}
                disabled={isSubmitting}
              >
                Excellent
              </Button>
              <Button
                variant="primary"
                className="flex-1 bg-cyan-600 hover:bg-cyan-500"
                icon={<ThumbsUp size={16} />}
                onClick={() => submitFeedback(selectedAsset.asset_id, 'good')}
                disabled={isSubmitting}
              >
                Good
              </Button>
              <Button
                variant="primary"
                className="flex-1 bg-red-600 hover:bg-red-500"
                icon={<RefreshCw size={16} />}
                onClick={() => submitFeedback(selectedAsset.asset_id, 'rejected', true)}
                disabled={isSubmitting}
              >
                Regenerate
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Header */}
      <div className="px-6 pt-6 pb-2 border-b border-neutral-800 flex justify-between items-end">
        <div>
          <h2 className="text-2xl font-mono font-bold text-neutral-200 flex items-center gap-2">
            <span className="text-orange-500">FEEDBACK</span> // HUMAN-IN-THE-LOOP
          </h2>
          <Tabs
            tabs={tabs}
            activeTab={activeTab}
            onChange={setActiveTab}
            className="mt-4"
            variant="purple"
          />
        </div>
        <div className="pb-2 flex gap-2">
          <Badge variant="cyan">{pendingReviews.length} Pending</Badge>
          {stats && stats.needs_regeneration > 0 && (
            <Badge variant="amber">{stats.needs_regeneration} Regen Queue</Badge>
          )}
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === 'REVIEW' && renderReviewQueue()}
        {activeTab === 'STATS' && renderStats()}
        {activeTab === 'QUALITY' && renderQualityStats()}
      </div>
    </div>
  );
};
