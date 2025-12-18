import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  Upload,
  FileText,
  Image,
  Link,
  Clipboard,
  CheckCircle,
  AlertCircle,
  Loader2,
  X,
  ChevronDown,
  ChevronUp,
  Lightbulb,
  FileCode,
  File,
  Copy,
  Check,
  RotateCcw,
  Trash2,
  Clock,
  HardDrive,
  FolderOpen
} from 'lucide-react';
import {
  ingestFile,
  ingestClipboard,
  ingestUrlUnified,
  ingestTextContent,
  subscribeToIngestProgress,
  getIngestStatus,
  IngestItem
} from '../services/hydraApi';

// Helper to fetch and update item with full data
const fetchAndUpdateItem = async (
  itemId: string,
  setItems: React.Dispatch<React.SetStateAction<IngestItem[]>>
) => {
  const { data } = await getIngestStatus(itemId);
  if (data) {
    setItems(prev => prev.map(item =>
      item.id === itemId ? { ...item, ...data } : item
    ));
  }
};
import { Badge, ProgressBar, Button } from './UIComponents';

// ============================================================================
// Utilities
// ============================================================================

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

const formatRelativeTime = (dateStr: string): string => {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHr = Math.floor(diffMin / 60);

  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  return date.toLocaleDateString();
};

const getFileTypeFromName = (filename: string): string => {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  const typeMap: Record<string, string> = {
    png: 'image', jpg: 'image', jpeg: 'image', gif: 'image', webp: 'image', svg: 'image',
    pdf: 'pdf',
    txt: 'document', md: 'document', doc: 'document', docx: 'document',
    py: 'code', js: 'code', ts: 'code', jsx: 'code', tsx: 'code',
    json: 'code', yaml: 'code', yml: 'code', css: 'code', html: 'code',
  };
  return typeMap[ext] || 'unknown';
};

// ============================================================================
// Content Type Icons & Colors
// ============================================================================

const contentTypeIcons: Record<string, React.ReactNode> = {
  image: <Image size={16} className="text-purple-400" />,
  pdf: <FileText size={16} className="text-red-400" />,
  document: <FileText size={16} className="text-cyan-400" />,
  code: <FileCode size={16} className="text-emerald-400" />,
  url: <Link size={16} className="text-amber-400" />,
  text: <FileText size={16} className="text-neutral-400" />,
  unknown: <File size={16} className="text-neutral-500" />,
};

const statusColors: Record<string, 'emerald' | 'cyan' | 'amber' | 'neutral' | 'red'> = {
  pending: 'neutral',
  processing: 'cyan',
  extracting: 'cyan',
  analyzing: 'cyan',
  storing: 'amber',
  completed: 'emerald',
  failed: 'red',
};

const statusLabels: Record<string, string> = {
  pending: 'Queued',
  processing: 'Processing',
  extracting: 'Extracting',
  analyzing: 'Analyzing',
  storing: 'Saving',
  completed: 'Done',
  failed: 'Failed',
};

// ============================================================================
// Queued File Preview Component
// ============================================================================

interface QueuedFile {
  id: string;
  file: File;
  preview?: string;
  status: 'queued' | 'uploading' | 'done' | 'error';
  error?: string;
}

interface QueuedFileCardProps {
  item: QueuedFile;
  onRemove: () => void;
}

const QueuedFileCard: React.FC<QueuedFileCardProps> = ({ item, onRemove }) => {
  const isImage = item.file.type.startsWith('image/');

  return (
    <div className="flex items-center gap-3 p-2 bg-surface-raised rounded-lg border border-neutral-800">
      {/* Preview/Icon */}
      <div className="w-12 h-12 shrink-0 rounded overflow-hidden bg-neutral-800 flex items-center justify-center">
        {isImage && item.preview ? (
          <img src={item.preview} alt="" className="w-full h-full object-cover" />
        ) : (
          <div className="text-neutral-500">
            {contentTypeIcons[getFileTypeFromName(item.file.name)] || contentTypeIcons.unknown}
          </div>
        )}
      </div>

      {/* File info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-neutral-200 truncate">{item.file.name}</p>
        <p className="text-xs text-neutral-500">{formatFileSize(item.file.size)}</p>
      </div>

      {/* Status/Actions */}
      <div className="shrink-0">
        {item.status === 'queued' && (
          <button
            onClick={onRemove}
            className="p-1.5 text-neutral-500 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
          >
            <X size={16} />
          </button>
        )}
        {item.status === 'uploading' && (
          <Loader2 size={16} className="text-cyan-400 animate-spin" />
        )}
        {item.status === 'done' && (
          <CheckCircle size={16} className="text-emerald-400" />
        )}
        {item.status === 'error' && (
          <AlertCircle size={16} className="text-red-400" />
        )}
      </div>
    </div>
  );
};

// ============================================================================
// Ingest Item Card Component (Results)
// ============================================================================

interface IngestItemCardProps {
  item: IngestItem;
  isExpanded: boolean;
  onToggle: () => void;
  onRetry?: () => void;
  onRemove?: () => void;
}

const IngestItemCard: React.FC<IngestItemCardProps> = ({
  item,
  isExpanded,
  onToggle,
  onRetry,
  onRemove
}) => {
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const isProcessing = ['pending', 'processing', 'extracting', 'analyzing', 'storing'].includes(item.status);

  const copyToClipboard = async (text: string, field: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const CopyButton: React.FC<{ text: string; field: string }> = ({ text, field }) => (
    <button
      onClick={(e) => {
        e.stopPropagation();
        copyToClipboard(text, field);
      }}
      className="p-1 text-neutral-500 hover:text-neutral-300 transition-colors"
      title="Copy to clipboard"
    >
      {copiedField === field ? (
        <Check size={12} className="text-emerald-400" />
      ) : (
        <Copy size={12} />
      )}
    </button>
  );

  return (
    <div className="bg-surface-dim border border-neutral-800 rounded-lg overflow-hidden hover:border-neutral-700 transition-colors">
      {/* Header */}
      <div
        className="px-4 py-3 flex items-center gap-3 cursor-pointer hover:bg-surface-raised/50 transition-colors"
        onClick={onToggle}
      >
        {/* Icon */}
        <div className="shrink-0 p-2 bg-surface-raised rounded">
          {contentTypeIcons[item.content_type] || contentTypeIcons.unknown}
        </div>

        {/* Title/Name */}
        <div className="flex-1 min-w-0">
          <div className="font-medium text-neutral-200 truncate">
            {item.title || item.filename || item.url || 'Processing...'}
          </div>
          <div className="flex items-center gap-2 text-xs text-neutral-500">
            <span>{item.current_step}</span>
            {item.created_at && (
              <>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Clock size={10} />
                  {formatRelativeTime(item.created_at)}
                </span>
              </>
            )}
          </div>
        </div>

        {/* Status */}
        <div className="shrink-0 flex items-center gap-2">
          {isProcessing ? (
            <Loader2 size={16} className="text-cyan-400 animate-spin" />
          ) : item.status === 'completed' ? (
            <CheckCircle size={16} className="text-emerald-400" />
          ) : item.status === 'failed' ? (
            <AlertCircle size={16} className="text-red-400" />
          ) : null}
          <Badge variant={statusColors[item.status] || 'neutral'}>
            {statusLabels[item.status] || item.status}
          </Badge>
        </div>

        {/* Expand toggle */}
        <div className="shrink-0 text-neutral-500">
          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </div>

      {/* Progress bar */}
      {isProcessing && (
        <div className="px-4 pb-2">
          <ProgressBar value={item.progress} colorClass="bg-cyan-500" />
        </div>
      )}

      {/* Expanded content - Completed */}
      {isExpanded && item.status === 'completed' && (
        <div className="px-4 pb-4 pt-2 border-t border-neutral-800 space-y-4">
          {/* Summary */}
          {item.summary && (
            <div className="group">
              <div className="flex items-center justify-between mb-1">
                <div className="text-xs font-medium text-neutral-500 uppercase">Summary</div>
                <CopyButton text={item.summary} field="summary" />
              </div>
              <p className="text-sm text-neutral-300 leading-relaxed">{item.summary}</p>
            </div>
          )}

          {/* Key Insights */}
          {item.key_insights && item.key_insights.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="text-xs font-medium text-neutral-500 uppercase flex items-center gap-1">
                  <Lightbulb size={12} />
                  Key Insights
                </div>
                <CopyButton text={item.key_insights.join('\n• ')} field="insights" />
              </div>
              <ul className="space-y-1.5">
                {item.key_insights.map((insight, i) => (
                  <li key={i} className="text-sm text-neutral-400 flex items-start gap-2">
                    <span className="text-emerald-500 shrink-0 mt-1">•</span>
                    <span>{insight}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Relevance to Hydra */}
          {item.relevance_to_hydra && (
            <div className="group">
              <div className="flex items-center justify-between mb-1">
                <div className="text-xs font-medium text-neutral-500 uppercase">Relevance to Hydra</div>
                <CopyButton text={item.relevance_to_hydra} field="relevance" />
              </div>
              <p className="text-sm text-cyan-300/90 leading-relaxed bg-cyan-500/5 p-2 rounded border border-cyan-500/20">
                {item.relevance_to_hydra}
              </p>
            </div>
          )}

          {/* Action Items */}
          {item.action_items && item.action_items.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="text-xs font-medium text-neutral-500 uppercase">Action Items</div>
                <CopyButton text={item.action_items.join('\n→ ')} field="actions" />
              </div>
              <ul className="space-y-1.5">
                {item.action_items.map((action, i) => (
                  <li key={i} className="text-sm text-amber-300/90 flex items-start gap-2 bg-amber-500/5 p-2 rounded border border-amber-500/20">
                    <span className="shrink-0">→</span>
                    <span>{action}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Tags */}
          {item.tags && item.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-2">
              {item.tags.map((tag, i) => (
                <span key={i} className="px-2 py-0.5 bg-neutral-800 text-neutral-400 text-xs rounded-full border border-neutral-700">
                  #{tag}
                </span>
              ))}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-2 pt-2 border-t border-neutral-800">
            <button
              onClick={(e) => {
                e.stopPropagation();
                const allText = [
                  item.summary,
                  item.key_insights?.join('\n• '),
                  item.relevance_to_hydra,
                  item.action_items?.join('\n→ '),
                ].filter(Boolean).join('\n\n');
                copyToClipboard(allText, 'all');
              }}
              className="text-xs text-neutral-500 hover:text-neutral-300 flex items-center gap-1 transition-colors"
            >
              {copiedField === 'all' ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
              Copy all
            </button>
            {onRemove && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onRemove();
                }}
                className="text-xs text-neutral-500 hover:text-red-400 flex items-center gap-1 transition-colors ml-auto"
              >
                <Trash2 size={12} />
                Remove
              </button>
            )}
          </div>
        </div>
      )}

      {/* Error state */}
      {item.status === 'failed' && (
        <div className="px-4 pb-3 border-t border-neutral-800">
          <div className="text-sm text-red-400 mb-2">
            {item.error || 'An error occurred during processing'}
          </div>
          <div className="flex gap-2">
            {onRetry && (
              <Button
                onClick={(e) => {
                  e.stopPropagation();
                  onRetry();
                }}
                variant="secondary"
                size="sm"
              >
                <RotateCcw size={14} className="mr-1" />
                Retry
              </Button>
            )}
            {onRemove && (
              <Button
                onClick={(e) => {
                  e.stopPropagation();
                  onRemove();
                }}
                variant="ghost"
                size="sm"
              >
                <Trash2 size={14} className="mr-1" />
                Remove
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// Confirmation Modal
// ============================================================================

interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

const ConfirmModal: React.FC<ConfirmModalProps> = ({
  isOpen,
  title,
  message,
  confirmLabel = 'Confirm',
  onConfirm,
  onCancel,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onCancel} />
      <div className="relative bg-surface-raised border border-neutral-700 rounded-lg p-6 max-w-sm w-full mx-4 shadow-xl">
        <h3 className="text-lg font-medium text-neutral-200 mb-2">{title}</h3>
        <p className="text-sm text-neutral-400 mb-4">{message}</p>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onCancel}>Cancel</Button>
          <Button variant="primary" onClick={onConfirm}>{confirmLabel}</Button>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// Main IngestDropZone Component
// ============================================================================

interface IngestDropZoneProps {
  className?: string;
  onIngestComplete?: (item: IngestItem) => void;
}

const STORAGE_KEY = 'hydra-ingest-history';
const MAX_HISTORY = 50;

export const IngestDropZone: React.FC<IngestDropZoneProps> = ({ className = '', onIngestComplete }) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [activeTab, setActiveTab] = useState<'drop' | 'url' | 'text'>('drop');
  const [urlInput, setUrlInput] = useState('');
  const [textInput, setTextInput] = useState('');
  const [textTitle, setTextTitle] = useState('');
  const [topic, setTopic] = useState('');
  const [items, setItems] = useState<IngestItem[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropZoneRef = useRef<HTMLDivElement>(null);

  // Load history from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        // Only load completed items from history
        setItems(parsed.filter((item: IngestItem) => item.status === 'completed').slice(0, MAX_HISTORY));
      }
    } catch (e) {
      console.error('Failed to load ingest history:', e);
    }
  }, []);

  // Save completed items to localStorage
  useEffect(() => {
    const completedItems = items.filter(item => item.status === 'completed').slice(0, MAX_HISTORY);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(completedItems));
    } catch (e) {
      console.error('Failed to save ingest history:', e);
    }
  }, [items]);

  // Generate simple unique ID
  const generateId = () => Math.random().toString(36).substring(2, 10);

  // Handle files - immediately upload them
  const handleFiles = useCallback(async (files: FileList | File[]) => {
    const fileArray = Array.from(files);
    if (fileArray.length === 0) return;

    console.log('handleFiles called with', fileArray.length, 'files');
    setIsUploading(true);

    for (const file of fileArray) {
      console.log('Processing file:', file.name, file.type, file.size);

      try {
        const { data, error } = await ingestFile(file, topic || undefined);
        console.log('ingestFile response:', data, error);

        if (data) {
          const itemWithTimestamp = { ...data, created_at: new Date().toISOString() };
          setItems(prev => [itemWithTimestamp, ...prev]);
          setExpandedId(data.id);

          // Subscribe to progress updates
          subscribeToIngestProgress(
            data.id,
            (event) => {
              setItems(prev => prev.map(item =>
                item.id === event.id
                  ? { ...item, progress: event.progress, current_step: event.step, status: event.status as IngestItem['status'] }
                  : item
              ));
              // When completed, fetch full item data including analysis
              if (event.status === 'completed') {
                fetchAndUpdateItem(event.id, setItems);
              }
            },
            () => onIngestComplete?.(data)
          );
        } else if (error) {
          console.error('Upload failed:', error);
          // Add failed item to show error
          const failedItem: IngestItem = {
            id: generateId(),
            source: 'upload',
            content_type: 'unknown',
            status: 'failed',
            progress: 0,
            current_step: 'failed',
            filename: file.name,
            key_insights: [],
            action_items: [],
            tags: [],
            error: error,
            created_at: new Date().toISOString(),
          };
          setItems(prev => [failedItem, ...prev]);
        }
      } catch (err) {
        console.error('Exception during upload:', err);
      }
    }

    setIsUploading(false);
    // Clear the file input so the same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [topic, onIngestComplete]);

  // Drag & Drop handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFiles(files);
    }

    // Check for dropped URLs
    const text = e.dataTransfer.getData('text');
    if (text && (text.startsWith('http://') || text.startsWith('https://'))) {
      handleUrlSubmit(text);
    }
  }, [handleFiles]);

  // Clipboard paste handler
  useEffect(() => {
    const handlePaste = async (e: ClipboardEvent) => {
      // Only handle paste if focused on drop zone or body
      if (!dropZoneRef.current?.contains(document.activeElement) &&
          document.activeElement?.tagName !== 'BODY') {
        return;
      }

      const clipboardItems = e.clipboardData?.items;
      if (!clipboardItems) return;

      for (const item of Array.from(clipboardItems)) {
        if (item.type.startsWith('image/')) {
          e.preventDefault();
          const blob = item.getAsFile();
          if (blob) {
            const reader = new FileReader();
            reader.onload = async () => {
              const base64 = reader.result as string;
              const { data } = await ingestClipboard(base64, topic || undefined);

              if (data) {
                const itemWithTimestamp = { ...data, created_at: new Date().toISOString() };
                setItems(prev => [itemWithTimestamp, ...prev]);
                setExpandedId(data.id);

                subscribeToIngestProgress(
                  data.id,
                  (event) => {
                    setItems(prev => prev.map(i =>
                      i.id === event.id
                        ? { ...i, progress: event.progress, current_step: event.step, status: event.status as IngestItem['status'] }
                        : i
                    ));
                    if (event.status === 'completed') {
                      fetchAndUpdateItem(event.id, setItems);
                    }
                  }
                );
              }
            };
            reader.readAsDataURL(blob);
          }
        }
      }
    };

    document.addEventListener('paste', handlePaste);
    return () => document.removeEventListener('paste', handlePaste);
  }, [topic]);

  // URL submission
  const handleUrlSubmit = async (url?: string) => {
    const urlToSubmit = url || urlInput;
    if (!urlToSubmit.trim()) return;

    setIsUploading(true);
    const { data } = await ingestUrlUnified(urlToSubmit, topic || undefined);

    if (data) {
      const itemWithTimestamp = { ...data, created_at: new Date().toISOString() };
      setItems(prev => [itemWithTimestamp, ...prev]);
      setExpandedId(data.id);
      setUrlInput('');

      subscribeToIngestProgress(
        data.id,
        (event) => {
          setItems(prev => prev.map(item =>
            item.id === event.id
              ? { ...item, progress: event.progress, current_step: event.step, status: event.status as IngestItem['status'] }
              : item
          ));
          if (event.status === 'completed') {
            fetchAndUpdateItem(event.id, setItems);
          }
        }
      );
    }

    setIsUploading(false);
  };

  // Text submission
  const handleTextSubmit = async () => {
    if (!textInput.trim()) return;

    setIsUploading(true);
    const { data } = await ingestTextContent(textInput, textTitle || undefined, topic || undefined);

    if (data) {
      const itemWithTimestamp = { ...data, created_at: new Date().toISOString() };
      setItems(prev => [itemWithTimestamp, ...prev]);
      setExpandedId(data.id);
      setTextInput('');
      setTextTitle('');

      subscribeToIngestProgress(
        data.id,
        (event) => {
          setItems(prev => prev.map(item =>
            item.id === event.id
              ? { ...item, progress: event.progress, current_step: event.step, status: event.status as IngestItem['status'] }
              : item
          ));
          if (event.status === 'completed') {
            fetchAndUpdateItem(event.id, setItems);
          }
        }
      );
    }

    setIsUploading(false);
  };

  // Remove item from history
  const removeItem = useCallback((id: string) => {
    setItems(prev => prev.filter(item => item.id !== id));
    if (expandedId === id) setExpandedId(null);
  }, [expandedId]);

  // Clear all history
  const clearAllHistory = useCallback(() => {
    setItems([]);
    setExpandedId(null);
    setShowClearConfirm(false);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  const completedCount = items.filter(i => i.status === 'completed').length;
  const processingCount = items.filter(i => ['pending', 'processing', 'extracting', 'analyzing', 'storing'].includes(i.status)).length;

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Tab selector */}
      <div className="flex gap-1 border-b border-neutral-800">
        <button
          onClick={() => setActiveTab('drop')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'drop'
              ? 'border-cyan-500 text-cyan-400'
              : 'border-transparent text-neutral-500 hover:text-neutral-300'
          }`}
        >
          <Upload size={16} />
          Upload
        </button>
        <button
          onClick={() => setActiveTab('url')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'url'
              ? 'border-cyan-500 text-cyan-400'
              : 'border-transparent text-neutral-500 hover:text-neutral-300'
          }`}
        >
          <Link size={16} />
          URL
        </button>
        <button
          onClick={() => setActiveTab('text')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'text'
              ? 'border-cyan-500 text-cyan-400'
              : 'border-transparent text-neutral-500 hover:text-neutral-300'
          }`}
        >
          <FileText size={16} />
          Text
        </button>
      </div>

      {/* Topic input (shared) */}
      <div>
        <label className="text-xs text-neutral-500 mb-1 block">Topic (optional)</label>
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="e.g., Agent frameworks, LLM optimization"
          className="w-full bg-surface-dim border border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-200 placeholder-neutral-600 focus:border-cyan-500 focus:outline-none"
        />
      </div>

      {/* Upload tab */}
      {activeTab === 'drop' && (
        <div className="space-y-4">
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={(e) => {
              console.log('File input changed:', e.target.files);
              if (e.target.files && e.target.files.length > 0) {
                handleFiles(e.target.files);
              }
            }}
            className="hidden"
            accept="image/*,.pdf,.txt,.md,.py,.js,.ts,.json,.yaml,.yml,.jsx,.tsx,.css,.html,.xml,.csv,.log"
          />

          {/* Action buttons */}
          <div className="flex gap-3">
            <Button
              onClick={() => fileInputRef.current?.click()}
              variant="primary"
              className="flex-1 py-3 bg-cyan-600 hover:bg-cyan-500"
              disabled={isUploading}
            >
              <FolderOpen size={18} className="mr-2" />
              Browse Files
            </Button>
            <Button
              onClick={() => {
                navigator.clipboard.read().then(async (items) => {
                  for (const item of items) {
                    if (item.types.includes('image/png') || item.types.includes('image/jpeg')) {
                      const blob = await item.getType(item.types.find(t => t.startsWith('image/')) || 'image/png');
                      const reader = new FileReader();
                      reader.onload = async () => {
                        const base64 = reader.result as string;
                        const { data } = await ingestClipboard(base64, topic || undefined);
                        if (data) {
                          const itemWithTimestamp = { ...data, created_at: new Date().toISOString() };
                          setItems(prev => [itemWithTimestamp, ...prev]);
                          setExpandedId(data.id);
                          subscribeToIngestProgress(data.id, (event) => {
                            setItems(prev => prev.map(i =>
                              i.id === event.id
                                ? { ...i, progress: event.progress, current_step: event.step, status: event.status as IngestItem['status'] }
                                : i
                            ));
                            if (event.status === 'completed') {
                              fetchAndUpdateItem(event.id, setItems);
                            }
                          });
                        }
                      };
                      reader.readAsDataURL(blob);
                    }
                  }
                }).catch(() => {
                  alert('Use Ctrl+V to paste images from clipboard');
                });
              }}
              variant="secondary"
              className="px-4"
              disabled={isUploading}
            >
              <Clipboard size={18} className="mr-2" />
              Paste
            </Button>
          </div>

          {/* Drop zone */}
          <div
            ref={dropZoneRef}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`
              relative border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all
              ${isDragOver
                ? 'border-cyan-500 bg-cyan-500/10'
                : 'border-neutral-700 hover:border-neutral-600 hover:bg-surface-raised'
              }
            `}
          >
            <div className="flex flex-col items-center gap-2">
              <div className={`p-3 rounded-full ${isDragOver ? 'bg-cyan-500/20' : 'bg-surface-raised'}`}>
                <Upload size={24} className={isDragOver ? 'text-cyan-400' : 'text-neutral-500'} />
              </div>
              <div>
                <p className="text-neutral-300 font-medium">
                  {isDragOver ? 'Drop files here' : 'Drag & drop files here'}
                </p>
                <p className="text-xs text-neutral-500 mt-1">
                  Images, PDFs, documents, code files
                </p>
              </div>
            </div>
          </div>

          {/* Keyboard hint */}
          <div className="flex items-center justify-center gap-4 text-xs text-neutral-500">
            <span className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-neutral-800 rounded text-neutral-400">Ctrl</kbd>
              <span>+</span>
              <kbd className="px-1.5 py-0.5 bg-neutral-800 rounded text-neutral-400">V</kbd>
              <span className="ml-1">paste screenshot</span>
            </span>
          </div>
        </div>
      )}

      {/* URL tab */}
      {activeTab === 'url' && (
        <div className="space-y-3">
          <div className="flex gap-2">
            <input
              type="url"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleUrlSubmit()}
              placeholder="https://github.com/user/repo or https://arxiv.org/abs/..."
              className="flex-1 bg-surface-dim border border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-200 placeholder-neutral-600 focus:border-cyan-500 focus:outline-none"
            />
            <Button
              onClick={() => handleUrlSubmit()}
              disabled={!urlInput.trim() || isUploading}
              variant="primary"
            >
              {isUploading ? <Loader2 size={16} className="animate-spin" /> : 'Ingest'}
            </Button>
          </div>
          <p className="text-xs text-neutral-500">
            Supports: Web pages, GitHub repos, arXiv papers
          </p>
        </div>
      )}

      {/* Text tab */}
      {activeTab === 'text' && (
        <div className="space-y-3">
          <input
            type="text"
            value={textTitle}
            onChange={(e) => setTextTitle(e.target.value)}
            placeholder="Title (optional)"
            className="w-full bg-surface-dim border border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-200 placeholder-neutral-600 focus:border-cyan-500 focus:outline-none"
          />
          <textarea
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            placeholder="Paste research notes, article excerpts, or any text content..."
            rows={6}
            className="w-full bg-surface-dim border border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-200 placeholder-neutral-600 focus:border-cyan-500 focus:outline-none resize-none"
          />
          <div className="flex justify-end">
            <Button
              onClick={handleTextSubmit}
              disabled={!textInput.trim() || isUploading}
              variant="primary"
            >
              {isUploading ? <Loader2 size={16} className="animate-spin" /> : 'Analyze Text'}
            </Button>
          </div>
        </div>
      )}

      {/* Results list */}
      {items.length > 0 && (
        <div className="space-y-3 pt-4 border-t border-neutral-800">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-neutral-300 flex items-center gap-2">
              <HardDrive size={14} />
              Ingestion History
              <span className="text-neutral-500 font-normal">
                ({completedCount} completed{processingCount > 0 ? `, ${processingCount} processing` : ''})
              </span>
            </h4>
            {items.length > 0 && (
              <button
                onClick={() => setShowClearConfirm(true)}
                className="text-xs text-neutral-500 hover:text-red-400 flex items-center gap-1 transition-colors"
              >
                <Trash2 size={12} />
                Clear all
              </button>
            )}
          </div>

          <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
            {items.map((item) => (
              <IngestItemCard
                key={item.id}
                item={item}
                isExpanded={expandedId === item.id}
                onToggle={() => setExpandedId(expandedId === item.id ? null : item.id)}
                onRemove={() => removeItem(item.id)}
                onRetry={item.status === 'failed' ? () => {
                  // Re-trigger the ingest for failed items
                  // This would need the original data which we don't have stored
                  // For now, just remove and let user re-upload
                  removeItem(item.id);
                } : undefined}
              />
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {items.length === 0 && (
        <div className="text-center py-8 text-neutral-500">
          <HardDrive size={32} className="mx-auto mb-2 opacity-50" />
          <p>No ingestions yet</p>
          <p className="text-xs mt-1">Upload files, paste screenshots, or submit URLs</p>
        </div>
      )}

      {/* Confirmation modal */}
      <ConfirmModal
        isOpen={showClearConfirm}
        title="Clear History"
        message={`This will remove ${items.length} item(s) from your ingestion history. This action cannot be undone.`}
        confirmLabel="Clear All"
        onConfirm={clearAllHistory}
        onCancel={() => setShowClearConfirm(false)}
      />
    </div>
  );
};

export default IngestDropZone;
