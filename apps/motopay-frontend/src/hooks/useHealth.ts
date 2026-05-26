import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '../AuthContext';

export interface HealthCheckResult {
  name: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  duration_ms: number;
  error?: string;
  details?: Record<string, unknown>;
}

export interface HealthStatus {
  timestamp: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  uptime_seconds: number;
  checks: HealthCheckResult[];
  overall_message: string;
}

export const useHealth = (pollInterval: number = 30000) => {
  const { api } = useAuth();
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const r = await api.get<HealthStatus>('/health/status');
      setHealth(r.data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    void fetchHealth();
    const interval = setInterval(() => void fetchHealth(), pollInterval);
    return () => clearInterval(interval);
  }, [fetchHealth, pollInterval]);

  return { health, loading, error };
};

export const getHealthColor = (status: string): string => {
  switch (status) {
    case 'healthy':
      return '#10b981';
    case 'degraded':
      return '#f59e0b';
    case 'unhealthy':
      return '#ef4444';
    default:
      return '#6b7280';
  }
};

export const getHealthIcon = (status: string): string => {
  switch (status) {
    case 'healthy':
      return '✓';
    case 'degraded':
      return '⚠';
    case 'unhealthy':
      return '✗';
    default:
      return '?';
  }
};
