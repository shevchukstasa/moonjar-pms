import { useEffect, useRef } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

export function useWebSocket() {
  const user = useAuthStore((s) => s.user);
  const qc = useQueryClient();
  const ws = useRef<WebSocket | null>(null);
  useEffect(() => {
    if (!user) return;
    const socket = new WebSocket(`${import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/ws'}/notifications?token=cookie`);
    socket.onmessage = (e) => { try { const msg = JSON.parse(e.data); if (msg.type === 'notification') { qc.invalidateQueries({ queryKey: ['notifications'] }); toast(msg.data?.title); } if (msg.type === 'status_change') { qc.invalidateQueries({ queryKey: ['orders'] }); qc.invalidateQueries({ queryKey: ['positions'] }); } } catch {} };
    ws.current = socket;
    return () => socket.close();
  }, [user, qc]);
}
