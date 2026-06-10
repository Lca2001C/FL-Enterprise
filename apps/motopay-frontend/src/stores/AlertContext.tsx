import React, { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import { resolveApiBase, sanitizeApiBase } from '../utils/apiBase';

export type AlertSeverity = 'critical' | 'warning' | 'info';

export interface Alert {
  id: string;
  timestamp: string;
  severity: AlertSeverity;
  title: string;
  message: string;
  tenant_id?: number;
  acknowledged: boolean;
}

interface AlertContextType {
  alerts: Alert[];
  unacknowledgedCount: number;
  addAlert: (alert: Alert) => void;
  removeAlert: (id: string) => void;
  acknowledgeAlert: (id: string) => Promise<void>;
  clearAlerts: () => void;
  hasNewAlerts: boolean;
}

const AlertContext = createContext<AlertContextType | undefined>(undefined);

export const AlertProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [hasNewAlerts, setHasNewAlerts] = useState(false);

  const addAlert = useCallback((alert: Alert) => {
    setAlerts(prev => {
      // Evitar duplicatas
      if (prev.some(a => a.id === alert.id)) return prev;
      return [alert, ...prev].slice(0, 100); // Manter apenas 100 alertas
    });
    
    // Marcar como novo se for crítico ou warning
    if (alert.severity === 'critical' || alert.severity === 'warning') {
      setHasNewAlerts(true);
    }
  }, []);

  const removeAlert = useCallback((id: string) => {
    setAlerts(prev => prev.filter(a => a.id !== id));
  }, []);

  const acknowledgeAlert = useCallback(async (id: string) => {
    try {
      const token = localStorage.getItem('token');
      const base = sanitizeApiBase(
        resolveApiBase(
          import.meta.env.VITE_API_BASE_URL as string | undefined,
          localStorage.getItem('apiBase')
        )
      );
      await fetch(`${base}/alerts/${id}/acknowledge`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      setAlerts(prev => 
        prev.map(a => a.id === id ? { ...a, acknowledged: true } : a)
      );
    } catch (error) {
      console.error('Error acknowledging alert:', error);
    }
  }, []);

  const clearAlerts = useCallback(() => {
    setAlerts([]);
    setHasNewAlerts(false);
  }, []);

  const unacknowledgedCount = alerts.filter(a => !a.acknowledged).length;

  return (
    <AlertContext.Provider value={{
      alerts,
      unacknowledgedCount,
      addAlert,
      removeAlert,
      acknowledgeAlert,
      clearAlerts,
      hasNewAlerts,
    }}>
      {children}
    </AlertContext.Provider>
  );
};

export const useAlerts = (): AlertContextType => {
  const context = useContext(AlertContext);
  if (!context) {
    throw new Error('useAlerts must be used within AlertProvider');
  }
  return context;
};
