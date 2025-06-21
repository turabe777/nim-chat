import React, { useState, useRef, useEffect } from 'react';
import { Send, MessageCircle, User, Bot, Loader, AlertCircle } from 'lucide-react';
import { clsx } from 'clsx';
import toast from 'react-hot-toast';
import { llmService } from '@/services/api';
import { QuestionAnsweringRequest, ContextItem } from '@/types';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  contexts?: ContextItem[];
  metadata?: {
    confidence?: number;
    model_used?: string;
    processing_time?: number;
    token_usage?: {
      prompt_tokens: number;
      completion_tokens: number;
      total_tokens: number;
    };
  };
}

interface ChatInterfaceProps {
  documentId?: string;
  className?: string;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  documentId,
  className,
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showContexts, setShowContexts] = useState<{ [messageId: string]: boolean }>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!input.trim() || isLoading) return;
    
    if (!documentId) {
      toast.error('ドキュメントが選択されていません');
      return;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const request: QuestionAnsweringRequest = {
        question: input.trim(),
        document_id: documentId,
        context_length: 3,
        similarity_threshold: 0.3,
        model: 'nvidia/llama-3.1-nemotron-70b-instruct',
        max_tokens: 1000,
        temperature: 0.7,
      };

      const response = await llmService.askQuestion(request);

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: response.answer,
        timestamp: new Date(),
        contexts: response.contexts_used,
        metadata: {
          confidence: response.confidence,
          model_used: response.model_used,
          processing_time: response.processing_time,
          token_usage: response.token_usage,
        },
      };

      setMessages(prev => [...prev, assistantMessage]);

    } catch (error: any) {
      toast.error('回答の生成に失敗しました');
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: '申し訳ございませんが、回答を生成できませんでした。もう一度お試しください。',
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleContexts = (messageId: string) => {
    setShowContexts(prev => ({
      ...prev,
      [messageId]: !prev[messageId],
    }));
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('ja-JP', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className={clsx('flex flex-col h-full bg-white rounded-xl shadow-sm border border-gray-200', className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <div className="flex items-center space-x-2">
          <MessageCircle className="w-5 h-5 text-primary-600" />
          <h2 className="text-lg font-semibold text-gray-900">
            質問応答チャット
          </h2>
        </div>
        {documentId && (
          <div className="text-sm text-gray-500">
            ドキュメント: {documentId.slice(0, 8)}...
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center py-8">
            <MessageCircle className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">
              {documentId 
                ? 'ドキュメントについて質問してください'
                : 'まずドキュメントをアップロードしてください'
              }
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={clsx(
                'flex space-x-3',
                message.type === 'user' ? 'justify-end' : 'justify-start'
              )}
            >
              {message.type === 'assistant' && (
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
                    <Bot className="w-4 h-4 text-primary-600" />
                  </div>
                </div>
              )}
              
              <div className={clsx(
                'max-w-[80%] space-y-2',
                message.type === 'user' ? 'order-2' : 'order-1'
              )}>
                <div
                  className={clsx(
                    'px-4 py-2 rounded-lg',
                    message.type === 'user'
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-900'
                  )}
                >
                  <p className="whitespace-pre-wrap">{message.content}</p>
                </div>
                
                <div className={clsx(
                  'flex items-center space-x-2 text-xs text-gray-500',
                  message.type === 'user' ? 'justify-end' : 'justify-start'
                )}>
                  <span>{formatTime(message.timestamp)}</span>
                  {message.metadata?.confidence && (
                    <span>信頼度: {Math.round(message.metadata.confidence * 100)}%</span>
                  )}
                  {message.contexts && message.contexts.length > 0 && (
                    <button
                      onClick={() => toggleContexts(message.id)}
                      className="text-primary-600 hover:text-primary-700 underline"
                    >
                      参考文書 ({message.contexts.length})
                    </button>
                  )}
                </div>

                {/* Contexts */}
                {message.contexts && showContexts[message.id] && (
                  <div className="mt-3 space-y-2">
                    <h4 className="text-sm font-medium text-gray-700">参考文書:</h4>
                    {message.contexts.map((context, index) => (
                      <div
                        key={context.chunk_id}
                        className="p-3 bg-gray-50 rounded-lg border border-gray-200"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-medium text-gray-500">
                            チャンク {index + 1}
                          </span>
                          <span className="text-xs text-gray-500">
                            類似度: {Math.round(context.similarity_score * 100)}%
                          </span>
                        </div>
                        <p className="text-sm text-gray-700">
                          {context.content}
                        </p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Metadata */}
                {message.metadata && (
                  <div className="text-xs text-gray-400 space-x-2">
                    {message.metadata.processing_time && (
                      <span>処理時間: {message.metadata.processing_time.toFixed(2)}s</span>
                    )}
                    {message.metadata.token_usage && (
                      <span>トークン: {message.metadata.token_usage.total_tokens}</span>
                    )}
                  </div>
                )}
              </div>

              {message.type === 'user' && (
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center">
                    <User className="w-4 h-4 text-gray-600" />
                  </div>
                </div>
              )}
            </div>
          ))
        )}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
                <Bot className="w-4 h-4 text-primary-600" />
              </div>
              <div className="bg-gray-100 rounded-lg px-4 py-2 flex items-center space-x-2">
                <Loader className="w-4 h-4 animate-spin text-gray-500" />
                <span className="text-gray-500">考え中...</span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-4">
        {!documentId ? (
          <div className="flex items-center justify-center p-4 bg-yellow-50 rounded-lg border border-yellow-200">
            <AlertCircle className="w-5 h-5 text-yellow-600 mr-2" />
            <span className="text-yellow-700">
              質問するにはまずドキュメントをアップロードしてください
            </span>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex space-x-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="ドキュメントについて質問してください..."
              className="flex-1 input"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              {isLoading ? (
                <Loader className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              <span>送信</span>
            </button>
          </form>
        )}
      </div>
    </div>
  );
};