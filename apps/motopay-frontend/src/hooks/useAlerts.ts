import { useEffect, useCallback, useState } from 'react';
import axios from 'axios';
import { useAuth } from '../AuthContext';
import { useAlerts, type Alert } from '../stores/AlertContext';

function isNetworkError(err: unknown): boolean {
  return axios.isAxiosError(err) && err.response == null;
}

interface UseAlertsHookOptions {
  pollInterval?: number;
  autoAcknowledge?: boolean;
  maxAlerts?: number;
  enabled?: boolean;
}

export const useAlertsPolling = (options: UseAlertsHookOptions = {}) => {
  const {
    pollInterval = 10000,
    autoAcknowledge = false,
    maxAlerts = 50,
    enabled = true,
  } = options;

  const { api, token } = useAuth();
  const { addAlert } = useAlerts();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAlerts = useCallback(async () => {
    if (!enabled || !token) return;
    try {
      setLoading(true);
      setError(null);
      const r = await api.get<Alert[]>('/alerts', { params: { limit: maxAlerts } });
      r.data.forEach((alert) => {
        if (!autoAcknowledge || alert.severity !== 'info') {
          addAlert(alert);
        }
      });
    } catch (err) {
      if (isNetworkError(err)) return;
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [addAlert, api, autoAcknowledge, enabled, maxAlerts, token]);

  useEffect(() => {
    if (!enabled || !token) return;
    void fetchAlerts();
    const interval = setInterval(() => void fetchAlerts(), pollInterval);
    return () => clearInterval(interval);
  }, [enabled, fetchAlerts, pollInterval, token]);

  return { loading, error, refetch: fetchAlerts };
};

export const useHealthCheck = (pollInterval: number = 30000) => {
  const { api } = useAuth();
  const [status, setStatus] = useState<'healthy' | 'degraded' | 'unhealthy' | 'unknown'>('unknown');
  const [checks, setChecks] = useState<unknown[]>([]);
  const [loading, setLoading] = useState(true);
  const { addAlert } = useAlerts();

  const checkHealth = useCallback(async () => {
    try {
      setLoading(true);
      const r = await api.get<{ status: typeof status; checks: unknown[]; overall_message?: string }>(
        '/health/status'
      );
      setStatus(r.data.status);
      setChecks(r.data.checks);
      if (r.data.status === 'unhealthy') {
        addAlert({
          id: `health-unhealthy-${Date.now()}`,
          timestamp: new Date().toISOString(),
          severity: 'critical',
          title: 'System Unhealthy',
          message: r.data.overall_message ?? 'Health check failed',
          acknowledged: false,
        });
      }
    } catch {
      setStatus('unknown');
    } finally {
      setLoading(false);
    }
  }, [addAlert, api]);

  useEffect(() => {
    void checkHealth();
    const interval = setInterval(() => void checkHealth(), pollInterval);
    return () => clearInterval(interval);
  }, [checkHealth, pollInterval]);

  return { status, checks, loading };
};

export const parsePrometheusMetrics = (text: string): Map<string, number[]> => {
  const metrics = new Map<string, number[]>();
  text.split('\n').forEach((line) => {
    if (!line || line.startsWith('#')) return;
    const match = line.match(/^([a-zA-Z_:][a-zA-Z0-9_:]*)\s+(.+)$/);
    if (!match) return;
    const [, metricName, value] = match;
    const numValue = parseFloat(value);
    if (!isNaN(numValue)) {
      const existing = metrics.get(metricName) || [];
      metrics.set(metricName, [...existing, numValue]);
    }
  });
  return metrics;
};
