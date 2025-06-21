import React, { useState } from 'react';
import { FileText, Upload as UploadIcon, Settings } from 'lucide-react';
import { DocumentUpload } from '@/components/Upload/DocumentUpload';
import DocumentManager from '@/components/Document/DocumentManager';
import { DocumentUploadResponse } from '@/types';

export const DocumentsPage: React.FC = () => {
  const [uploadedDocuments, setUploadedDocuments] = useState<DocumentUploadResponse[]>([]);
  const [activeTab, setActiveTab] = useState<'upload' | 'manage'>('upload');

  const handleUploadComplete = (response: DocumentUploadResponse) => {
    setUploadedDocuments(prev => [...prev, response]);
  };

  const handleDocumentDeleted = (documentId: string) => {
    // Remove from recent uploads if it exists there
    setUploadedDocuments(prev => prev.filter(doc => doc.document_id !== documentId));
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center space-x-3">
        <FileText className="w-8 h-8 text-primary-600" />
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            ドキュメント管理
          </h1>
          <p className="text-gray-600 mt-1">
            PDFファイルをアップロードしてRAGシステムで利用可能にします
          </p>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-gray-200">
        <button
          onClick={() => setActiveTab('upload')}
          className={`px-6 py-3 text-sm font-medium border-b-2 ${
            activeTab === 'upload'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <UploadIcon className="w-4 h-4 inline mr-2" />
          ドキュメントアップロード
        </button>
        <button
          onClick={() => setActiveTab('manage')}
          className={`px-6 py-3 text-sm font-medium border-b-2 ${
            activeTab === 'manage'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <Settings className="w-4 h-4 inline mr-2" />
          ドキュメント管理
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'upload' ? (
        <>
          {/* Upload Section */}
          <div className="card">
        <div className="flex items-center space-x-2 mb-6">
          <UploadIcon className="w-5 h-5 text-gray-700" />
          <h2 className="text-xl font-semibold text-gray-900">
            新しいドキュメントをアップロード
          </h2>
        </div>
        
        <DocumentUpload 
          onUploadComplete={handleUploadComplete}
        />
      </div>

      {/* Recent Uploads */}
      {uploadedDocuments.length > 0 && (
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            最近アップロードしたドキュメント
          </h2>
          
          <div className="space-y-3">
            {uploadedDocuments.map((doc) => (
              <div
                key={doc.document_id}
                className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200"
              >
                <div className="flex items-center space-x-3">
                  <FileText className="w-5 h-5 text-primary-600" />
                  <div>
                    <p className="font-medium text-gray-900">
                      {doc.filename}
                    </p>
                    <p className="text-sm text-gray-500">
                      ID: {doc.document_id}
                    </p>
                  </div>
                </div>
                
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-900">
                    {(doc.file_size / 1024 / 1024).toFixed(2)} MB
                  </p>
                  <p className="text-xs text-gray-500">
                    アップロード時間: {doc.upload_time.toFixed(2)}秒
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

          {/* Instructions */}
          <div className="card bg-blue-50 border-blue-200">
            <h3 className="text-lg font-semibold text-blue-900 mb-3">
              使用方法
            </h3>
            <div className="space-y-2 text-blue-800">
              <p className="flex items-start space-x-2">
                <span className="font-bold">1.</span>
                <span>PDFファイルをドラッグ&ドロップまたはクリックして選択</span>
              </p>
              <p className="flex items-start space-x-2">
                <span className="font-bold">2.</span>
                <span>オプションでドキュメント名を入力</span>
              </p>
              <p className="flex items-start space-x-2">
                <span className="font-bold">3.</span>
                <span>「アップロード開始」ボタンをクリック</span>
              </p>
              <p className="flex items-start space-x-2">
                <span className="font-bold">4.</span>
                <span>処理完了後、チャット画面で質問応答が可能</span>
              </p>
            </div>
          </div>
        </>
      ) : (
        <div className="card">
          <DocumentManager onDocumentDeleted={handleDocumentDeleted} />
        </div>
      )}
    </div>
  );
};