'use client';

import { useState, useEffect, useRef } from 'react';
import api, { LettaMessage, LettaSendResponse } from '@/lib/api';

const AGENT_ID = 'agent-24d7d80f-2576-457c-be55-9cbf5390576c';
const AGENT_NAME = 'hydra-steward-v2';

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant' | 'reasoning' | 'error';
  content: string;
  timestamp: Date;
}

export function LettaChat() {
  const [isExpanded, setIsExpanded] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Convert Letta messages to chat messages
  const convertMessages = (lettaMessages: LettaMessage[]): ChatMessage[] => {
    return lettaMessages
      .filter(m => m.message_type !== 'system_message')
      .map(m => {
        let type: ChatMessage['type'] = 'assistant';
        if (m.message_type === 'user_message') type = 'user';
        else if (m.message_type === 'reasoning_message') type = 'reasoning';

        // Parse user messages - they may be JSON login events
        let content = m.content;
        if (m.message_type === 'user_message') {
          try {
            const parsed = JSON.parse(m.content);
            if (parsed.type === 'login') {
              content = `[Session started: ${parsed.time}]`;
            }
          } catch {
            // Not JSON, use as-is
          }
        }

        return {
          id: m.id,
          type,
          content,
          timestamp: new Date(m.date),
        };
      });
  };

  // Load message history
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const history = await api.lettaMessages(AGENT_ID);
        setMessages(convertMessages(history));
      } catch (err) {
        console.error('Failed to load chat history:', err);
      } finally {
        setInitialLoading(false);
      }
    };
    loadHistory();
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input when expanded
  useEffect(() => {
    if (isExpanded) {
      inputRef.current?.focus();
    }
  }, [isExpanded]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setError(null);
    setLoading(true);

    // Add user message immediately
    const tempUserMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      type: 'user',
      content: userMessage,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, tempUserMsg]);

    try {
      const response: LettaSendResponse = await api.lettaSendMessage(AGENT_ID, userMessage);

      if (response.error) {
        setError(response.error.message || 'Agent failed to respond');
        setMessages(prev => [...prev, {
          id: `error-${Date.now()}`,
          type: 'error',
          content: response.error?.detail || response.error?.message || 'Unknown error',
          timestamp: new Date(),
        }]);
      } else {
        // Reload full history to get proper message IDs
        const history = await api.lettaMessages(AGENT_ID);
        setMessages(convertMessages(history));
      }
    } catch (err) {
      setError('Failed to send message');
      setMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        type: 'error',
        content: 'Failed to communicate with agent',
        timestamp: new Date(),
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
    if (e.key === 'Escape') {
      setIsExpanded(false);
    }
  };

  // Collapsed state - just a chat bubble
  if (!isExpanded) {
    return (
      <button
        onClick={() => setIsExpanded(true)}
        className="fixed bottom-4 right-4 w-14 h-14 bg-hydra-darker border border-hydra-cyan/50 rounded-full flex items-center justify-center hover:bg-hydra-cyan/20 transition-colors shadow-lg z-50"
        title={`Chat with ${AGENT_NAME}`}
      >
        <svg
          className="w-6 h-6 text-hydra-cyan"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
          />
        </svg>
      </button>
    );
  }

  // Expanded chat window
  return (
    <div className="fixed bottom-4 right-4 w-96 h-[500px] bg-hydra-darker border border-hydra-cyan/30 rounded-lg flex flex-col shadow-xl z-50">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-hydra-gray/30">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-hydra-green animate-pulse" />
          <span className="text-sm font-bold text-hydra-cyan">{AGENT_NAME}</span>
          <span className="text-xs text-gray-500">AI Assistant</span>
        </div>
        <button
          onClick={() => setIsExpanded(false)}
          className="text-gray-500 hover:text-gray-300 text-xl leading-none"
        >
          &times;
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {initialLoading ? (
          <div className="text-center text-gray-500 text-sm">Loading history...</div>
        ) : messages.length === 0 ? (
          <div className="text-center text-gray-500 text-sm">
            Start a conversation with {AGENT_NAME}
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                  msg.type === 'user'
                    ? 'bg-hydra-cyan/20 text-hydra-cyan'
                    : msg.type === 'error'
                    ? 'bg-hydra-red/20 text-hydra-red'
                    : msg.type === 'reasoning'
                    ? 'bg-hydra-gray/10 text-gray-500 italic text-xs'
                    : 'bg-hydra-gray/20 text-gray-300'
                }`}
              >
                {msg.type === 'reasoning' && (
                  <span className="text-hydra-yellow mr-1">[thinking]</span>
                )}
                {msg.content}
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-hydra-gray/20 rounded-lg px-3 py-2 text-sm text-gray-400">
              <span className="animate-pulse">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Error banner */}
      {error && (
        <div className="mx-4 mb-2 p-2 bg-hydra-red/20 border border-hydra-red rounded text-xs text-hydra-red">
          {error}
        </div>
      )}

      {/* Input */}
      <div className="p-3 border-t border-hydra-gray/30">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            disabled={loading}
            className="flex-1 bg-hydra-dark border border-hydra-gray/30 rounded px-3 py-2 text-sm text-gray-300 placeholder-gray-500 focus:outline-none focus:border-hydra-cyan/50"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="px-4 py-2 bg-hydra-cyan/20 hover:bg-hydra-cyan/40 text-hydra-cyan rounded text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
        <div className="mt-2 text-xs text-gray-600 text-center">
          Press Enter to send, Esc to minimize
        </div>
      </div>
    </div>
  );
}
