import { useEffect, useState } from "react";
import { Bell, Check, RefreshCw } from "lucide-react";
import { listAlerts, markAlertRead } from "../../features/alerts/alert.api";
import type { Alert } from "../../types/alert.types";
import { userMessage } from "../../services/api/errors";
import "./alerts.css";

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  async function load() { setError(""); setLoading(true); try { setAlerts(await listAlerts({ unread: unreadOnly })); } catch (reason) { setError(userMessage(reason)); } finally { setLoading(false); } }
  useEffect(() => { void load(); }, [unreadOnly]);
  async function read(id: string) { try { await markAlertRead(id); setAlerts((items) => items.map((item) => item.id === id ? { ...item, is_read: true } : item)); } catch (reason) { setError(userMessage(reason)); } }
  return <main className="alerts-page"><header className="alerts-header"><div><span className="alerts-eyebrow">MONITORING CENTER</span><h1>Alerts</h1><p>Alerts currently stored for your investigations.</p></div><div className="alerts-counter"><Bell size={18} /><span>{alerts.filter((item) => !item.is_read).length} unread</span></div></header>
    <section className="alerts-container"><div className="alerts-section-heading"><div><span>RECORDED ALERTS</span><h2>Recent activity</h2></div><div><label><input type="checkbox" checked={unreadOnly} onChange={(event) => setUnreadOnly(event.target.checked)} /> Unread only</label><button type="button" onClick={() => void load()}><RefreshCw size={14} /> Refresh</button></div></div>
      {error && <p role="alert">{error} <button onClick={() => void load()}>Retry</button></p>}{loading ? <p>Loading alerts…</p> : alerts.length === 0 ? <p>No alerts are recorded.</p> : <div className="alerts-list">{alerts.map((alert) => <article className={`alert-card ${alert.severity.toLowerCase()}`} key={alert.id}><div className="alert-card-icon"><Bell size={19} /></div><div className="alert-card-content"><div className="alert-title-row"><div><span className="alert-type">{alert.alert_type} · {alert.severity}</span><h3>{alert.title}</h3></div><span>{alert.is_read ? "Read" : "Unread"}</span></div><p>{alert.message}</p><div className="alert-footer"><time>{new Date(alert.created_at).toLocaleString()}</time>{!alert.is_read && <button type="button" className="alert-action" onClick={() => void read(alert.id)}>Mark read <Check size={15} /></button>}</div></div></article>)}</div>}
      <small>The backend currently supports listing and marking alerts read. It does not yet create alerts automatically or expose resolve/acknowledge operations.</small>
    </section></main>;
}
