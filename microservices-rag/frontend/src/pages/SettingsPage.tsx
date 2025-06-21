import React, { useState } from 'react';
import { Settings, Save, TestTube, CheckCircle, XCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import { llmService } from '@/services/api';

interface SettingsState {
  model: string;
  maxTokens: number;
  temperature: number;
  contextLength: number;
  similarityThreshold: number;
}

export const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<SettingsState>({
    model: 'nvidia/llama-3.1-nemotron-70b-instruct',
    maxTokens: 1000,
    temperature: 0.7,
    contextLength: 3,
    similarityThreshold: 0.3,
  });

  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  const handleSettingChange = (key: keyof SettingsState, value: string | number) => {
    setSettings(prev => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleSave = () => {
    // In a real app, you'd save to backend/localStorage
    localStorage.setItem('rag_settings', JSON.stringify(settings));
    toast.success('設定を保存しました');
  };

  const handleTest = async () => {
    setIsTesting(true);
    setTestResult(null);

    try {
      await llmService.testConnection();
      setTestResult({
        success: true,
        message: 'NVIDIA Cloud APIの接続テストに成功しました',
      });
      toast.success('接続テスト成功');
    } catch (error: any) {
      setTestResult({
        success: false,
        message: `接続テストに失敗しました: ${error.message}`,
      });
      toast.error('接続テスト失敗');
    } finally {
      setIsTesting(false);
    }
  };

  // Load settings on component mount
  React.useEffect(() => {
    const saved = localStorage.getItem('rag_settings');
    if (saved) {
      try {
        const parsedSettings = JSON.parse(saved);
        setSettings(parsedSettings);
      } catch (error) {
        console.error('Failed to load settings:', error);
      }
    }
  }, []);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center space-x-3">
        <Settings className="w-8 h-8 text-primary-600" />
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            システム設定
          </h1>
          <p className="text-gray-600 mt-1">
            RAGシステムの動作パラメータを調整します
          </p>
        </div>
      </div>

      {/* LLM Settings */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">
          LLM設定
        </h2>
        
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              使用モデル
            </label>
            <select
              value={settings.model}
              onChange={(e) => handleSettingChange('model', e.target.value)}
              className="input"
            >
              <option value="nvidia/llama-3.1-nemotron-70b-instruct">
                Llama 3.1 Nemotron 70B Instruct
              </option>
              <option value="nvidia/llama-3.1-8b-instruct">
                Llama 3.1 8B Instruct
              </option>
              <option value="nvidia/llama-3.1-70b-instruct">
                Llama 3.1 70B Instruct
              </option>
            </select>
            <p className="text-sm text-gray-500 mt-1">
              NVIDIA Cloud APIで利用可能なモデルを選択
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              最大トークン数: {settings.maxTokens}
            </label>
            <input
              type="range"
              min="100"
              max="4000"
              step="100"
              value={settings.maxTokens}
              onChange={(e) => handleSettingChange('maxTokens', parseInt(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>100</span>
              <span>4000</span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Temperature: {settings.temperature}
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={settings.temperature}
              onChange={(e) => handleSettingChange('temperature', parseFloat(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>0 (決定論的)</span>
              <span>1 (ランダム)</span>
            </div>
          </div>
        </div>
      </div>

      {/* RAG Settings */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">
          RAG設定
        </h2>
        
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              コンテキスト数: {settings.contextLength}
            </label>
            <input
              type="range"
              min="1"
              max="10"
              step="1"
              value={settings.contextLength}
              onChange={(e) => handleSettingChange('contextLength', parseInt(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>1</span>
              <span>10</span>
            </div>
            <p className="text-sm text-gray-500 mt-1">
              回答生成に使用する関連文書の数
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              類似度閾値: {settings.similarityThreshold}
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={settings.similarityThreshold}
              onChange={(e) => handleSettingChange('similarityThreshold', parseFloat(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>0 (緩い)</span>
              <span>1 (厳密)</span>
            </div>
            <p className="text-sm text-gray-500 mt-1">
              文書を関連性があると判断する最小類似度
            </p>
          </div>
        </div>
      </div>

      {/* API Connection Test */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">
          API接続テスト
        </h2>
        
        <div className="space-y-4">
          <button
            onClick={handleTest}
            disabled={isTesting}
            className="btn btn-secondary flex items-center space-x-2"
          >
            <TestTube className="w-4 h-4" />
            <span>{isTesting ? 'テスト中...' : 'NVIDIA Cloud API テスト'}</span>
          </button>

          {testResult && (
            <div className={`p-4 rounded-lg border flex items-start space-x-3 ${
              testResult.success
                ? 'bg-success-50 border-success-200'
                : 'bg-error-50 border-error-200'
            }`}>
              {testResult.success ? (
                <CheckCircle className="w-5 h-5 text-success-500 mt-0.5" />
              ) : (
                <XCircle className="w-5 h-5 text-error-500 mt-0.5" />
              )}
              <div>
                <p className={`font-medium ${
                  testResult.success ? 'text-success-900' : 'text-error-900'
                }`}>
                  {testResult.success ? '成功' : '失敗'}
                </p>
                <p className={`text-sm ${
                  testResult.success ? 'text-success-700' : 'text-error-700'
                }`}>
                  {testResult.message}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-end space-x-4">
        <button
          onClick={handleSave}
          className="btn btn-primary flex items-center space-x-2"
        >
          <Save className="w-4 h-4" />
          <span>設定を保存</span>
        </button>
      </div>

      {/* Help */}
      <div className="card bg-blue-50 border-blue-200">
        <h3 className="text-lg font-semibold text-blue-900 mb-3">
          設定ガイド
        </h3>
        <div className="space-y-2 text-blue-800">
          <p className="flex items-start space-x-2">
            <span className="font-bold">•</span>
            <span><strong>Temperature</strong>: 低い値では一貫した回答、高い値では創造的な回答が生成されます</span>
          </p>
          <p className="flex items-start space-x-2">
            <span className="font-bold">•</span>
            <span><strong>コンテキスト数</strong>: 多いほど詳細な回答が可能ですが、処理時間が増加します</span>
          </p>
          <p className="flex items-start space-x-2">
            <span className="font-bold">•</span>
            <span><strong>類似度閾値</strong>: 低いほど多様な文書を参照しますが、関連性が下がる可能性があります</span>
          </p>
        </div>
      </div>
    </div>
  );
};