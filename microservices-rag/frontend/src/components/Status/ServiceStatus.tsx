import React, { useState, useEffect } from 'react';
import { Activity, CheckCircle, XCircle, Loader, RefreshCw } from 'lucide-react';
import { clsx } from 'clsx';
import { healthService } from '@/services/api';
import { ServiceStatus as ServiceStatusType } from '@/types';

export const ServiceStatus: React.FC = () => {
  const [services, setServices] = useState<ServiceStatusType[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const checkServices = async () => {
    setIsLoading(true);
    try {
      const statuses = await healthService.checkAllServices();
      setServices(statuses);
      setLastUpdated(new Date());
    } catch (error) {
      console.error('Failed to check services:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    checkServices();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(checkServices, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status: ServiceStatusType['status']) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="w-5 h-5 text-success-500" />;
      case 'unhealthy':
        return <XCircle className="w-5 h-5 text-error-500" />;
      case 'loading':
        return <Loader className="w-5 h-5 text-gray-400 animate-spin" />;
    }
  };

  const getStatusColor = (status: ServiceStatusType['status']) => {
    switch (status) {
      case 'healthy':
        return 'text-success-700 bg-success-50 border-success-200';
      case 'unhealthy':
        return 'text-error-700 bg-error-50 border-error-200';
      case 'loading':
        return 'text-gray-700 bg-gray-50 border-gray-200';
    }
  };

  const getStatusText = (status: ServiceStatusType['status']) => {
    switch (status) {
      case 'healthy':
        return '正常';
      case 'unhealthy':
        return 'エラー';
      case 'loading':
        return '確認中';
    }
  };

  const healthyCount = services.filter(s => s.status === 'healthy').length;
  const totalCount = services.length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Activity className="w-6 h-6 text-primary-600" />
          <h2 className="text-2xl font-bold text-gray-900">
            サービスステータス
          </h2>
        </div>
        <button
          onClick={checkServices}
          disabled={isLoading}
          className="btn btn-secondary flex items-center space-x-2"
        >
          <RefreshCw className={clsx('w-4 h-4', isLoading && 'animate-spin')} />
          <span>更新</span>
        </button>
      </div>

      {/* Overall Status */}
      <div className="card">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              システム全体
            </h3>
            <p className="text-sm text-gray-500">
              {totalCount}個のサービス中{healthyCount}個が正常稼働中
            </p>
          </div>
          <div className={clsx(
            'px-4 py-2 rounded-full border',
            healthyCount === totalCount
              ? 'text-success-700 bg-success-50 border-success-200'
              : 'text-warning-700 bg-warning-50 border-warning-200'
          )}>
            {healthyCount === totalCount ? '全サービス正常' : '一部サービスエラー'}
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-4">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-success-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${(healthyCount / totalCount) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Service List */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {services.map((service) => (
          <div key={service.name} className="card">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                {getStatusIcon(service.status)}
                <h3 className="font-semibold text-gray-900">
                  {service.name}
                </h3>
              </div>
              <div className={clsx(
                'px-2 py-1 rounded-full text-xs font-medium border',
                getStatusColor(service.status)
              )}>
                {getStatusText(service.status)}
              </div>
            </div>
            
            <div className="space-y-2 text-sm text-gray-600">
              <div className="flex justify-between">
                <span>ポート:</span>
                <span className="font-mono">{service.port}</span>
              </div>
              <div className="flex justify-between">
                <span>URL:</span>
                <span className="font-mono text-xs break-all">
                  {service.url}
                </span>
              </div>
            </div>

            {service.status === 'unhealthy' && (
              <div className="mt-3 p-2 bg-error-50 border border-error-200 rounded-lg">
                <p className="text-xs text-error-700">
                  サービスに接続できません。サービスが起動しているか確認してください。
                </p>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Last Updated */}
      {lastUpdated && (
        <div className="text-center text-sm text-gray-500">
          最終更新: {lastUpdated.toLocaleString('ja-JP')}
        </div>
      )}
    </div>
  );
};