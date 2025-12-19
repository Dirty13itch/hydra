import React, { useState, useEffect } from 'react';
import { Card, Button, Tabs, Badge, ProgressBar } from '../components/UIComponents';
import {
  Gamepad2,
  Search,
  Star,
  Clock,
  Play,
  Pause,
  Heart,
  EyeOff,
  Folder,
  Download,
  RefreshCw,
  Loader2,
  ExternalLink,
  Filter,
  Grid,
  List,
  Plus,
  X,
  Check,
  HardDrive,
  Tag,
  Calendar,
  Settings
} from 'lucide-react';

const API_BASE = 'http://192.168.1.244:8700';

interface Game {
  id: string;
  slug: string;
  title: string;
  developer: string | null;
  version: string | null;
  engine: string;
  status: string;
  install_path: string | null;
  executable: string | null;
  description: string | null;
  vndb_id: string | null;
  f95_thread_id: string | null;
  tags: string[];
  rating: number | null;
  notes: string | null;
  favorite: boolean;
  hidden: boolean;
  completion_status: string;
  cover_path: string | null;
  size_bytes: number | null;
  playtime_seconds: number;
  last_played: string | null;
  created_at: string;
  updated_at: string;
}

interface GameStats {
  total_games: number;
  by_engine: Record<string, number>;
  by_completion: Record<string, number>;
  total_playtime_seconds: number;
  total_playtime_hours: number;
  total_size_bytes: number;
  total_size_gb: number;
}

interface VNDBResult {
  id: string;
  title: string;
  developers: string[];
  tags: string[];
  rating: number | null;
  image_url: string | null;
  description: string;
}

interface ScannedGame {
  path: string;
  name: string;
  engine: string;
  executable: string | null;
  size_bytes: number;
}

export const Games: React.FC = () => {
  const [activeTab, setActiveTab] = useState('LIBRARY');
  const [games, setGames] = useState<Game[]>([]);
  const [stats, setStats] = useState<GameStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [engineFilter, setEngineFilter] = useState('');
  const [completionFilter, setCompletionFilter] = useState('');
  const [showFavorites, setShowFavorites] = useState(false);

  // Add game modal
  const [showAddModal, setShowAddModal] = useState(false);
  const [newGame, setNewGame] = useState({ title: '', developer: '', engine: 'unknown', tags: '' });
  const [vndbSearchQuery, setVndbSearchQuery] = useState('');
  const [vndbResults, setVndbResults] = useState<VNDBResult[]>([]);
  const [searchingVndb, setSearchingVndb] = useState(false);

  // Scan modal
  const [showScanModal, setShowScanModal] = useState(false);
  const [scanPath, setScanPath] = useState('/mnt/user/games');
  const [scanning, setScanning] = useState(false);
  const [scannedGames, setScannedGames] = useState<ScannedGame[]>([]);
  const [importing, setImporting] = useState<string | null>(null);

  // Selected game
  const [selectedGame, setSelectedGame] = useState<Game | null>(null);

  // Active session
  const [activeSession, setActiveSession] = useState<{ id: string; game_id: string; started_at: string } | null>(null);

  const tabs = [
    { id: 'LIBRARY', label: 'Library' },
    { id: 'STATS', label: 'Statistics' },
    { id: 'IMPORT', label: 'Import' }
  ];

  useEffect(() => {
    fetchGames();
    fetchStats();
  }, [searchQuery, engineFilter, completionFilter, showFavorites]);

  const fetchGames = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchQuery) params.set('search', searchQuery);
      if (engineFilter) params.set('engine', engineFilter);
      if (completionFilter) params.set('completion', completionFilter);
      if (showFavorites) params.set('favorite', 'true');
      params.set('limit', '100');

      const res = await fetch(`${API_BASE}/games/?${params}`);
      const data = await res.json();
      setGames(data.games || []);
    } catch (error) {
      console.error('Failed to fetch games:', error);
    }
    setLoading(false);
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/games/stats`);
      setStats(await res.json());
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const searchVNDB = async () => {
    if (!vndbSearchQuery.trim()) return;
    setSearchingVndb(true);
    try {
      const res = await fetch(`${API_BASE}/games/vndb/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: vndbSearchQuery, limit: 5 })
      });
      setVndbResults(await res.json());
    } catch (error) {
      console.error('VNDB search failed:', error);
    }
    setSearchingVndb(false);
  };

  const addGame = async () => {
    try {
      const res = await fetch(`${API_BASE}/games/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...newGame,
          tags: newGame.tags.split(',').map(t => t.trim()).filter(Boolean)
        })
      });
      if (res.ok) {
        setShowAddModal(false);
        setNewGame({ title: '', developer: '', engine: 'unknown', tags: '' });
        fetchGames();
        fetchStats();
      }
    } catch (error) {
      console.error('Failed to add game:', error);
    }
  };

  const scanDirectory = async () => {
    if (!scanPath.trim()) return;
    setScanning(true);
    try {
      const res = await fetch(`${API_BASE}/games/scan?path=${encodeURIComponent(scanPath)}`, {
        method: 'POST'
      });
      const data = await res.json();
      setScannedGames(data.games || []);
    } catch (error) {
      console.error('Scan failed:', error);
    }
    setScanning(false);
  };

  const importGame = async (game: ScannedGame) => {
    setImporting(game.path);
    try {
      const res = await fetch(`${API_BASE}/games/import?path=${encodeURIComponent(game.path)}&search_vndb=true`, {
        method: 'POST'
      });
      if (res.ok) {
        setScannedGames(prev => prev.filter(g => g.path !== game.path));
        fetchGames();
        fetchStats();
      }
    } catch (error) {
      console.error('Import failed:', error);
    }
    setImporting(null);
  };

  const toggleFavorite = async (game: Game) => {
    try {
      await fetch(`${API_BASE}/games/${game.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ favorite: !game.favorite })
      });
      fetchGames();
    } catch (error) {
      console.error('Failed to toggle favorite:', error);
    }
  };

  const updateCompletion = async (game: Game, status: string) => {
    try {
      await fetch(`${API_BASE}/games/${game.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ completion_status: status })
      });
      fetchGames();
      setSelectedGame(null);
    } catch (error) {
      console.error('Failed to update completion:', error);
    }
  };

  const startSession = async (gameId: string) => {
    try {
      const res = await fetch(`${API_BASE}/games/${gameId}/sessions/start`, { method: 'POST' });
      const session = await res.json();
      setActiveSession(session);
    } catch (error) {
      console.error('Failed to start session:', error);
    }
  };

  const endSession = async () => {
    if (!activeSession) return;
    try {
      await fetch(`${API_BASE}/games/sessions/${activeSession.id}/end`, { method: 'POST' });
      setActiveSession(null);
      fetchGames();
    } catch (error) {
      console.error('Failed to end session:', error);
    }
  };

  const formatPlaytime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (hours > 0) return `${hours}h ${mins}m`;
    return `${mins}m`;
  };

  const formatSize = (bytes: number | null) => {
    if (!bytes) return 'Unknown';
    const gb = bytes / (1024 ** 3);
    if (gb >= 1) return `${gb.toFixed(1)} GB`;
    const mb = bytes / (1024 ** 2);
    return `${mb.toFixed(0)} MB`;
  };

  type BadgeVariant = 'emerald' | 'cyan' | 'amber' | 'neutral' | 'purple' | 'red';

  const engineColors: Record<string, BadgeVariant> = {
    renpy: 'emerald',
    rpgm_mv: 'purple',
    rpgm_mz: 'purple',
    rpgm_vxace: 'purple',
    unity: 'cyan',
    unreal: 'amber',
    html: 'cyan',
    unknown: 'neutral'
  };

  const completionColors: Record<string, BadgeVariant> = {
    not_started: 'neutral',
    playing: 'cyan',
    completed: 'emerald',
    dropped: 'red',
    on_hold: 'amber'
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
            <Gamepad2 size={24} className="text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-text-primary">Game Library</h1>
            <p className="text-text-secondary text-sm">
              {stats ? `${stats.total_games} games · ${stats.total_playtime_hours}h played · ${stats.total_size_gb} GB` : 'Loading...'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {activeSession && (
            <Button variant="secondary" onClick={endSession}>
              <Pause size={16} className="mr-2" />
              Stop Session
            </Button>
          )}
          <Button variant="secondary" onClick={() => setShowScanModal(true)}>
            <Folder size={16} className="mr-2" />
            Scan
          </Button>
          <Button variant="primary" onClick={() => setShowAddModal(true)}>
            <Plus size={16} className="mr-2" />
            Add Game
          </Button>
        </div>
      </div>

      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {activeTab === 'LIBRARY' && (
        <div className="space-y-4">
          {/* Filters */}
          <Card className="p-4">
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex-1 min-w-[200px]">
                <div className="relative">
                  <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
                  <input
                    type="text"
                    placeholder="Search games..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-surface-raised border border-border rounded-lg pl-10 pr-4 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>
              </div>
              <select
                value={engineFilter}
                onChange={(e) => setEngineFilter(e.target.value)}
                className="bg-surface-raised border border-border rounded-lg px-3 py-2 text-sm text-text-primary"
              >
                <option value="">All Engines</option>
                <option value="renpy">Ren'Py</option>
                <option value="rpgm_mv">RPGM MV</option>
                <option value="rpgm_mz">RPGM MZ</option>
                <option value="rpgm_vxace">RPGM VX Ace</option>
                <option value="unity">Unity</option>
                <option value="unreal">Unreal</option>
                <option value="html">HTML</option>
              </select>
              <select
                value={completionFilter}
                onChange={(e) => setCompletionFilter(e.target.value)}
                className="bg-surface-raised border border-border rounded-lg px-3 py-2 text-sm text-text-primary"
              >
                <option value="">All Status</option>
                <option value="not_started">Not Started</option>
                <option value="playing">Playing</option>
                <option value="completed">Completed</option>
                <option value="dropped">Dropped</option>
                <option value="on_hold">On Hold</option>
              </select>
              <Button
                variant={showFavorites ? 'primary' : 'secondary'}
                onClick={() => setShowFavorites(!showFavorites)}
                size="sm"
              >
                <Heart size={16} className={showFavorites ? 'fill-current' : ''} />
              </Button>
              <div className="flex border border-border rounded-lg overflow-hidden">
                <button
                  onClick={() => setViewMode('grid')}
                  className={`p-2 ${viewMode === 'grid' ? 'bg-purple-500 text-white' : 'bg-surface-raised text-text-secondary'}`}
                >
                  <Grid size={16} />
                </button>
                <button
                  onClick={() => setViewMode('list')}
                  className={`p-2 ${viewMode === 'list' ? 'bg-purple-500 text-white' : 'bg-surface-raised text-text-secondary'}`}
                >
                  <List size={16} />
                </button>
              </div>
            </div>
          </Card>

          {/* Games Grid/List */}
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="animate-spin text-purple-500" size={32} />
            </div>
          ) : games.length === 0 ? (
            <Card className="p-12 text-center">
              <Gamepad2 size={48} className="mx-auto mb-4 text-text-tertiary" />
              <h3 className="text-lg font-medium text-text-primary mb-2">No games yet</h3>
              <p className="text-text-secondary mb-4">Add games manually or scan a directory</p>
              <Button variant="primary" onClick={() => setShowAddModal(true)}>
                <Plus size={16} className="mr-2" />
                Add Your First Game
              </Button>
            </Card>
          ) : viewMode === 'grid' ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
              {games.map(game => (
                <Card
                  key={game.id}
                  className="overflow-hidden cursor-pointer hover:ring-2 hover:ring-purple-500 transition-all"
                  onClick={() => setSelectedGame(game)}
                >
                  <div className="aspect-[3/4] bg-surface-raised relative">
                    {game.cover_path ? (
                      <img src={game.cover_path} alt={game.title} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Gamepad2 size={48} className="text-text-tertiary" />
                      </div>
                    )}
                    {game.favorite && (
                      <div className="absolute top-2 right-2">
                        <Heart size={20} className="text-pink-500 fill-current" />
                      </div>
                    )}
                    <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-3">
                      <Badge variant={engineColors[game.engine] || 'neutral'}>
                        {game.engine.toUpperCase()}
                      </Badge>
                    </div>
                  </div>
                  <div className="p-3">
                    <h3 className="font-medium text-text-primary truncate">{game.title}</h3>
                    <p className="text-xs text-text-secondary truncate">{game.developer || 'Unknown developer'}</p>
                    <div className="flex items-center gap-2 mt-2 text-xs text-text-tertiary">
                      <Clock size={12} />
                      <span>{formatPlaytime(game.playtime_seconds)}</span>
                      <Badge variant={completionColors[game.completion_status] || 'neutral'}>
                        {game.completion_status.replace('_', ' ')}
                      </Badge>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {games.map(game => (
                <Card
                  key={game.id}
                  className="p-4 flex items-center gap-4 cursor-pointer hover:ring-2 hover:ring-purple-500 transition-all"
                  onClick={() => setSelectedGame(game)}
                >
                  <div className="w-16 h-20 bg-surface-raised rounded-lg flex items-center justify-center flex-shrink-0">
                    {game.cover_path ? (
                      <img src={game.cover_path} alt={game.title} className="w-full h-full object-cover rounded-lg" />
                    ) : (
                      <Gamepad2 size={24} className="text-text-tertiary" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-text-primary truncate">{game.title}</h3>
                      {game.favorite && <Heart size={14} className="text-pink-500 fill-current flex-shrink-0" />}
                    </div>
                    <p className="text-sm text-text-secondary truncate">{game.developer || 'Unknown developer'}</p>
                    <div className="flex items-center gap-3 mt-1">
                      <Badge variant={engineColors[game.engine] || 'neutral'}>
                        {game.engine.toUpperCase()}
                      </Badge>
                      <Badge variant={completionColors[game.completion_status] || 'neutral'}>
                        {game.completion_status.replace('_', ' ')}
                      </Badge>
                      {game.tags.slice(0, 3).map(tag => (
                        <span key={tag} className="text-xs text-text-tertiary">#{tag}</span>
                      ))}
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className="flex items-center gap-1 text-text-secondary">
                      <Clock size={14} />
                      <span className="text-sm">{formatPlaytime(game.playtime_seconds)}</span>
                    </div>
                    <div className="text-xs text-text-tertiary mt-1">{formatSize(game.size_bytes)}</div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'STATS' && stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Card className="p-6">
            <h3 className="text-lg font-medium text-text-primary mb-4">Library Overview</h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-text-secondary">Total Games</span>
                <span className="text-2xl font-bold text-purple-500">{stats.total_games}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-text-secondary">Total Playtime</span>
                <span className="text-2xl font-bold text-emerald-500">{stats.total_playtime_hours}h</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-text-secondary">Total Size</span>
                <span className="text-2xl font-bold text-cyan-500">{stats.total_size_gb} GB</span>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="text-lg font-medium text-text-primary mb-4">By Engine</h3>
            <div className="space-y-3">
              {Object.entries(stats.by_engine).map(([engine, count]) => (
                <div key={engine} className="flex items-center gap-3">
                  <Badge variant={engineColors[engine] || 'neutral'}>{engine}</Badge>
                  <div className="flex-1">
                    <ProgressBar value={(count / stats.total_games) * 100} colorClass="bg-purple-500" />
                  </div>
                  <span className="text-sm text-text-secondary w-8 text-right">{count}</span>
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="text-lg font-medium text-text-primary mb-4">Completion Status</h3>
            <div className="space-y-3">
              {Object.entries(stats.by_completion).map(([status, count]) => (
                <div key={status} className="flex items-center gap-3">
                  <Badge variant={completionColors[status] || 'neutral'}>
                    {status.replace('_', ' ')}
                  </Badge>
                  <div className="flex-1">
                    <ProgressBar value={(count / stats.total_games) * 100} colorClass="bg-emerald-500" />
                  </div>
                  <span className="text-sm text-text-secondary w-8 text-right">{count}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {activeTab === 'IMPORT' && (
        <div className="space-y-6">
          <Card className="p-6">
            <h3 className="text-lg font-medium text-text-primary mb-4">Scan Directory for Games</h3>
            <div className="flex gap-4">
              <input
                type="text"
                placeholder="/mnt/user/games"
                value={scanPath}
                onChange={(e) => setScanPath(e.target.value)}
                className="flex-1 bg-surface-raised border border-border rounded-lg px-4 py-2 text-text-primary focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
              <Button variant="primary" onClick={scanDirectory} disabled={scanning}>
                {scanning ? <Loader2 className="animate-spin mr-2" size={16} /> : <Search size={16} className="mr-2" />}
                Scan
              </Button>
            </div>
          </Card>

          {scannedGames.length > 0 && (
            <Card className="p-6">
              <h3 className="text-lg font-medium text-text-primary mb-4">Found {scannedGames.length} Games</h3>
              <div className="space-y-3">
                {scannedGames.map(game => (
                  <div key={game.path} className="flex items-center justify-between p-4 bg-surface-raised rounded-lg">
                    <div>
                      <h4 className="font-medium text-text-primary">{game.name}</h4>
                      <div className="flex items-center gap-3 mt-1">
                        <Badge variant={engineColors[game.engine] as any || 'gray'}>{game.engine}</Badge>
                        <span className="text-xs text-text-tertiary">{formatSize(game.size_bytes)}</span>
                      </div>
                    </div>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => importGame(game)}
                      disabled={importing === game.path}
                    >
                      {importing === game.path ? (
                        <Loader2 className="animate-spin" size={16} />
                      ) : (
                        <>
                          <Download size={16} className="mr-2" />
                          Import
                        </>
                      )}
                    </Button>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Game Detail Modal */}
      {selectedGame && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedGame(null)}>
          <div onClick={(e) => e.stopPropagation()}>
          <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-start mb-4">
                <div className="flex gap-4">
                  <div className="w-24 h-32 bg-surface-raised rounded-lg flex items-center justify-center flex-shrink-0">
                    {selectedGame.cover_path ? (
                      <img src={selectedGame.cover_path} alt={selectedGame.title} className="w-full h-full object-cover rounded-lg" />
                    ) : (
                      <Gamepad2 size={32} className="text-text-tertiary" />
                    )}
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-text-primary">{selectedGame.title}</h2>
                    <p className="text-text-secondary">{selectedGame.developer || 'Unknown developer'}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <Badge variant={engineColors[selectedGame.engine] || 'neutral'}>
                        {selectedGame.engine.toUpperCase()}
                      </Badge>
                      {selectedGame.version && (
                        <Badge variant="neutral">v{selectedGame.version}</Badge>
                      )}
                    </div>
                  </div>
                </div>
                <button onClick={() => setSelectedGame(null)} className="text-text-tertiary hover:text-text-primary">
                  <X size={24} />
                </button>
              </div>

              {selectedGame.description && (
                <p className="text-text-secondary text-sm mb-4 line-clamp-3">{selectedGame.description}</p>
              )}

              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="bg-surface-raised rounded-lg p-4">
                  <div className="flex items-center gap-2 text-text-tertiary mb-1">
                    <Clock size={14} />
                    <span className="text-xs">Playtime</span>
                  </div>
                  <span className="text-lg font-bold text-text-primary">{formatPlaytime(selectedGame.playtime_seconds)}</span>
                </div>
                <div className="bg-surface-raised rounded-lg p-4">
                  <div className="flex items-center gap-2 text-text-tertiary mb-1">
                    <HardDrive size={14} />
                    <span className="text-xs">Size</span>
                  </div>
                  <span className="text-lg font-bold text-text-primary">{formatSize(selectedGame.size_bytes)}</span>
                </div>
              </div>

              {selectedGame.tags.length > 0 && (
                <div className="mb-4">
                  <div className="flex items-center gap-2 text-text-tertiary mb-2">
                    <Tag size={14} />
                    <span className="text-xs">Tags</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {selectedGame.tags.map(tag => (
                      <span key={tag} className="px-2 py-1 bg-surface-raised rounded text-xs text-text-secondary">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div className="mb-4">
                <div className="text-text-tertiary text-xs mb-2">Completion Status</div>
                <div className="flex gap-2">
                  {['not_started', 'playing', 'completed', 'dropped', 'on_hold'].map(status => (
                    <Button
                      key={status}
                      variant={selectedGame.completion_status === status ? 'primary' : 'secondary'}
                      size="sm"
                      onClick={() => updateCompletion(selectedGame, status)}
                    >
                      {status.replace('_', ' ')}
                    </Button>
                  ))}
                </div>
              </div>

              <div className="flex justify-between items-center pt-4 border-t border-border">
                <div className="flex gap-2">
                  <Button variant="secondary" onClick={() => toggleFavorite(selectedGame)}>
                    <Heart size={16} className={selectedGame.favorite ? 'fill-current text-pink-500' : ''} />
                  </Button>
                  {selectedGame.vndb_id && (
                    <Button
                      variant="secondary"
                      onClick={() => window.open(`https://vndb.org/${selectedGame.vndb_id}`, '_blank')}
                    >
                      <ExternalLink size={16} className="mr-2" />
                      VNDB
                    </Button>
                  )}
                </div>
                <Button
                  variant="primary"
                  onClick={() => startSession(selectedGame.id)}
                  disabled={!!activeSession}
                >
                  <Play size={16} className="mr-2" />
                  Start Playing
                </Button>
              </div>
            </div>
          </Card>
          </div>
        </div>
      )}

      {/* Add Game Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowAddModal(false)}>
          <div onClick={(e) => e.stopPropagation()}>
          <Card className="w-full max-w-lg">
            <div className="p-6">
              <h2 className="text-xl font-bold text-text-primary mb-4">Add New Game</h2>

              <div className="space-y-4">
                <div>
                  <label className="text-sm text-text-secondary">Search VNDB</label>
                  <div className="flex gap-2 mt-1">
                    <input
                      type="text"
                      placeholder="Search for game..."
                      value={vndbSearchQuery}
                      onChange={(e) => setVndbSearchQuery(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && searchVNDB()}
                      className="flex-1 bg-surface-raised border border-border rounded-lg px-3 py-2 text-sm text-text-primary"
                    />
                    <Button variant="secondary" onClick={searchVNDB} disabled={searchingVndb}>
                      {searchingVndb ? <Loader2 className="animate-spin" size={16} /> : <Search size={16} />}
                    </Button>
                  </div>
                </div>

                {vndbResults.length > 0 && (
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {vndbResults.map(result => (
                      <div
                        key={result.id}
                        className="p-3 bg-surface-raised rounded-lg cursor-pointer hover:ring-2 hover:ring-purple-500"
                        onClick={() => {
                          setNewGame({
                            title: result.title,
                            developer: result.developers[0] || '',
                            engine: 'renpy',
                            tags: result.tags.slice(0, 5).join(', ')
                          });
                          setVndbResults([]);
                        }}
                      >
                        <div className="font-medium text-text-primary">{result.title}</div>
                        <div className="text-xs text-text-secondary">{result.developers.join(', ')}</div>
                      </div>
                    ))}
                  </div>
                )}

                <div>
                  <label className="text-sm text-text-secondary">Title *</label>
                  <input
                    type="text"
                    value={newGame.title}
                    onChange={(e) => setNewGame({ ...newGame, title: e.target.value })}
                    className="w-full bg-surface-raised border border-border rounded-lg px-3 py-2 text-sm text-text-primary mt-1"
                  />
                </div>

                <div>
                  <label className="text-sm text-text-secondary">Developer</label>
                  <input
                    type="text"
                    value={newGame.developer}
                    onChange={(e) => setNewGame({ ...newGame, developer: e.target.value })}
                    className="w-full bg-surface-raised border border-border rounded-lg px-3 py-2 text-sm text-text-primary mt-1"
                  />
                </div>

                <div>
                  <label className="text-sm text-text-secondary">Engine</label>
                  <select
                    value={newGame.engine}
                    onChange={(e) => setNewGame({ ...newGame, engine: e.target.value })}
                    className="w-full bg-surface-raised border border-border rounded-lg px-3 py-2 text-sm text-text-primary mt-1"
                  >
                    <option value="unknown">Unknown</option>
                    <option value="renpy">Ren'Py</option>
                    <option value="rpgm_mv">RPGM MV</option>
                    <option value="rpgm_mz">RPGM MZ</option>
                    <option value="rpgm_vxace">RPGM VX Ace</option>
                    <option value="unity">Unity</option>
                    <option value="unreal">Unreal</option>
                    <option value="html">HTML</option>
                  </select>
                </div>

                <div>
                  <label className="text-sm text-text-secondary">Tags (comma-separated)</label>
                  <input
                    type="text"
                    value={newGame.tags}
                    onChange={(e) => setNewGame({ ...newGame, tags: e.target.value })}
                    placeholder="visual novel, dating sim, college"
                    className="w-full bg-surface-raised border border-border rounded-lg px-3 py-2 text-sm text-text-primary mt-1"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 mt-6">
                <Button variant="secondary" onClick={() => setShowAddModal(false)}>Cancel</Button>
                <Button variant="primary" onClick={addGame} disabled={!newGame.title}>Add Game</Button>
              </div>
            </div>
          </Card>
          </div>
        </div>
      )}
    </div>
  );
};

export default Games;
