import React, { useState, useEffect } from 'react';
import { Trash2, FileText, Calendar, Download, RefreshCw, AlertCircle } from 'lucide-react';

interface Document {
  document_id: string;
  filename: string;
  original_size: number;
  upload_timestamp: number;
  saved_filename: string;
  mime_type: string;
  upload_date?: string;
}

interface DocumentManagerProps {
  onDocumentDeleted?: (documentId: string) => void;
}

const DocumentManager: React.FC<DocumentManagerProps> = ({ onDocumentDeleted }) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('http://localhost:8001/api/v1/documents');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      if (data.success) {
        setDocuments(data.documents || []);
      } else {
        setError('Failed to fetch documents');
      }
    } catch (err) {
      console.error('Error fetching documents:', err);
      setError('Failed to load documents. Please check if the document service is running.');
    } finally {
      setLoading(false);
    }
  };

  const deleteDocument = async (documentId: string, filename: string) => {
    if (!confirm(`Are you sure you want to delete "${filename}"? This action cannot be undone.`)) {
      return;
    }

    try {
      setDeleting(documentId);
      setError(null);

      // Delete document from document service
      const response = await fetch(`http://localhost:8001/api/v1/documents/${documentId}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      if (data.success) {
        // Delete vectors from vector store
        try {
          const vectorResponse = await fetch(`http://localhost:8004/api/v1/vector/document/${documentId}`, {
            method: 'DELETE'
          });
          
          if (!vectorResponse.ok) {
            console.warn('Failed to delete vectors, but document was deleted');
          }
        } catch (vectorError) {
          console.warn('Vector deletion failed:', vectorError);
        }

        // Update local state
        setDocuments(prev => prev.filter(doc => doc.document_id !== documentId));
        
        // Notify parent component
        if (onDocumentDeleted) {
          onDocumentDeleted(documentId);
        }

        alert(`Document "${filename}" deleted successfully`);
      } else {
        throw new Error(data.message || 'Delete failed');
      }
    } catch (err) {
      console.error('Error deleting document:', err);
      setError(`Failed to delete document: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setDeleting(null);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (timestamp: number): string => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  const downloadDocument = (documentId: string, filename: string) => {
    const downloadUrl = `http://localhost:8001/api/v1/documents/${documentId}/download`;
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <RefreshCw className="animate-spin h-6 w-6 mr-2" />
        <span>Loading documents...</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center">
          <FileText className="h-5 w-5 mr-2" />
          Document Manager
        </h2>
        <button
          onClick={fetchDocuments}
          className="flex items-center px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <RefreshCw className="h-4 w-4 mr-1" />
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center">
          <AlertCircle className="h-5 w-5 text-red-500 mr-2" />
          <span className="text-red-700">{error}</span>
        </div>
      )}

      {documents.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <FileText className="h-12 w-12 mx-auto mb-4 text-gray-300" />
          <p>No documents uploaded yet</p>
          <p className="text-sm">Upload some PDF files to get started</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Document
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Size
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Upload Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {documents.map((doc) => (
                  <tr key={doc.document_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <FileText className="h-5 w-5 text-red-500 mr-3" />
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {doc.filename}
                          </div>
                          <div className="text-sm text-gray-500">
                            ID: {doc.document_id.substring(0, 8)}...
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatFileSize(doc.original_size)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <div className="flex items-center">
                        <Calendar className="h-4 w-4 mr-1" />
                        {formatDate(doc.upload_timestamp)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <div className="flex space-x-2">
                        <button
                          onClick={() => downloadDocument(doc.document_id, doc.filename)}
                          className="inline-flex items-center px-3 py-1 text-blue-600 hover:text-blue-800"
                          title="Download document"
                        >
                          <Download className="h-4 w-4 mr-1" />
                          Download
                        </button>
                        <button
                          onClick={() => deleteDocument(doc.document_id, doc.filename)}
                          disabled={deleting === doc.document_id}
                          className="inline-flex items-center px-3 py-1 text-red-600 hover:text-red-800 disabled:opacity-50"
                        >
                          {deleting === doc.document_id ? (
                            <RefreshCw className="animate-spin h-4 w-4 mr-1" />
                          ) : (
                            <Trash2 className="h-4 w-4 mr-1" />
                          )}
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          <div className="bg-gray-50 px-6 py-3 text-sm text-gray-500">
            Total: {documents.length} document{documents.length !== 1 ? 's' : ''}
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentManager;