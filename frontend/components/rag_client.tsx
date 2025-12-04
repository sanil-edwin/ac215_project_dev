/**
 * RAG Chat Client Components for AgriGuard
 * Integrates with API Orchestrator for intelligent agricultural chatbot
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

interface AgriContextData {
  fips?: string;
  county?: string;
  week?: number;
  year?: number;
  csi_overall?: number;
  water_stress?: number;
  heat_stress?: number;
  vegetation_health?: number;
  atmospheric_stress?: number;
  predicted_yield?: number;
  yield_uncertainty?: number;
  recommendations?: string;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources_used?: number;
  has_live_data?: boolean;
  county?: string;
  mcsi_summary?: string;
  yield_summary?: string;
}

interface ChatResponse {
  response: string;
  sources_used: number;
  has_live_data: boolean;
  county: string | null;
  mcsi_summary: string | null;
  yield_summary: string | null;
}

interface HealthStatus {
  status: string;
  services: {
    mcsi: string;
    yield: string;
    rag: string;
  };
}

// ============================================================================
// CUSTOM HOOKS
// ============================================================================

/**
 * Hook for RAG chat functionality via API Orchestrator
 */
const useRAGChat = (apiUrl: string) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(
    async (
      message: string,
      fips?: string,
      week?: number,
      includeLiveData = true,
      stressData?: {
        overall_stress?: number;
        water_stress?: number;
        heat_stress?: number;
        vegetation_health?: number;
        atmospheric_stress?: number;
        predicted_yield?: number;
        yield_uncertainty?: number;
      }
    ): Promise<void> => {
      if (!message.trim()) return;

      setLoading(true);
      setError(null);

      try {
        // Add user message to history
        const userMessage: ChatMessage = {
          role: 'user',
          content: message,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, userMessage]);

        // Call API Orchestrator /chat endpoint
        const response = await fetch(`${apiUrl}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message,
            fips: fips || null,
            week: week || null,
            include_live_data: includeLiveData,
            stress_data: stressData || null,
          }),
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`API error: ${response.status} - ${errorText}`);
        }

        const data: ChatResponse = await response.json();

        // Add assistant message to history
        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: data.response,
          timestamp: new Date().toISOString(),
          sources_used: data.sources_used,
          has_live_data: data.has_live_data,
          county: data.county || undefined,
          mcsi_summary: data.mcsi_summary || undefined,
          yield_summary: data.yield_summary || undefined,
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Unknown error';
        setError(errorMsg);
        console.error('Chat error:', err);
      } finally {
        setLoading(false);
      }
    },
    [apiUrl]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    loading,
    error,
    sendMessage,
    clearMessages,
  };
};

/**
 * Hook for health checks via API Orchestrator
 */
const useRAGHealth = (apiUrl: string, interval = 30000) => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [isHealthy, setIsHealthy] = useState(false);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch(`${apiUrl}/health`);
        if (response.ok) {
          const data: HealthStatus = await response.json();
          setHealth(data);
          setIsHealthy(data.status === 'healthy');
        }
      } catch (err) {
        console.error('Health check failed:', err);
        setIsHealthy(false);
      }
    };

    checkHealth();
    const timer = setInterval(checkHealth, interval);
    return () => clearInterval(timer);
  }, [apiUrl, interval]);

  return { health, isHealthy };
};

/**
 * Hook for direct vector search (testing/debugging)
 */
const useRAGQuery = (apiUrl: string) => {
  const [results, setResults] = useState<Array<{ text: string; score: number }>>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const query = useCallback(
    async (queryText: string, topK = 5): Promise<void> => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(`${apiUrl}/query`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: queryText,
            top_k: topK,
          }),
        });

        if (!response.ok) {
          throw new Error(`Query error: ${response.status}`);
        }

        const data = await response.json();
        setResults(data.results || []);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Unknown error';
        setError(errorMsg);
        console.error('Query error:', err);
      } finally {
        setLoading(false);
      }
    },
    [apiUrl]
  );

  return { results, loading, error, query };
};

// ============================================================================
// UI COMPONENTS
// ============================================================================

/**
 * Chat message component
 */
const ChatMessageComponent: React.FC<{
  message: ChatMessage;
  showSources?: boolean;
}> = ({ message, showSources = false }) => {
  const isUser = message.role === 'user';

  return (
    <div className={`flex mb-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-md px-4 py-3 rounded-lg ${
          isUser
            ? 'bg-blue-500 text-white rounded-br-none'
            : 'bg-gray-200 text-gray-800 rounded-bl-none'
        }`}
      >
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        <p className={`text-xs mt-2 ${isUser ? 'text-blue-100' : 'text-gray-600'}`}>
          {new Date(message.timestamp).toLocaleTimeString()}
        </p>

        {!isUser && showSources && (
          <div className="mt-2 text-xs border-t border-gray-300 pt-2 space-y-1">
            {message.sources_used !== undefined && (
              <p>📚 Sources: {message.sources_used}</p>
            )}
            {message.has_live_data && (
              <p>📡 Live data included</p>
            )}
            {message.county && (
              <p>📍 County: {message.county}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Main AgriBot chat component
 */
interface AgriBotProps {
  apiUrl: string;
  fips?: string;
  county?: string;
  week?: number;
  currentData?: {
    overall_stress_index?: number;
    water_stress_index?: { value: number };
    heat_stress_index?: { value: number };
    vegetation_health_index?: { value: number };
    atmospheric_stress_index?: { value: number };
  };
  yield_?: {
    predicted_yield?: number;
    uncertainty?: number;
  };
  recommendations?: string;
  showSources?: boolean;
}

const AgriBot: React.FC<AgriBotProps> = ({
  apiUrl,
  fips,
  county,
  week,
  currentData,
  yield_,
  recommendations,
  showSources = true,
}) => {
  const { messages, loading, error, sendMessage, clearMessages } = useRAGChat(apiUrl);
  const { isHealthy } = useRAGHealth(apiUrl);
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [showSourcesLocal, setShowSourcesLocal] = useState(showSources);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || loading) return;
    // Pass week and stress data to sendMessage
    const stressData = {
      overall_stress: currentData?.overall_stress_index,
      water_stress: currentData?.water_stress_index?.value,
      heat_stress: currentData?.heat_stress_index?.value,
      vegetation_health: currentData?.vegetation_health_index?.value,
      atmospheric_stress: currentData?.atmospheric_stress_index?.value,
      predicted_yield: yield_?.predicted_yield,
      yield_uncertainty: yield_?.uncertainty,
    };
    await sendMessage(inputValue, fips, week, true, stressData);
    setInputValue('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !loading) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  if (!isHealthy) {
    return (
      <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <p className="text-yellow-800 font-semibold">⚠️ RAG Service Unavailable</p>
        <p className="text-yellow-700 text-sm mt-1">
          The AI chatbot is currently unavailable. Please try again later.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-lg border border-gray-200">
      {/* Header */}
      <div className="bg-gradient-to-r from-green-600 to-blue-600 text-white px-4 py-3 rounded-t-lg flex justify-between items-center">
        <div>
          <h3 className="font-bold text-lg">💬 AgriBot Assistant</h3>
          <p className="text-xs text-green-100">Ask questions about corn stress, yields, or farming practices. AgriBot uses AI to provide intelligent insights based on your current data.</p>
        </div>
        {(county || fips) && (
          <div className="text-right text-sm">
            <p className="font-semibold">{county || fips}</p>
            {week && <p className="text-xs text-green-100">Week {week}</p>}
          </div>
        )}
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2 min-h-[300px] max-h-[500px]">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 py-8">
            <p className="text-4xl mb-4">🌽</p>
            <p className="text-sm">
              👋 Welcome! Ask me about corn stress, yields, or farming practices.
            </p>
            <p className="text-xs mt-2">
              {fips || county
                ? `Analyzing ${county || `FIPS ${fips}`} - Week ${week || 'current'}`
                : 'Select a county to get live data insights'}
            </p>
          </div>
        )}
        {messages.map((msg, idx) => (
          <ChatMessageComponent
            key={idx}
            message={msg}
            showSources={showSourcesLocal}
          />
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-200 text-gray-800 px-4 py-3 rounded-lg rounded-bl-none">
              <p className="text-sm">🤖 AgriBot is thinking...</p>
            </div>
          </div>
        )}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-2 rounded text-sm">
            Error: {error}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 p-4 space-y-2">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about stress, yield, or farming practices..."
            disabled={loading || !isHealthy}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
          />
          <button
            onClick={handleSendMessage}
            disabled={loading || !isHealthy || !inputValue.trim()}
            className="bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 text-white px-4 py-2 rounded-lg font-medium transition-colors"
          >
            {loading ? '...' : '📤'}
          </button>
        </div>

        {/* Options */}
        <div className="flex justify-between text-xs">
          <label className="flex items-center gap-1 cursor-pointer text-gray-600 hover:text-gray-800">
            <input
              type="checkbox"
              checked={showSourcesLocal}
              onChange={(e) => setShowSourcesLocal(e.target.checked)}
              className="w-4 h-4"
            />
            Show sources
          </label>
          {messages.length > 0 && (
            <button
              onClick={clearMessages}
              className="text-gray-600 hover:text-gray-800 underline"
            >
              Clear chat
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// EXPORT
// ============================================================================

export {
  AgriBot,
  ChatMessageComponent,
  useRAGChat,
  useRAGHealth,
  useRAGQuery,
  type ChatMessage,
  type AgriContextData,
  type ChatResponse,
  type HealthStatus,
};

export default AgriBot;
