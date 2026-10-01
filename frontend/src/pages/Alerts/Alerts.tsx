import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, ArrowRight, Bell, CheckCircle2, Clock3, ShieldAlert, ShieldCheck } from "lucide-react";
import { dismissAlert, listAlerts, markAlertRead, markAllAlertsRead } from "../../features/alerts/alert.api";
import { ErrorState, LoadingState } from "../../components/states/AsyncStates";
import type { Alert } from "../../types/api.types";
import "./alerts.css";

type AlertVisualType = "critical" | "high" | "verification" | "resolved";
type AlertItem = Alert & { type: AlertVisualType; entity: string };
const iconMap = { critical: ShieldAlert, high: AlertTriangle, verification: ShieldCheck, resolved: CheckCircle2 };

function Alerts() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [markingAll, setMarkingAll] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    listAlerts(false, controller.signal)
      .then(({ items }) => setAlerts(items.map((alert) => ({ ...alert, type: visualType(alert), entity: alert.entity_name || "Workspace alert" }))))
      .catch((cause) => { if (!controller.signal.aborted) { console.error(cause); setError(true); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);

  const activeAlerts = alerts.filter((alert) => !alert.read_at).length;
  const criticalCount = alerts.filter((alert) => alert.type === "critical").length;
  const highCount = alerts.filter((alert) => alert.type === "high").length;
  const verificationCount = alerts.filter((alert) => alert.type === "verification").length;

  const handleRead = async (alert: AlertItem) => {
    if (alert.read_at || busyId) return;
    setBusyId(alert.id);
    try {
      const updated = await markAlertRead(alert.id);
      setAlerts((current) => current.map((item) => item.id === alert.id ? { ...item, ...updated } : item));
    } catch (cause) { console.error("Unable to mark alert as read", cause); }
    finally { setBusyId(null); }
  };

  const handleReadAll = async () => {
    if (markingAll || !activeAlerts) return;
    setMarkingAll(true);
    try {
      await markAllAlertsRead();
      const readAt = new Date().toISOString();
      setAlerts((current) => current.map((alert) => alert.read_at ? alert : { ...alert, read_at: readAt }));
    } catch (cause) { console.error("Unable to mark all alerts as read", cause); }
    finally { setMarkingAll(false); }
  };

  const handleDismiss = async (alert: AlertItem) => {
    setBusyId(alert.id);
    try {
      await dismissAlert(alert.id);
      setAlerts((current) => current.filter((item) => item.id !== alert.id));
    } catch (cause) { console.error("Unable to dismiss alert", cause); }
    finally { setBusyId(null); }
  };

  return <div className="alerts-page">
    <section className="alerts-header"><div><span className="alerts-eyebrow">MONITORING CENTER</span><h1>Alerts</h1><p>Review alert records created by backend processes.</p></div><div className="alerts-header-actions"><button type="button" className="alert-action" onClick={() => void handleReadAll()} disabled={!activeAlerts || markingAll}>{markingAll ? "Saving..." : "Mark all read"}</button><div className="alerts-counter"><Bell size={18} /><span>{activeAlerts} Unread</span></div></div></section>
    <section className="alerts-summary"><AlertSummary icon={<ShieldAlert size={20} />} value={criticalCount} label="Critical" kind="critical" /><AlertSummary icon={<AlertTriangle size={20} />} value={highCount} label="High Risk" kind="high" /><AlertSummary icon={<ShieldCheck size={20} />} value={verificationCount} label="Needs Verification" kind="verification" /><AlertSummary icon={<CheckCircle2 size={20} />} value={alerts.filter((alert) => !!alert.read_at).length} label="Read" kind="resolved" /></section>
    <section className="alerts-container"><div className="alerts-section-heading"><div><span>DEPENDENCY ALERTS</span><h2>Recent Activity</h2></div><span className="alerts-filter">All Alerts</span></div>
      {loading ? <LoadingState label="Loading alerts..." /> : error ? <ErrorState title="Alerts are unavailable" description="Check the backend and PostgreSQL connection." action={() => window.location.reload()} /> : <div className="alerts-list">
        {alerts.map((alert) => { const Icon = iconMap[alert.type]; return <article className={`alert-card ${alert.type}`} data-alert-id={alert.id} key={alert.id}><div className="alert-card-icon"><Icon size={21} /></div><div className="alert-card-content"><div className="alert-title-row"><div><span className="alert-type">{alert.severity} · {alert.title}</span><h3>{alert.entity}</h3></div></div><p>{alert.message}</p><div className="alert-footer"><span className="alert-time"><Clock3 size={14} />{new Date(alert.created_at).toLocaleString()}</span><div><button className="alert-action" onClick={() => void handleRead(alert)} disabled={!!alert.read_at || busyId === alert.id}>{alert.read_at ? "Read" : busyId === alert.id ? "Saving..." : "Mark read"}<ArrowRight size={15} /></button><button className="alert-action" onClick={() => void handleDismiss(alert)} disabled={busyId === alert.id}>Dismiss</button></div></div></div></article>; })}
        {!alerts.length && <p className="empty-event">No alerts have been recorded yet.</p>}
      </div>}
    </section>
  </div>;
}

function visualType(alert: Alert): AlertVisualType {
  const severity = alert.severity.toLowerCase();
  if (severity === "critical") return "critical";
  if (severity === "high") return "high";
  if (/verif/i.test(`${alert.title} ${alert.message}`)) return "verification";
  return alert.read_at ? "resolved" : "high";
}

function AlertSummary({ icon, value, label, kind }: { icon: React.ReactNode; value: number; label: string; kind: AlertVisualType }) {
  return <div className="alert-summary-card"><div className={`alert-summary-icon ${kind}`}>{icon}</div><div><strong>{value}</strong><span>{label}</span></div></div>;
}

export default Alerts;
