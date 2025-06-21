import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, X, CheckCircle, AlertCircle } from 'lucide-react';
import { clsx } from 'clsx';
import toast from 'react-hot-toast';
import { documentService } from '@/services/api';
import { DocumentUploadResponse } from '@/types';

interface UploadedFile {
  file: File;
  status: 'pending' | 'uploading' | 'success' | 'error';
  response?: DocumentUploadResponse;
  error?: string;
}

interface DocumentUploadProps {
  onUploadComplete?: (response: DocumentUploadResponse) => void;
  className?: string;
}

export const DocumentUpload: React.FC<DocumentUploadProps> = ({
  onUploadComplete,
  className,
}) => {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [documentName, setDocumentName] = useState('');

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map(file => ({
      file,
      status: 'pending' as const,
    }));
    
    setUploadedFiles(prev => [...prev, ...newFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    maxFiles: 10,
    maxSize: 50 * 1024 * 1024, // 50MB
  });

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const uploadFiles = async () => {
    const pendingFiles = uploadedFiles.filter(f => f.status === 'pending');
    
    if (pendingFiles.length === 0) {
      toast.error('アップロードするファイルがありません');
      return;
    }

    // Mark files as uploading
    setUploadedFiles(prev =>
      prev.map(f => 
        f.status === 'pending' ? { ...f, status: 'uploading' } : f
      )
    );

    try {
      const fileList = new DataTransfer();
      pendingFiles.forEach(({ file }) => fileList.items.add(file));

      const response = await documentService.upload(
        fileList.files,
        documentName || undefined
      );

      // Mark files as successful
      setUploadedFiles(prev =>
        prev.map(f =>
          f.status === 'uploading'
            ? { ...f, status: 'success', response }
            : f
        )
      );

      toast.success(`${pendingFiles.length}個のファイルがアップロードされました`);
      
      // Save to localStorage for recent documents
      const recentDocs = JSON.parse(localStorage.getItem('recent_documents') || '[]');
      recentDocs.unshift(response);
      // Keep only last 10 documents
      if (recentDocs.length > 10) {
        recentDocs.splice(10);
      }
      localStorage.setItem('recent_documents', JSON.stringify(recentDocs));
      
      if (onUploadComplete) {
        onUploadComplete(response);
      }

      // Clear document name after successful upload
      setDocumentName('');
      
    } catch (error: any) {
      // Mark files as error
      setUploadedFiles(prev =>
        prev.map(f =>
          f.status === 'uploading'
            ? { ...f, status: 'error', error: error.message }
            : f
        )
      );

      toast.error('アップロードに失敗しました');
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStatusIcon = (status: UploadedFile['status']) => {
    switch (status) {
      case 'pending':
        return <FileText className="w-5 h-5 text-gray-400" />;
      case 'uploading':
        return <div className="w-5 h-5 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />;
      case 'success':
        return <CheckCircle className="w-5 h-5 text-success-500" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-error-500" />;
    }
  };

  const hasUploading = uploadedFiles.some(f => f.status === 'uploading');

  return (
    <div className={clsx('space-y-6', className)}>
      {/* Upload Area */}
      <div
        {...getRootProps()}
        className={clsx(
          'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors duration-200',
          isDragActive
            ? 'border-primary-500 bg-primary-50'
            : 'border-gray-300 hover:border-primary-400 hover:bg-gray-50'
        )}
      >
        <input {...getInputProps()} />
        <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <p className="text-lg font-medium text-gray-900 mb-2">
          {isDragActive ? 'ファイルをドロップしてください' : 'PDFファイルをアップロード'}
        </p>
        <p className="text-sm text-gray-500">
          ドラッグ&ドロップまたはクリックしてファイルを選択
        </p>
        <p className="text-xs text-gray-400 mt-2">
          PDF形式、最大50MB、最大10ファイル
        </p>
      </div>

      {/* Document Name Input */}
      {uploadedFiles.length > 0 && (
        <div>
          <label htmlFor="document-name" className="block text-sm font-medium text-gray-700 mb-2">
            ドキュメント名（オプション）
          </label>
          <input
            id="document-name"
            type="text"
            value={documentName}
            onChange={(e) => setDocumentName(e.target.value)}
            placeholder="ドキュメントに名前を付ける..."
            className="input"
            disabled={hasUploading}
          />
        </div>
      )}

      {/* File List */}
      {uploadedFiles.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-gray-700">
            アップロード予定のファイル ({uploadedFiles.length})
          </h3>
          <div className="space-y-2">
            {uploadedFiles.map((uploadedFile, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg"
              >
                <div className="flex items-center space-x-3">
                  {getStatusIcon(uploadedFile.status)}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {uploadedFile.file.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {formatFileSize(uploadedFile.file.size)}
                    </p>
                    {uploadedFile.error && (
                      <p className="text-xs text-error-600 mt-1">
                        {uploadedFile.error}
                      </p>
                    )}
                  </div>
                </div>
                
                {uploadedFile.status === 'pending' && (
                  <button
                    onClick={() => removeFile(index)}
                    className="p-1 text-gray-400 hover:text-gray-600 transition-colors duration-200"
                    disabled={hasUploading}
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload Button */}
      {uploadedFiles.some(f => f.status === 'pending') && (
        <div className="flex justify-end">
          <button
            onClick={uploadFiles}
            disabled={hasUploading}
            className="btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {hasUploading ? 'アップロード中...' : 'アップロード開始'}
          </button>
        </div>
      )}
    </div>
  );
};