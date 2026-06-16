import { useEffect } from 'react';
import { useAuth } from '../AuthContext';
import { useAlerts, type Alert } from '../stores/AlertContext';
import { disconnectRealtimeSocket, getRealtimeSocket, reconnectRealtimeSocketIfNeeded } from './socket';

// Realtime (Socket.IO) só liga quando explicitamente habilitado no build
// (VITE_ENABLE_REALTIME=true) — requer a API servida via asgi:app com WebSocket
// (docker-compose/host único). Em Vercel+Render (free) fica desligado por padrão,
// evitando tentativas de WebSocket que falham e poluem o console.
const REALTIME_ENABLED = import.meta.env.VITE_ENABLE_REALTIME === 'true';

export function useRealtime(options?: { enabled?: boolean }) {
  const { token, apiBase, user } = useAuth();
  const { addAlert } = useAlerts();
  const enabled =
    REALTIME_ENABLED && (options?.enabled ?? user?.tipo === 'admin');

  useEffect(() => {
    if (!enabled || !token) return;

    const socket = getRealtimeSocket(token, apiBase);

    const onAlert = (payload: Alert) => {
      addAlert({
        id: payload.id,
        timestamp: payload.timestamp ?? new Date().toISOString(),
        severity: payload.severity,
        title: payload.title,
        message: payload.message,
        tenant_id: payload.tenant_id,
        acknowledged: payload.acknowledged ?? false,
      });
    };

    const onQueueStats = () => {
      // Ops dashboard polls summary; hook reserved for future live widgets
    };

    socket.on('alert.new', onAlert);
    socket.on('celery.queue_stats', onQueueStats);

    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        reconnectRealtimeSocketIfNeeded();
      }
    };

    document.addEventListener('visibilitychange', onVisibilityChange);

    return () => {
      socket.off('alert.new', onAlert);
      socket.off('celery.queue_stats', onQueueStats);
      document.removeEventListener('visibilitychange', onVisibilityChange);
      disconnectRealtimeSocket();
    };
  }, [addAlert, apiBase, enabled, token]);
}
