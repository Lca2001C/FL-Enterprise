import { io, type Socket } from 'socket.io-client';
import { normalizeBase } from '../apiClient';

let socket: Socket | null = null;

export function getRealtimeSocket(token: string, apiBase: string): Socket {
  if (socket?.connected) {
    return socket;
  }
  const base = normalizeBase(apiBase);
  socket = io(base, {
    path: '/socket.io',
    auth: { token },
    transports: ['websocket', 'polling'],
    reconnection: true,
  });
  return socket;
}

export function disconnectRealtimeSocket(): void {
  socket?.disconnect();
  socket = null;
}

export function reconnectRealtimeSocketIfNeeded(): void {
  if (socket && !socket.connected) {
    socket.connect();
  }
}
