import React, { useState, useEffect } from 'react';
import { MessageCircle, FileText, AlertCircle } from 'lucide-react';
import { ChatInterface } from '@/components/Chat/ChatInterface';
import { DocumentUploadResponse } from '@/types';

export const ChatPage: React.FC = () => {
  const [selectedDocumentId, setSelectedDocumentId] = useState<string>('');
  const [recentDocuments, setRecentDocuments] = useState<DocumentUploadResponse[]>([]);

  // Load recent documents from localStorage (in real app, would fetch from API)
  useEffect(() => {
    const stored = localStorage.getItem('recent_documents');
    if (stored) {
      try {
        const docs = JSON.parse(stored);
        setRecentDocuments(docs);
        if (docs.length > 0 && !selectedDocumentId) {
          setSelectedDocumentId(docs[0].document_id);
        }
      } catch (error) {
        console.error('Failed to load recent documents:', error);
      }
    }
  }, [selectedDocumentId]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-3">
        <MessageCircle className="w-8 h-8 text-primary-600" />
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            質問応答チャット
          </h1>
          <p className="text-gray-600 mt-1">
            アップロードしたドキュメントについて質問してください
          </p>
        </div>
      </div>

      {/* Document Selection */}
      {recentDocuments.length > 0 ? (
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            ドキュメント選択
          </h2>
          
          <div className="space-y-3">
            {recentDocuments.map((doc) => (
              <label
                key={doc.document_id}
                className="flex items-center space-x-3 p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors duration-200"
              >
                <input
                  type="radio"
                  name="document"
                  value={doc.document_id}
                  checked={selectedDocumentId === doc.document_id}
                  onChange={(e) => setSelectedDocumentId(e.target.value)}
                  className="text-primary-600 focus:ring-primary-500"
                />
                <FileText className="w-5 h-5 text-primary-600" />
                <div className="flex-1">
                  <p className="font-medium text-gray-900">
                    {doc.filename}
                  </p>
                  <p className="text-sm text-gray-500">
                    ID: {doc.document_id.slice(0, 8)}...
                  </p>
                </div>
                <div className="text-sm text-gray-500">
                  {(doc.file_size / 1024 / 1024).toFixed(2)} MB
                </div>
              </label>
            ))}
          </div>
        </div>
      ) : (
        <div className="card bg-yellow-50 border-yellow-200">
          <div className="flex items-center space-x-3">
            <AlertCircle className="w-6 h-6 text-yellow-600" />
            <div>
              <h3 className="text-lg font-semibold text-yellow-900">
                ドキュメントがありません
              </h3>
              <p className="text-yellow-800 mt-1">
                チャットを開始するには、まず
                <a href="/" className="font-medium underline hover:no-underline ml-1">
                  ドキュメント管理ページ
                </a>
                でPDFファイルをアップロードしてください。
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Chat Interface */}
      <div className="h-[600px]">
        <ChatInterface documentId={selectedDocumentId} />
      </div>

      {/* Usage Tips */}
      <div className="card bg-blue-50 border-blue-200">
        <h3 className="text-lg font-semibold text-blue-900 mb-3">
          チャット使用のコツ
        </h3>
        <div className="space-y-2 text-blue-800">
          <p className="flex items-start space-x-2">
            <span className="font-bold">•</span>
            <span>具体的で明確な質問をすると、より正確な回答が得られます</span>
          </p>
          <p className="flex items-start space-x-2">
            <span className="font-bold">•</span>
            <span>「参考文書」リンクをクリックすると、回答の根拠となった文書を確認できます</span>
          </p>
          <p className="flex items-start space-x-2">
            <span className="font-bold">•</span>
            <span>信頼度が低い場合は、別の表現で質問を言い換えてみてください</span>
          </p>
          <p className="flex items-start space-x-2">
            <span className="font-bold">•</span>
            <span>処理には数秒かかる場合があります。しばらくお待ちください</span>
          </p>
        </div>
      </div>
    </div>
  );
};