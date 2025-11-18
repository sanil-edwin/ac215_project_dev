/**
 * AgriGuard AI Chat Interface
 * Conversational interface for corn stress interpretation and yield guidance
 */

'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, MessageSquare, Loader2, AlertCircle, Bot, User } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: Array<{
    source: string;
    content: string;
  }>;
  context?: {
    county_name?: string;
    mcsi_score?: number;
    stress_level?: string;
  };
}

interface ChatInterfaceProps {
  selectedCounty?: string;
  countyName?: string;
  apiUrl: string;
}

export default function ChatInterface({ 
  selectedCounty, 
  countyName,
  apiUrl 
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Generate conversation ID on mount
  useEffect(() => {
    const convId = `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    setConversationId(convId);
  }, []);

  // Add welcome message
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([{
        role: 'assistant',
        content: `Hello! I'm AgriGuard AI, your agricultural assistant for Iowa corn farming. I can help you:\n\n• Interpret MCSI stress scores\n• Understand yield predictions\n• Get management recommendations\n• Learn about corn stress physiology\n\n${selectedCounty && countyName ? `I see you're viewing ${countyName} County. ` : ''}Ask me anything about your corn crop!`,
        timestamp: new Date().toISOString()
      }]);
    }
  }, []); // Only run once on mount

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiUrl}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: inputMessage,
          county_fips: selectedCounty,
          conversation_id: conversationId
        })
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();

      const assistantMessage: Message = {
        role: 'assistant',
        content: data.response,
        timestamp: data.timestamp,
        sources: data.sources,
        context: data.context
      };

      setMessages(prev => [...prev, assistantMessage]);

    } catch (err) {
      setError('Failed to get response. Please try again.');
      console.error('Chat error:', err);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearChat = () => {
    setMessages([{
      role: 'assistant',
      content: `Chat cleared. ${selectedCounty && countyName ? `You're still viewing ${countyName} County. ` : ''}How can I help you today?`,
      timestamp: new Date().toISOString()
    }]);
    const newConvId = `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    setConversationId(newConvId);
    setError(null);
  };

  const suggestedQuestions = [
    "What does my current MCSI score mean?",
    "How does stress during silking affect yield?",
    "What should I do if I see high stress?",
    "When is the critical period for corn?",
    "How accurate are the yield predictions?"
  ];

  return (
    <div className="bg-white rounded-lg shadow-md">
      {/* Chat Header */}
      <div 
        className="flex items-center justify-between p-4 border-b cursor-pointer hover:bg-gray-50"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          <Bot className="w-6 h-6 text-green-600" />
          <h2 className="text-lg font-semibold text-gray-800">
            AgriGuard AI Assistant
          </h2>
        </div>
        <div className="flex items-center gap-2">
          {selectedCounty && countyName && (
            <span className="text-sm text-gray-600 bg-green-50 px-3 py-1 rounded-full">
              {countyName} County
            </span>
          )}
          <MessageSquare className="w-5 h-5 text-gray-600" />
        </div>
      </div>

      {isExpanded && (
        <>
          {/* Messages Area */}
          <div className="h-96 overflow-y-auto p-4 space-y-4 bg-gray-50">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`flex gap-2 max-w-[80%] ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                  {/* Avatar */}
                  <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                    message.role === 'user' 
                      ? 'bg-blue-600' 
                      : 'bg-green-600'
                  }`}>
                    {message.role === 'user' ? (
                      <User className="w-5 h-5 text-white" />
                    ) : (
                      <Bot className="w-5 h-5 text-white" />
                    )}
                  </div>

                  {/* Message Content */}
                  <div className={`rounded-lg p-3 ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-gray-800 border border-gray-200'
                  }`}>
                    <p className="whitespace-pre-wrap text-sm">{message.content}</p>
                    
                    {/* Context Info */}
                    {message.context && (
                      <div className="mt-2 pt-2 border-t border-gray-300 text-xs text-gray-600">
                        <p>
                          {message.context.county_name && `${message.context.county_name} • `}
                          {message.context.mcsi_score !== undefined && 
                            `MCSI: ${message.context.mcsi_score.toFixed(2)} • `}
                          {message.context.stress_level}
                        </p>
                      </div>
                    )}

                    {/* Sources */}
                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-gray-300">
                        <p className="text-xs font-semibold text-gray-700 mb-1">Sources:</p>
                        {message.sources.map((source, idx) => (
                          <div key={idx} className="text-xs text-gray-600 mb-1">
                            <span className="font-medium">{source.source}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    <p className="text-xs mt-1 opacity-70">
                      {new Date(message.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              </div>
            ))}

            {/* Loading Indicator */}
            {isLoading && (
              <div className="flex justify-start">
                <div className="flex gap-2 items-center">
                  <div className="w-8 h-8 rounded-full bg-green-600 flex items-center justify-center">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                  <div className="bg-white border border-gray-200 rounded-lg p-3">
                    <Loader2 className="w-4 h-4 animate-spin text-gray-600" />
                  </div>
                </div>
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div className="flex justify-center">
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-red-600" />
                  <p className="text-sm text-red-600">{error}</p>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Suggested Questions */}
          {messages.length <= 1 && !isLoading && (
            <div className="p-4 border-t bg-white">
              <p className="text-sm font-medium text-gray-700 mb-2">Suggested questions:</p>
              <div className="flex flex-wrap gap-2">
                {suggestedQuestions.map((question, index) => (
                  <button
                    key={index}
                    onClick={() => setInputMessage(question)}
                    className="text-xs bg-green-50 hover:bg-green-100 text-green-700 px-3 py-1.5 rounded-full transition-colors"
                  >
                    {question}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input Area */}
          <div className="p-4 border-t bg-white">
            <div className="flex gap-2">
              <input
                ref={inputRef}
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask me about corn stress, yields, or management..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                disabled={isLoading}
              />
              <button
                onClick={sendMessage}
                disabled={!inputMessage.trim() || isLoading}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>

            {/* Clear Chat Button */}
            {messages.length > 1 && (
              <button
                onClick={clearChat}
                className="mt-2 text-xs text-gray-600 hover:text-gray-800"
              >
                Clear conversation
              </button>
            )}
          </div>
        </>
      )}

      {/* Collapsed State */}
      {!isExpanded && (
        <div className="p-4 text-center text-sm text-gray-600">
          Click to open AI assistant chat
        </div>
      )}
    </div>
  );
}
