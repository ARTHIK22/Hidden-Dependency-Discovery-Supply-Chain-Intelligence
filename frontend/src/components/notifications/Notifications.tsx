import { useEffect, useRef, useState } from "react";
import { Bell, Check, CheckCheck, ShieldAlert, FileCheck2, CircleCheck, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { dismissAlert, listAlerts, markAlertRead } from "../../features/alerts/alert.api";
import type { Alert } from "../../types/api.types";
import "./notifications.css";

export default function Notifications() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<Alert[]>([]);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const unreadCount = notifications.filter((item) => !item.read_at).length;

  useEffect(() => {
    const controller = new AbortController();
    listAlerts(false, controller.signal)
      .then(({ items }) => { setNotifications(items); setError(false); })
      .catch((cause) => { if (!controller.signal.aborted) { console.error(cause); setError(true); } });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const handleOutside = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, []);

  const markAllRead = async () => {
    setBusy(true);
    try {
      await Promise.all(notifications.filter((item) => !item.read_at).map((item) => markAlertRead(item.id)));
      const now = new Date().toISOString();
      setNotifications((items) => items.map((item) => item.read_at ? item : { ...item, read_at: now }));
    } catch (cause) { console.error("Unable to update notifications", cause); }
    finally { setBusy(false); }
  };

  const markRead = async (id: string) => {
    try {
      const updated = await markAlertRead(id);
      setNotifications((items) => items.map((item) => item.id === id ? { ...item, ...updated } : item));
    } catch (cause) { console.error("Unable to mark notification read", cause); }
  };

  const removeNotification = async (id: string) => {
    try {
      await dismissAlert(id);
      setNotifications((items) => items.filter((item) => item.id !== id));
    } catch (cause) { console.error("Unable to dismiss notification", cause); }
  };

  const getIcon = (notification: Alert) => {
    if (notification.severity.toLowerCase() === "critical") return ShieldAlert;
    if (/verif/i.test(`${notification.title} ${notification.message}`)) return FileCheck2;
    return CircleCheck;
  };

  return <div className="notification-wrapper" ref={ref}>
    <button className="notification-trigger" onClick={() => setOpen((value) => !value)} aria-label="Notifications" aria-expanded={open} aria-controls="notification-popover" type="button"><Bell size={19} />{unreadCount > 0 && <span className="notification-badge">{unreadCount > 9 ? "9+" : unreadCount}</span>}</button>
    {open && <div className="notification-popover" id="notification-popover"><div className="notification-header"><div><h3>Notifications</h3><span>{error ? "Backend unavailable" : unreadCount > 0 ? `${unreadCount} unread` : "You're all caught up"}</span></div>{unreadCount > 0 && <button className="mark-all-button" onClick={() => void markAllRead()} disabled={busy} type="button"><CheckCheck size={15} />Mark all read</button>}</div>
      <div className="notification-list">{notifications.length === 0 ? <div className="notifications-empty"><div className="empty-bell"><Bell size={23} /></div><strong>{error ? "Notifications unavailable" : "No notifications"}</strong><span>{error ? "Check your backend connection." : "No alerts have been recorded."}</span></div> : notifications.map((notification) => { const Icon = getIcon(notification); const read = !!notification.read_at; const type = notification.severity.toLowerCase() === "critical" || notification.severity.toLowerCase() === "high" ? "critical" : "verification"; return <div key={notification.id} className={`notification-item ${read ? "" : "unread"}`} onClick={() => !read && void markRead(notification.id)}><div className={`notification-icon ${type}`}><Icon size={17} /></div><div className="notification-content"><div className="notification-title-row"><strong>{notification.title}</strong>{!read && <span className="unread-dot" />}</div><p>{notification.message}</p><span className="notification-time">{new Date(notification.created_at).toLocaleString()}</span></div><div className="notification-actions">{!read && <button title="Mark as read" aria-label={`Mark ${notification.title} as read`} onClick={(event) => { event.stopPropagation(); void markRead(notification.id); }} type="button"><Check size={14} /></button>}<button title="Dismiss" aria-label={`Dismiss ${notification.title}`} onClick={(event) => { event.stopPropagation(); void removeNotification(notification.id); }} type="button"><X size={14} /></button></div></div>; })}</div>
      <button className="view-alerts-button" onClick={() => { setOpen(false); navigate("/alerts"); }} type="button">View all alerts</button>
    </div>}
  </div>;
}
