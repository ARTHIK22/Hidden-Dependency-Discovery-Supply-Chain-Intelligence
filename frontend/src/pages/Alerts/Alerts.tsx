import {
  AlertTriangle,
  ArrowRight,
  Bell,
  CheckCircle2,
  Clock3,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import "./alerts.css";

type AlertItem = {
  id: number;
  type: "critical" | "high" | "verification" | "resolved";
  title: string;
  entity: string;
  description: string;
  time: string;
  score?: number;
};

const alerts: AlertItem[] = [
  {
    id: 1,
    type: "critical",
    title: "Critical Dependency",
    entity: "Processing Facility D",
    description:
      "Single-region concentration detected in an upstream processing dependency.",
    time: "2 hours ago",
    score: 91,
  },
  {
    id: 2,
    type: "high",
    title: "High Risk Supplier",
    entity: "Supplier B",
    description:
      "Material dependency identified with limited alternative suppliers.",
    time: "5 hours ago",
    score: 78,
  },
  {
    id: 3,
    type: "verification",
    title: "Verification Required",
    entity: "Lithium → Processing Facility D",
    description:
      "Relationship evidence should be re-verified before the next investigation cycle.",
    time: "Yesterday",
  },
  {
    id: 4,
    type: "resolved",
    title: "Risk Signal Resolved",
    entity: "Factory X",
    description:
      "Previously detected geographic concentration has been resolved.",
    time: "Yesterday",
  },
];

const iconMap = {
  critical: ShieldAlert,
  high: AlertTriangle,
  verification: ShieldCheck,
  resolved: CheckCircle2,
};

function Alerts() {
  const activeAlerts = alerts.filter(
    (alert) => alert.type !== "resolved"
  ).length;

  return (
    <div className="alerts-page">
      <section className="alerts-header">
        <div>
          <span className="alerts-eyebrow">MONITORING CENTER</span>

          <h1>Alerts</h1>

          <p>
            Monitor dependency changes, verification issues,
            and emerging supply-chain risk signals.
          </p>
        </div>

        <div className="alerts-counter">
          <Bell size={18} />
          <span>{activeAlerts} Active</span>
        </div>
      </section>

      <section className="alerts-summary">
        <div className="alert-summary-card">
          <div className="alert-summary-icon critical">
            <ShieldAlert size={20} />
          </div>

          <div>
            <strong>1</strong>
            <span>Critical</span>
          </div>
        </div>

        <div className="alert-summary-card">
          <div className="alert-summary-icon high">
            <AlertTriangle size={20} />
          </div>

          <div>
            <strong>1</strong>
            <span>High Risk</span>
          </div>
        </div>

        <div className="alert-summary-card">
          <div className="alert-summary-icon verification">
            <ShieldCheck size={20} />
          </div>

          <div>
            <strong>1</strong>
            <span>Needs Verification</span>
          </div>
        </div>

        <div className="alert-summary-card">
          <div className="alert-summary-icon resolved">
            <CheckCircle2 size={20} />
          </div>

          <div>
            <strong>1</strong>
            <span>Resolved</span>
          </div>
        </div>
      </section>

      <section className="alerts-container">
        <div className="alerts-section-heading">
          <div>
            <span>DEPENDENCY ALERTS</span>
            <h2>Recent Activity</h2>
          </div>

          <button className="alerts-filter">
            All Alerts
          </button>
        </div>

        <div className="alerts-list">
          {alerts.map((alert) => {
            const Icon = iconMap[alert.type];

            return (
              <article
                className={`alert-card ${alert.type}`}
                key={alert.id}
              >
                <div className="alert-card-icon">
                  <Icon size={21} />
                </div>

                <div className="alert-card-content">
                  <div className="alert-title-row">
                    <div>
                      <span className="alert-type">
                        {alert.title}
                      </span>

                      <h3>{alert.entity}</h3>
                    </div>

                    {alert.score !== undefined && (
                      <div className="alert-score">
                        <strong>{alert.score}</strong>
                        <span>/100</span>
                      </div>
                    )}
                  </div>

                  <p>{alert.description}</p>

                  <div className="alert-footer">
                    <span className="alert-time">
                      <Clock3 size={14} />
                      {alert.time}
                    </span>

                    <button className="alert-action">
                      {alert.type === "verification"
                        ? "Review"
                        : alert.type === "resolved"
                        ? "View Details"
                        : "View Risk"}

                      <ArrowRight size={15} />
                    </button>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}

export default Alerts;
