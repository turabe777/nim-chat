import React, { useState, useEffect } from 'react';
import { Settings, Zap, Cloud, Bot, Check, RefreshCw } from 'lucide-react';
import { clsx } from 'clsx';
import toast from 'react-hot-toast';
import { llmService } from '@/services/api';

interface ModeSwitchProps {
  onModeChange?: (mode: string, modelName: string) => void;
  className?: string;
}

interface ModeInfo {
  current_mode: string;
  override_mode: string | null;
  is_auto: boolean;
  recommended_model: string;
  available_modes: {
    nim_local: boolean;
    nvidia_cloud: boolean;
    mock: boolean;
  };
}

export const ModeSwitch: React.FC<ModeSwitchProps> = ({ onModeChange, className }) => {
  const [modeInfo, setModeInfo] = useState<ModeInfo | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  const fetchModeInfo = async () => {
    try {
      const info = await llmService.getCurrentMode();
      if (info.success) {
        setModeInfo(info);
      }
    } catch (error) {
      console.error('Failed to fetch mode info:', error);
    }
  };

  useEffect(() => {
    fetchModeInfo();
  }, []);

  const switchMode = async (newMode: string) => {
    setIsLoading(true);
    try {
      const result = await llmService.switchMode(newMode);
      if (result.success) {
        await fetchModeInfo();
        toast.success(`モードを${getModeDisplayName(result.actual_mode)}に切り替えました`);
        if (onModeChange) {
          onModeChange(result.actual_mode, result.recommended_model);
        }
      }
    } catch (error: any) {
      toast.error(`モード切り替えに失敗しました: ${error.response?.data?.detail || error.message}`);
    } finally {
      setIsLoading(false);
      setIsOpen(false);
    }
  };

  const getModeDisplayName = (mode: string) => {
    switch (mode) {
      case 'nim_local': return 'NIM Local';
      case 'nvidia_cloud': return 'NVIDIA Cloud';
      case 'mock': return 'Mock';
      default: return 'Unknown';
    }
  };

  const getModeIcon = (mode: string) => {
    switch (mode) {
      case 'nim_local': return <Zap className="w-4 h-4" />;
      case 'nvidia_cloud': return <Cloud className="w-4 h-4" />;
      case 'mock': return <Bot className="w-4 h-4" />;
      default: return <Settings className="w-4 h-4" />;
    }
  };

  const getModeColor = (mode: string) => {
    switch (mode) {
      case 'nim_local': return 'text-green-600 bg-green-50 border-green-200';
      case 'nvidia_cloud': return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'mock': return 'text-gray-600 bg-gray-50 border-gray-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  if (!modeInfo) {
    return (
      <div className={clsx('flex items-center space-x-2', className)}>
        <RefreshCw className="w-4 h-4 animate-spin text-gray-400" />
        <span className="text-sm text-gray-500">Loading...</span>
      </div>
    );
  }

  return (
    <div className={clsx('relative', className)}>
      {/* Current Mode Display */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading}
        className={clsx(
          'flex items-center space-x-2 px-3 py-2 rounded-lg border text-sm font-medium transition-colors',
          getModeColor(modeInfo.current_mode),
          'hover:opacity-80 disabled:opacity-50'
        )}
      >
        {getModeIcon(modeInfo.current_mode)}
        <span>{getModeDisplayName(modeInfo.current_mode)}</span>
        {modeInfo.is_auto && (
          <span className="text-xs opacity-75">(Auto)</span>
        )}
        <Settings className="w-3 h-3 opacity-60" />
        {isLoading && <RefreshCw className="w-3 h-3 animate-spin" />}
      </button>

      {/* Mode Selection Dropdown */}
      {isOpen && (
        <div className="absolute top-full mt-2 right-0 w-64 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
          <div className="p-3 border-b border-gray-100">
            <h3 className="text-sm font-semibold text-gray-900">LLM モード切り替え</h3>
            <p className="text-xs text-gray-500 mt-1">利用するLLMエンドポイントを選択</p>
          </div>
          
          <div className="p-2 space-y-1">
            {/* Auto Mode */}
            <button
              onClick={() => switchMode('auto')}
              disabled={isLoading}
              className={clsx(
                'w-full flex items-center justify-between px-3 py-2 rounded-md text-sm hover:bg-gray-50 transition-colors',
                modeInfo.is_auto && 'bg-gray-100'
              )}
            >
              <div className="flex items-center space-x-2">
                <Settings className="w-4 h-4 text-gray-600" />
                <span>Auto</span>
              </div>
              {modeInfo.is_auto && <Check className="w-4 h-4 text-green-600" />}
            </button>

            {/* NIM Local */}
            <button
              onClick={() => switchMode('nim_local')}
              disabled={isLoading || !modeInfo.available_modes.nim_local}
              className={clsx(
                'w-full flex items-center justify-between px-3 py-2 rounded-md text-sm transition-colors',
                modeInfo.available_modes.nim_local 
                  ? 'hover:bg-green-50 text-green-700' 
                  : 'opacity-50 cursor-not-allowed text-gray-400',
                modeInfo.current_mode === 'nim_local' && !modeInfo.is_auto && 'bg-green-100'
              )}
            >
              <div className="flex items-center space-x-2">
                <Zap className="w-4 h-4" />
                <span>NIM Local</span>
              </div>
              {modeInfo.current_mode === 'nim_local' && !modeInfo.is_auto && (
                <Check className="w-4 h-4 text-green-600" />
              )}
            </button>

            {/* NVIDIA Cloud */}
            <button
              onClick={() => switchMode('nvidia_cloud')}
              disabled={isLoading || !modeInfo.available_modes.nvidia_cloud}
              className={clsx(
                'w-full flex items-center justify-between px-3 py-2 rounded-md text-sm transition-colors',
                modeInfo.available_modes.nvidia_cloud 
                  ? 'hover:bg-blue-50 text-blue-700' 
                  : 'opacity-50 cursor-not-allowed text-gray-400',
                modeInfo.current_mode === 'nvidia_cloud' && !modeInfo.is_auto && 'bg-blue-100'
              )}
            >
              <div className="flex items-center space-x-2">
                <Cloud className="w-4 h-4" />
                <span>NVIDIA Cloud</span>
              </div>
              {modeInfo.current_mode === 'nvidia_cloud' && !modeInfo.is_auto && (
                <Check className="w-4 h-4 text-blue-600" />
              )}
            </button>

            {/* Mock */}
            <button
              onClick={() => switchMode('mock')}
              disabled={isLoading}
              className={clsx(
                'w-full flex items-center justify-between px-3 py-2 rounded-md text-sm hover:bg-gray-50 transition-colors',
                modeInfo.current_mode === 'mock' && !modeInfo.is_auto && 'bg-gray-100'
              )}
            >
              <div className="flex items-center space-x-2">
                <Bot className="w-4 h-4 text-gray-600" />
                <span>Mock</span>
              </div>
              {modeInfo.current_mode === 'mock' && !modeInfo.is_auto && (
                <Check className="w-4 h-4 text-gray-600" />
              )}
            </button>
          </div>

          {/* Current Model Info */}
          <div className="p-3 border-t border-gray-100 bg-gray-50">
            <p className="text-xs text-gray-600">
              現在のモデル: <span className="font-mono text-xs">{modeInfo.recommended_model}</span>
            </p>
          </div>
        </div>
      )}

      {/* Click outside to close */}
      {isOpen && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  );
};