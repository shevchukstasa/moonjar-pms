import { useEffect, useRef, useCallback } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { useNotificationStore } from '@/stores/notificationStore';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

export type WsStatus = 'disconnected' | 'connecting' | 'connected';

/** Derive WebSocket URL from current window location (same host, ws/wss). */
function buildWsUrl(): string {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL + '/notifications';
  }

  const loc = window.location;
  const protocol = loc.protocol === 'https:' ? 'wss:' : 'ws:';

  // On Railway, frontend and backend are on different subdomains.
  // Reuse the same hostname-resolution logic as api/client.ts.
  let host = loc.host;
  if (loc.hostname.includes('.up.railway.app')) {
    host = loc.hostname.replace(/-\d+\.up\.railway\.app$/, '.up.railway.app');
  }

  return `${protocol}//${host}/api/ws/notifications`;
}

const MAX_BACKOFF = 30_000;
const HEARTBEAT_INTERVAL = 30_000;

export function useWebSocket() {
  const user = useAuthStore((s) => s.user);
  const qc = useQueryClient();
  const addNotification = useNotificationStore((s) => s.addNotification);

  const wsRef = useRef<WebSocket | null>(null);
  const statusRef = useRef<WsStatus>('disconnected');
  const retriesRef = useRef(0);
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmountedRef = useRef(false);

  const cleanup = useCallback(() => {
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current);
      heartbeatRef.current = null;
    }
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.onopen = null;
      wsRef.current.onmessage = null;
      wsRef.current.onerror = null;
      wsRef.current.onclose = null;
      wsRef.current.close();
      wsRef.current = null;
    }
    statusRef.current = 'disconnected';
  }, []);

  const scheduleReconnect = useCallback(() => {
    if (unmountedRef.current) return;
    const delay = Math.min(1000 * Math.pow(2, retriesRef.current), MAX_BACKOFF);
    retriesRef.current++;
    reconnectTimerRef.current = setTimeout(() => {
      if (!unmountedRef.current) connect();
    }, delay);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const connect = useCallback(() => {
    if (unmountedRef.current) return;
    cleanup();

    statusRef.current = 'connecting';
    const url = buildWsUrl();

    // The backend reads the access_token from the cookie automatically
    // during the WebSocket handshake (withCredentials is handled by the browser).
    // We pass token=cookie to signal cookie-based auth.
    const socket = new WebSocket(url + '?token=cookie');
    wsRef.current = socket;

    socket.onopen = () => {
      statusRef.current = 'connected';
      retriesRef.current = 0;

      // Start heartbeat
      heartbeatRef.current = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send('ping');
        }
      }, HEARTBEAT_INTERVAL);
    };

    socket.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);

        if (msg.type === 'notification') {
          addNotification({
            title: msg.data?.title || 'New notification',
            body: msg.data?.body,
            type: 'notification',
          });
          qc.invalidateQueries({ queryKey: ['notifications'] });
          if (msg.data?.title) toast(msg.data.title);
        }

        if (msg.type === 'status_change') {
          qc.invalidateQueries({ queryKey: ['orders'] });
          qc.invalidateQueries({ queryKey: ['positions'] });
          addNotification({
            title: msg.data?.title || 'Status updated',
            body: msg.data?.body,
            type: 'status_change',
          });
        }

        if (msg.type === 'material_update') {
          qc.invalidateQueries({ queryKey: ['materials'] });
        }

        if (msg.type === 'schedule_update') {
          qc.invalidateQueries({ queryKey: ['schedule'] });
          qc.invalidateQueries({ queryKey: ['kilns'] });
        }
      } catch {
        // ignore non-JSON messages (e.g. "pong")
      }
    };

    socket.onerror = () => {
      // onerror is always followed by onclose
    };

    socket.onclose = () => {
      statusRef.current = 'disconnected';
      if (heartbeatRef.current) {
        clearInterval(heartbeatRef.current);
        heartbeatRef.current = null;
      }
      if (!unmountedRef.current) {
        scheduleReconnect();
      }
    };
  }, [cleanup, scheduleReconnect, addNotification, qc]);

  useEffect(() => {
    unmountedRef.current = false;

    if (!user) {
      cleanup();
      return;
    }

    connect();

    return () => {
      unmountedRef.current = true;
      cleanup();
    };
  }, [user, connect, cleanup]);
}
