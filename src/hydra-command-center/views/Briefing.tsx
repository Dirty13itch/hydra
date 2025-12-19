import { useState, useEffect } from 'react';
import {
  Calendar,
  Mail,
  Newspaper,
  Server,
  Volume2,
  Send,
  RefreshCw,
  Clock,
  AlertCircle,
  CheckCircle,
  Settings,
  Plus,
  X,
  DollarSign,
  TrendingUp,
  TrendingDown,
  Wallet,
  PiggyBank,
} from 'lucide-react';

interface BriefingSection {
  title: string;
  icon: string;
  items: any[];
  summary: string;
  priority: number;
}

interface BriefingData {
  generated_at: string;
  greeting: string;
  sections: BriefingSection[];
  voice_summary: string;
}

interface ServiceStatus {
  configured: boolean;
  authenticated?: boolean;
}

interface NewsStatus extends ServiceStatus {
  miniflux_url: string;
  monitored_topics: string[];
}

interface FinancialStatus {
  plaid_configured: boolean;
  accounts_linked: number;
  crypto_holdings: number;
  budgets_configured: number;
  features_available: {
    banking: boolean;
    crypto: boolean;
    budgets: boolean;
  };
}

interface CryptoHolding {
  symbol: string;
  name: string;
  quantity: number;
  current_price: number;
  total_value: number;
  price_change_24h: number;
}

interface BudgetAlert {
  category: string;
  spent: number;
  limit: number;
  percentage: number;
  status: 'ok' | 'warning' | 'exceeded';
}

const API_BASE = 'http://192.168.1.244:8700';

export default function Briefing() {
  const [briefing, setBriefing] = useState<BriefingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [delivering, setDelivering] = useState(false);
  const [deliveryStatus, setDeliveryStatus] = useState<string | null>(null);

  // Service statuses
  const [calendarStatus, setCalendarStatus] = useState<ServiceStatus | null>(null);
  const [gmailStatus, setGmailStatus] = useState<ServiceStatus | null>(null);
  const [newsStatus, setNewsStatus] = useState<NewsStatus | null>(null);
  const [financialStatus, setFinancialStatus] = useState<FinancialStatus | null>(null);
  const [cryptoHoldings, setCryptoHoldings] = useState<CryptoHolding[]>([]);
  const [budgetAlerts, setBudgetAlerts] = useState<BudgetAlert[]>([]);

  // Topic management
  const [newTopic, setNewTopic] = useState('');
  const [topics, setTopics] = useState<string[]>([]);

  useEffect(() => {
    fetchAll();
  }, []);

  const fetchAll = async () => {
    setLoading(true);
    await Promise.all([
      fetchBriefing(),
      fetchCalendarStatus(),
      fetchGmailStatus(),
      fetchNewsStatus(),
      fetchTopics(),
      fetchFinancialData(),
    ]);
    setLoading(false);
  };

  const fetchBriefing = async () => {
    try {
      const res = await fetch(`${API_BASE}/briefing/`);
      if (res.ok) {
        const data = await res.json();
        setBriefing(data);
      }
    } catch (err) {
      console.error('Failed to fetch briefing:', err);
    }
  };

  const fetchCalendarStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/google/status`);
      if (res.ok) {
        setCalendarStatus(await res.json());
      }
    } catch (err) {
      console.error('Failed to fetch calendar status:', err);
    }
  };

  const fetchGmailStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/gmail/status`);
      if (res.ok) {
        setGmailStatus(await res.json());
      }
    } catch (err) {
      console.error('Failed to fetch gmail status:', err);
    }
  };

  const fetchNewsStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/news/status`);
      if (res.ok) {
        setNewsStatus(await res.json());
      }
    } catch (err) {
      console.error('Failed to fetch news status:', err);
    }
  };

  const fetchTopics = async () => {
    try {
      const res = await fetch(`${API_BASE}/news/topics`);
      if (res.ok) {
        const data = await res.json();
        setTopics(data.topics || []);
      }
    } catch (err) {
      console.error('Failed to fetch topics:', err);
    }
  };

  const fetchFinancialData = async () => {
    try {
      // Fetch financial status
      const statusRes = await fetch(`${API_BASE}/financial/status`);
      if (statusRes.ok) {
        const statusData = await statusRes.json();
        setFinancialStatus(statusData);
      }

      // Fetch crypto holdings
      const cryptoRes = await fetch(`${API_BASE}/financial/crypto`);
      if (cryptoRes.ok) {
        const cryptoData = await cryptoRes.json();
        setCryptoHoldings(cryptoData.holdings || []);
      }

      // Fetch budget alerts
      const budgetsRes = await fetch(`${API_BASE}/financial/budgets`);
      if (budgetsRes.ok) {
        const budgetsData = await budgetsRes.json();
        // Filter for warnings and exceeded
        const alerts = (budgetsData.budgets || []).filter(
          (b: BudgetAlert) => b.status === 'warning' || b.status === 'exceeded'
        );
        setBudgetAlerts(alerts);
      }
    } catch (err) {
      console.error('Failed to fetch financial data:', err);
    }
  };

  const deliverBriefing = async (voice: boolean = true, discord: boolean = false) => {
    setDelivering(true);
    setDeliveryStatus(null);
    try {
      const res = await fetch(`${API_BASE}/briefing/deliver?voice=${voice}&discord=${discord}`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = await res.json();
        const voiceStatus = data.delivery?.voice?.status;
        setDeliveryStatus(voiceStatus === 'delivered' ? 'Briefing delivered!' : 'Delivery failed');
      }
    } catch (err) {
      setDeliveryStatus('Error delivering briefing');
    }
    setDelivering(false);
    setTimeout(() => setDeliveryStatus(null), 3000);
  };

  const addTopic = async () => {
    if (!newTopic.trim()) return;
    try {
      await fetch(`${API_BASE}/news/topics`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: newTopic.trim() }),
      });
      setNewTopic('');
      fetchTopics();
    } catch (err) {
      console.error('Failed to add topic:', err);
    }
  };

  const removeTopic = async (topic: string) => {
    try {
      await fetch(`${API_BASE}/news/topics`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic }),
      });
      fetchTopics();
    } catch (err) {
      console.error('Failed to remove topic:', err);
    }
  };

  const startOAuth = () => {
    window.open(`${API_BASE}/google/auth`, '_blank');
  };

  const getIconForSection = (iconName: string) => {
    switch (iconName) {
      case 'calendar': return <Calendar className="w-5 h-5" />;
      case 'mail': return <Mail className="w-5 h-5" />;
      case 'newspaper': return <Newspaper className="w-5 h-5" />;
      case 'server': return <Server className="w-5 h-5" />;
      case 'book-open': return <Newspaper className="w-5 h-5" />;
      default: return <AlertCircle className="w-5 h-5" />;
    }
  };

  const getPriorityColor = (priority: number) => {
    if (priority <= 2) return 'border-red-500/50 bg-red-500/10';
    if (priority <= 3) return 'border-yellow-500/50 bg-yellow-500/10';
    return 'border-gray-600 bg-gray-800/50';
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Morning Briefing</h1>
          <p className="text-gray-400 mt-1">
            {briefing ? briefing.greeting : 'Loading...'}
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => fetchAll()}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => deliverBriefing(true, false)}
            disabled={delivering}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-colors"
          >
            <Volume2 className="w-4 h-4" />
            {delivering ? 'Speaking...' : 'Speak Briefing'}
          </button>
        </div>
      </div>

      {/* Delivery Status */}
      {deliveryStatus && (
        <div className={`p-3 rounded-lg flex items-center gap-2 ${
          deliveryStatus.includes('delivered') ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'
        }`}>
          {deliveryStatus.includes('delivered') ? <CheckCircle className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
          {deliveryStatus}
        </div>
      )}

      {/* Service Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Calendar Status */}
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Calendar className="w-5 h-5 text-blue-400" />
              <span className="font-medium text-white">Google Calendar</span>
            </div>
            {calendarStatus?.authenticated ? (
              <CheckCircle className="w-5 h-5 text-emerald-400" />
            ) : (
              <AlertCircle className="w-5 h-5 text-yellow-400" />
            )}
          </div>
          {calendarStatus?.authenticated ? (
            <p className="text-sm text-gray-400">Connected and syncing</p>
          ) : (
            <button
              onClick={startOAuth}
              className="text-sm text-blue-400 hover:text-blue-300"
            >
              Connect Google Account
            </button>
          )}
        </div>

        {/* Gmail Status */}
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Mail className="w-5 h-5 text-red-400" />
              <span className="font-medium text-white">Gmail</span>
            </div>
            {gmailStatus?.authenticated ? (
              <CheckCircle className="w-5 h-5 text-emerald-400" />
            ) : (
              <AlertCircle className="w-5 h-5 text-yellow-400" />
            )}
          </div>
          {gmailStatus?.authenticated ? (
            <p className="text-sm text-gray-400">Connected and monitoring</p>
          ) : (
            <p className="text-sm text-gray-400">Uses same OAuth as Calendar</p>
          )}
        </div>

        {/* News Status */}
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Newspaper className="w-5 h-5 text-orange-400" />
              <span className="font-medium text-white">News/RSS</span>
            </div>
            {newsStatus?.configured ? (
              <CheckCircle className="w-5 h-5 text-emerald-400" />
            ) : (
              <AlertCircle className="w-5 h-5 text-yellow-400" />
            )}
          </div>
          <p className="text-sm text-gray-400">
            {newsStatus?.configured
              ? `${topics.length} topics monitored`
              : 'Set MINIFLUX_API_KEY to enable'}
          </p>
        </div>

        {/* Financial Status */}
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-emerald-400" />
              <span className="font-medium text-white">Financial</span>
            </div>
            {financialStatus?.features_available?.crypto || financialStatus?.features_available?.budgets ? (
              <CheckCircle className="w-5 h-5 text-emerald-400" />
            ) : (
              <AlertCircle className="w-5 h-5 text-yellow-400" />
            )}
          </div>
          <p className="text-sm text-gray-400">
            {cryptoHoldings.length > 0
              ? `${cryptoHoldings.length} crypto holdings`
              : financialStatus?.features_available?.crypto
                ? 'Ready - add holdings'
                : 'Configure Plaid to enable'}
          </p>
        </div>
      </div>

      {/* Topic Management */}
      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <h3 className="font-medium text-white mb-3 flex items-center gap-2">
          <Settings className="w-4 h-4" />
          Monitored Topics
        </h3>
        <div className="flex flex-wrap gap-2 mb-3">
          {topics.map((topic) => (
            <span
              key={topic}
              className="flex items-center gap-1 px-3 py-1 bg-gray-700 text-gray-300 rounded-full text-sm"
            >
              {topic}
              <button
                onClick={() => removeTopic(topic)}
                className="ml-1 text-gray-500 hover:text-red-400"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
          {topics.length === 0 && (
            <span className="text-gray-500 text-sm">No topics configured</span>
          )}
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={newTopic}
            onChange={(e) => setNewTopic(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addTopic()}
            placeholder="Add topic (e.g., 'artificial intelligence')"
            className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-500 text-sm"
          />
          <button
            onClick={addTopic}
            className="px-3 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Financial Summary */}
      {(cryptoHoldings.length > 0 || budgetAlerts.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Crypto Holdings */}
          {cryptoHoldings.length > 0 && (
            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <h3 className="font-medium text-white mb-3 flex items-center gap-2">
                <Wallet className="w-4 h-4 text-amber-400" />
                Crypto Holdings
              </h3>
              <div className="space-y-2">
                {cryptoHoldings.map((holding, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between bg-gray-700/50 rounded px-3 py-2"
                  >
                    <div>
                      <span className="font-medium text-white">{holding.symbol}</span>
                      <span className="text-gray-400 text-sm ml-2">
                        {holding.quantity.toLocaleString()} @ ${holding.current_price.toLocaleString()}
                      </span>
                    </div>
                    <div className="text-right">
                      <div className="font-medium text-white">
                        ${holding.total_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </div>
                      <div className={`text-xs flex items-center gap-1 ${
                        holding.price_change_24h >= 0 ? 'text-emerald-400' : 'text-red-400'
                      }`}>
                        {holding.price_change_24h >= 0 ? (
                          <TrendingUp className="w-3 h-3" />
                        ) : (
                          <TrendingDown className="w-3 h-3" />
                        )}
                        {holding.price_change_24h.toFixed(2)}%
                      </div>
                    </div>
                  </div>
                ))}
                <div className="border-t border-gray-600 pt-2 mt-2 flex justify-between">
                  <span className="text-gray-400">Total</span>
                  <span className="font-bold text-emerald-400">
                    ${cryptoHoldings.reduce((sum, h) => sum + h.total_value, 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Budget Alerts */}
          {budgetAlerts.length > 0 && (
            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <h3 className="font-medium text-white mb-3 flex items-center gap-2">
                <PiggyBank className="w-4 h-4 text-pink-400" />
                Budget Alerts
              </h3>
              <div className="space-y-2">
                {budgetAlerts.map((alert, idx) => (
                  <div
                    key={idx}
                    className={`flex items-center justify-between rounded px-3 py-2 ${
                      alert.status === 'exceeded'
                        ? 'bg-red-500/10 border border-red-500/30'
                        : 'bg-yellow-500/10 border border-yellow-500/30'
                    }`}
                  >
                    <div>
                      <span className="font-medium text-white">{alert.category}</span>
                      <span className={`text-sm ml-2 ${
                        alert.status === 'exceeded' ? 'text-red-400' : 'text-yellow-400'
                      }`}>
                        {alert.status === 'exceeded' ? 'EXCEEDED' : 'WARNING'}
                      </span>
                    </div>
                    <div className="text-right">
                      <div className="text-white">
                        ${alert.spent.toLocaleString()} / ${alert.limit.toLocaleString()}
                      </div>
                      <div className="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            alert.status === 'exceeded' ? 'bg-red-500' : 'bg-yellow-500'
                          }`}
                          style={{ width: `${Math.min(alert.percentage, 100)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Briefing Sections */}
      {briefing && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <Clock className="w-4 h-4" />
            Generated: {new Date(briefing.generated_at).toLocaleString()}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {briefing.sections
              .sort((a, b) => a.priority - b.priority)
              .map((section, idx) => (
                <div
                  key={idx}
                  className={`rounded-lg p-4 border ${getPriorityColor(section.priority)}`}
                >
                  <div className="flex items-center gap-2 mb-3">
                    {getIconForSection(section.icon)}
                    <h3 className="font-medium text-white">{section.title}</h3>
                    <span className="ml-auto text-xs text-gray-500">
                      Priority {section.priority}
                    </span>
                  </div>
                  <p className="text-gray-300 mb-3">{section.summary}</p>
                  {section.items.length > 0 && (
                    <div className="space-y-2">
                      {section.items.slice(0, 5).map((item, itemIdx) => (
                        <div
                          key={itemIdx}
                          className="text-sm text-gray-400 bg-black/20 rounded px-2 py-1"
                        >
                          {item.title || item.service || item.time ? (
                            <span>
                              {item.time && <span className="text-gray-500 mr-2">{item.time}</span>}
                              {item.title || item.service}
                              {item.status && (
                                <span className={`ml-2 ${item.status === 'healthy' ? 'text-emerald-400' : 'text-yellow-400'}`}>
                                  ({item.status})
                                </span>
                              )}
                            </span>
                          ) : (
                            JSON.stringify(item)
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Voice Summary */}
      {briefing && (
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <h3 className="font-medium text-white mb-2 flex items-center gap-2">
            <Volume2 className="w-4 h-4" />
            Voice Summary
          </h3>
          <p className="text-gray-300 italic">"{briefing.voice_summary}"</p>
        </div>
      )}
    </div>
  );
}
