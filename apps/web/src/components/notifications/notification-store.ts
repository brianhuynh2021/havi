"use client";

import { useEffect, useState } from "react";

export type AppNotification = {
  id: string;
  type: "draft_ready" | "publish_success" | "info";
  title: string;
  description: string;
  timestamp: string;
  read: boolean;
};

const INITIAL_NOTIFICATIONS: AppNotification[] = [
  {
    id: "notif-welcome",
    type: "info",
    title: "Chào mừng bạn đến với Havi AI",
    description: "Havi đã sẵn sàng hỗ trợ bạn sáng tạo nội dung đa kênh và tương tác khách hàng tự động.",
    timestamp: "Hôm nay",
    read: true,
  },
];

let listeners: Array<(items: AppNotification[]) => void> = [];
let globalNotifications: AppNotification[] = INITIAL_NOTIFICATIONS;

export function getNotifications(): AppNotification[] {
  return globalNotifications;
}

export function pushNotification(item: Omit<AppNotification, "id" | "timestamp" | "read">) {
  const newNotif: AppNotification = {
    ...item,
    id: `notif-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    timestamp: "Vừa xong",
    read: false,
  };
  globalNotifications = [newNotif, ...globalNotifications];
  listeners.forEach((listener) => listener(globalNotifications));
}

export function markAllAsRead() {
  globalNotifications = globalNotifications.map((n) => ({ ...n, read: true }));
  listeners.forEach((listener) => listener(globalNotifications));
}

export function markAsRead(id: string) {
  globalNotifications = globalNotifications.map((n) =>
    n.id === id ? { ...n, read: true } : n
  );
  listeners.forEach((listener) => listener(globalNotifications));
}

export function useNotifications() {
  const [notifications, setNotifications] = useState<AppNotification[]>(globalNotifications);

  useEffect(() => {
    const handleUpdate = (items: AppNotification[]) => {
      setNotifications([...items]);
    };
    listeners.push(handleUpdate);
    return () => {
      listeners = listeners.filter((l) => l !== handleUpdate);
    };
  }, []);

  const unreadCount = notifications.filter((n) => !n.read).length;

  return {
    notifications,
    unreadCount,
    pushNotification,
    markAllAsRead,
    markAsRead,
  };
}
