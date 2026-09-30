import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  CheckCircle2,
  Circle,
  Clock3,
  Database,
  GitBranch,
  Globe2,
  ShieldCheck,
  Sparkles,
  Users,
  AlertTriangle,
  ArrowRight,
} from "lucide-react";
import "./investigation-details.css";

type AgentStatus = "pending" | "active" | "completed" | "error";

type Agent = {
  id: string;
  name: string;
  description: string;
  status: AgentStatus;
};

type EventItem = {
  id: string;
  agent: string;
  status: string;
  message: string;
};

const INITIAL_AGENTS: Agent[] = [
  {
    id: "planning",
    name: "Planning Agent",
    description: "Building investigation plan",
    status: "pending",
  },
  {
    id: "research",
    name: "Research Agent",
    description: "Discovering permitted sources",
    status: "pending",
  },
  {
    id: "entities",
    name: "Entity Discovery",
    description: "Resolving organizations and materials",
    status: "pending",
  },
  {
    id: "relationships",
    name: "Relationship Agent",
    description: "Connecting dependency relationships",
    status: "pending",
  },
  {
    id: "verification",
    name: "Verification Agent",
    description: "Checking evidence and confidence",
    status: "pending",
  },
  {
    id: "risk",
    name: "Risk Agent",
    description: "Identifying dependency risks",
    status: "pending",
  },
];

const agentNameToId: Record<string, string> = {
  "Planning Agent": "planning",
  "Research Agent": "research",
  "Entity Discovery": "entities",
  "Relationship Agent": "relationships",
  "Verification Agent": "verification",
  "Risk Agent": "risk",
};

function InvestigationDetails() {
  const navigate = useNavigate();

  const [agents, setAgents] = useState<Agent[]>(INITIAL_AGENTS);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [connected, setConnected] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [result, setResult] = useState<any>(null);

  const investigationId =
    sessionStorage.getItem("active_investigation_id") ||
    "demo-investigation";

  useEffect(() => {
    const socket = new WebSocket(
      `ws://localhost:8000/ws/investigations/${investigationId}`
    );

    socket.onopen = () => {
      setConnected(true);

      socket.send("start");
    };

    socket.onclose = () => {
      setConnected(false);
    };

    socket.onerror = () => {
      setConnected(false);
    };

    socket.onmessage = (message) => {
      try {
        const data = JSON.parse(message.data);

        if (data.type === "agent_started") {
          const agentId = agentNameToId[data.agent];

          if (agentId) {
            setAgents((current) =>
              current.map((agent) =>
                agent.id === agentId
                  ? { ...agent, status: "active" }
                  : agent
              )
            );
          }

          setEvents((current) => [
            {
              id: `${Date.now()}-${Math.random()}`,
              agent: data.agent,
              status: "ACTIVE",
              message: data.message || "Agent started.",
            },
            ...current,
          ]);
        }

        if (data.type === "agent_completed") {
          const agentId = agentNameToId[data.agent];

          if (agentId) {
            setAgents((current) =>
              current.map((agent) =>
                agent.id === agentId
                  ? { ...agent, status: "completed" }
                  : agent
              )
            );
          }

          setEvents((current) => [
            {
              id: `${Date.now()}-${Math.random()}`,
              agent: data.agent,
              status: "COMPLETED",
              message: data.message || "Agent completed successfully.",
            },
            ...current,
          ]);
        }

        if (data.type === "investigation_completed") {
          setCompleted(true);
          setResult(data.result);
        }
      } catch (error) {
        console.error("Invalid WebSocket message:", error);
      }
    };

    return () => {
      socket.close();
    };
  }, [investigationId]);

  const completedAgents = useMemo(
    () => agents.filter((agent) => agent.status === "completed").length,
    [agents]
  );

  const progress = Math.round(
    (completedAgents / agents.length) * 100
  );

  const summary = {
    entities: result?.entities?.length ?? 7,
    relationships: result?.relationships?.relationships?.length ?? 7,
    sources: result?.sources?.source_count ?? 3,
    verified:
      result?.relationships?.verified_count ??
      result?.verification?.verified_count ??
      5,
    risks: result?.risks?.length ?? 2,
  };

  return (
    <div className="investigation-page">
      <section className="investigation-hero">
        <div>
          <span className="eyebrow">LIVE INVESTIGATION</span>

          <h1>Battery Supply Chain</h1>

          <p>
            Investigating upstream suppliers, manufacturers,
            materials and geographic dependencies.
          </p>

          <div className="investigation-status">
            <span
              className={`status-dot ${
                connected ? "connected" : "disconnected"
              }`}
            />

            {completed
              ? "Investigation complete"
              : connected
              ? "Investigation running"
              : "Connecting to investigation engine..."}
          </div>
        </div>
      </section>

      <section className="glass-section progress-section">
        <div className="section-heading-row">
          <div>
            <span className="section-label">INVESTIGATION PROGRESS</span>
            <h2>{progress}%</h2>
          </div>

          <div className="progress-status">
            <Clock3 size={17} />

            {completed ? "Completed" : "Running"}
          </div>
        </div>

        <div className="progress-track">
          <div
            className="progress-fill"
            style={{ width: `${progress}%` }}
          />
        </div>
      </section>

      <section className="glass-section">
        <div className="section-heading-row pipeline-heading">
          <div>
            <span className="section-label">AGENT PIPELINE</span>
            <h2>Investigation Engine</h2>
          </div>

          <span className="agent-count">
            {completedAgents}/{agents.length}
          </span>
        </div>

        <div className="agent-list">
          {agents.map((agent, index) => (
            <div
              key={agent.id}
              className={`agent-row ${agent.status}`}
            >
              <div className="agent-step">
                <div className="agent-icon">
                  {agent.status === "completed" ? (
                    <CheckCircle2 size={19} />
                  ) : agent.status === "active" ? (
                    <Sparkles size={19} />
                  ) : (
                    <Circle size={18} />
                  )}
                </div>

                {index < agents.length - 1 && (
                  <div className="agent-connector" />
                )}
              </div>

              <div className="agent-content">
                <div className="agent-title-row">
                  <h3>{agent.name}</h3>

                  <span className={`agent-status ${agent.status}`}>
                    {agent.status === "completed"
                      ? "Completed"
                      : agent.status === "active"
                      ? "Active"
                      : "Waiting"}
                  </span>
                </div>

                <p>{agent.description}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="glass-section">
        <div className="section-heading-row">
          <div>
            <span className="section-label">LIVE ACTIVITY</span>
            <h2>Investigation Timeline</h2>
          </div>
        </div>

        <div className="event-feed">
          {events.length === 0 ? (
            <div className="empty-event">
              <Sparkles size={20} />
              Waiting for investigation events...
            </div>
          ) : (
            events.slice(0, 8).map((event) => (
              <div className="event-row" key={event.id}>
                <div className="event-icon">
                  {event.status === "COMPLETED" ? (
                    <CheckCircle2 size={17} />
                  ) : (
                    <Sparkles size={17} />
                  )}
                </div>

                <div className="event-content">
                  <div>
                    <strong>{event.agent}</strong>

                    <span className="event-status">
                      {event.status}
                    </span>
                  </div>

                  <p>{event.message}</p>
                </div>
              </div>
            ))
          )}
        </div>
      </section>

      <section className="glass-section">
        <div className="section-heading">
          <span className="section-label">DISCOVERY SUMMARY</span>
          <h2>What the engine found</h2>
        </div>

        <div className="summary-grid">
          <SummaryCard
            icon={<Users size={22} />}
            value={summary.entities}
            label="Entities"
          />

          <SummaryCard
            icon={<GitBranch size={22} />}
            value={summary.relationships}
            label="Relationships"
          />

          <SummaryCard
            icon={<Globe2 size={22} />}
            value={summary.sources}
            label="Sources"
          />

          <SummaryCard
            icon={<ShieldCheck size={22} />}
            value={summary.verified}
            label="Verified"
          />

          <SummaryCard
            icon={<AlertTriangle size={22} />}
            value={summary.risks}
            label="Risk Signals"
          />
        </div>
      </section>

      {completed && (
        <section className="completion-card">
          <div className="completion-icon">
            <CheckCircle2 size={28} />
          </div>

          <div className="completion-content">
            <span>INVESTIGATION COMPLETE</span>

            <h2>Your dependency intelligence graph is ready.</h2>

            <p>
              The investigation discovered <strong>{summary.entities}</strong>{" "}
              entities and <strong>{summary.relationships}</strong>{" "}
              relationships across <strong>{summary.sources}</strong> sources.
            </p>
          </div>

          <button
            className="graph-button"
            onClick={() => navigate("/graph")}
          >
            Explore Dependency Graph
            <ArrowRight size={18} />
          </button>
        </section>
      )}
    </div>
  );
}

function SummaryCard({
  icon,
  value,
  label,
}: {
  icon: React.ReactNode;
  value: number;
  label: string;
}) {
  return (
    <div className="summary-card">
      <div className="summary-icon">{icon}</div>

      <div className="summary-value">{value}</div>

      <div className="summary-label">{label}</div>
    </div>
  );
}

export default InvestigationDetails;
