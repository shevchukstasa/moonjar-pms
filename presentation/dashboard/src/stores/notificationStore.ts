import { create } from 'zustand';

export interface Notification {
  id: string;
  title: string;
  body?: string;
  type: string;
  read: boolean;
  timestamp: number;
}

interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
  addNotification: (n: Omit<Notification, 'id' | 'read' | 'timestamp'>) => void;
  markRead: (id: string) => void;
  markAllRead: () => void;
  clear: () => void;
}

let nextId = 1;

export const useNotificationStore = create<NotificationState>((set) => ({
  notifications: [],
  unreadCount: 0,
  addNotification: (n) =>
    set((s) => {
      const notification: Notification = {
        ...n,
        id: String(nextId++),
        read: false,
        timestamp: Date.now(),
      };
      const notifications = [notification, ...s.notifications].slice(0, 50);
      return { notifications, unreadCount: s.unreadCount + 1 };
    }),
  markRead: (id) =>
    set((s) => {
      let delta = 0;
      const notifications = s.notifications.map((n) => {
        if (n.id === id && !n.read) {
          delta++;
          return { ...n, read: true };
        }
        return n;
      });
      return { notifications, unreadCount: Math.max(0, s.unreadCount - delta) };
    }),
  markAllRead: () =>
    set((s) => ({
      notifications: s.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    })),
  clear: () => set({ notifications: [], unreadCount: 0 }),
}));
