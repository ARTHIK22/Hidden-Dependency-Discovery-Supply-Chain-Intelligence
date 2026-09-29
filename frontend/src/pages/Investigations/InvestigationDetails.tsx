import type { ElementType } from "react";
import { useEffect, useState } from "react";
import { ArrowLeft, Check, ChevronRight, Database, Factory, FileSearch, Globe2, Loader2, Network, Search, ShieldCheck, Sparkles, Timer } from "lucide-react";
import { useNavigate } from "react-router-dom";
import Card from "../../components/ui/Card/Card";
import Badge from "../../components/ui/Badge/Badge";
import Button from "../../components/ui/Button/Button";
import PageContainer from "../../components/layout/PageContainer";
import "./investigation-details.css";

type AgentStatus = "pending" | "running" | "completed";
interface Agent { id: string; name: string; description: string; status: AgentStatus; icon: ElementType; }
interface ActivityEvent { id: number; type: string; title: string; description: string; time: string; icon: ElementType; }
const initialAgents: Agent[] = [
  { id: "planner", name: "Planning Agent", description: "Breaking the investigation goal into research tasks", status: "running", icon: Sparkles },
  { id: "research", name: "Research Agent", description: "Searching permitted external information sources", status: "pending", icon: Search },
  { id: "entities", name: "Entity Discovery", description: "Identifying suppliers, manufacturers and facilities", status: "pending", icon: Database },
  { id: "relationships", name: "Relationship Discovery", description: "Finding connections between discovered entities", status: "pending", icon: Network },
  { id: "verification", name: "Verification Agent", description: "Checking relationships against source evidence", status: "pending", icon: ShieldCheck },
  { id: "graph", name: "Graph Builder", description: "Constructing the dependency intelligence graph", status: "pending", icon: Network },
];
const demoEvents: Omit<ActivityEvent, "id" | "time">[] = [
  { type: "agent", title: "Planning Agent started", description: "Investigation plan created with 6 research stages", icon: Sparkles },
  { type: "source", title: "Source discovered", description: "Corporate supplier information identified", icon: FileSearch },
  { type: "entity", title: "Entity discovered", description: "XYZ Manufacturing identified as a manufacturer", icon: Factory },
  { type: "relationship", title: "Relationship found", description: "ABC Electronics → SUPPLIES → XYZ Manufacturing", icon: Network },
  { type: "entity", title: "Geographic dependency discovered", description: "Production facility associated with Region X", icon: Globe2 },
];

function InvestigationDetails() {
  const navigate = useNavigate();
  const [agents, setAgents] = useState<Agent[]>(initialAgents);
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    const sequence = [
      { delay: 2200, agent: "planner", next: "research" }, { delay: 4500, agent: "research", next: "entities" },
      { delay: 7000, agent: "entities", next: "relationships" }, { delay: 9500, agent: "relationships", next: "verification" },
      { delay: 12000, agent: "verification", next: "graph" }, { delay: 14500, agent: "graph", next: null },
    ];
    const timers = sequence.map(({ delay, agent, next }, index) => setTimeout(() => {
      setAgents((current) => current.map((item) => item.id === agent ? { ...item, status: "completed" } : item.id === next ? { ...item, status: "running" } : item));
      const demoEvent = demoEvents[index];
      if (demoEvent) setEvents((current) => [{ ...demoEvent, id: Date.now(), time: "just now" }, ...current]);
      if (!next) setIsComplete(true);
    }, delay));
    return () => timers.forEach(clearTimeout);
  }, []);

  useEffect(() => {
    if (isComplete) return;
    const timer = setInterval(() => setElapsedSeconds((value) => value + 1), 1000);
    return () => clearInterval(timer);
  }, [isComplete]);

  const completedAgents = agents.filter((agent) => agent.status === "completed").length;
  const progress = completedAgents / agents.length * 100;
  return <PageContainer><div className="investigation-execution animate-fade">
    <div className="execution-header"><button className="back-button" onClick={() => navigate("/")}><ArrowLeft size={16} />Dashboard</button><div className="execution-title"><div><div className="eyebrow">LIVE INVESTIGATION</div><h1>Battery Supply Chain</h1><p>Investigating upstream suppliers, manufacturers, materials and geographic dependencies.</p></div><div className="execution-status">{isComplete ? <><Check size={14} />Investigation complete</> : <><span className="pulse-dot" />Investigation running</>}</div></div></div>
    <Card className="execution-progress-card"><div className="progress-top"><div><span className="progress-label">INVESTIGATION PROGRESS</span><strong>{isComplete ? "Investigation complete" : "AI agents are investigating dependencies"}</strong></div><div className="progress-percent">{Math.round(progress)}%</div></div><div className="execution-progress-bar"><div style={{ width: `${progress}%` }} /></div><div className="progress-footer"><span>{completedAgents} of {agents.length} stages completed</span><span className="elapsed"><Timer size={12} />{formatTime(elapsedSeconds)}</span></div></Card>
    <div className="execution-grid"><Card className="agent-pipeline-card"><div className="section-heading"><div><span className="eyebrow">AGENT PIPELINE</span><h2>Investigation workflow</h2></div><Badge variant={isComplete ? "success" : "warning"}>{isComplete ? "Completed" : "Running"}</Badge></div><div className="agent-pipeline">{agents.map((agent, index) => <AgentPipelineItem key={agent.id} agent={agent} last={index === agents.length - 1} />)}</div></Card><Card className="activity-feed-card"><div className="section-heading"><div><span className="eyebrow">LIVE FEED</span><h2>Investigation activity</h2></div><span className="live-indicator"><span />Live</span></div><div className="execution-events">{events.length === 0 ? <div className="waiting-state"><Loader2 size={22} className="spin" /><span>Waiting for investigation events...</span></div> : events.map((event) => <ActivityEventItem key={event.id} event={event} />)}</div></Card></div>
    <section className="discovery-summary"><DiscoveryCard icon={Database} label="ENTITIES" value={isComplete ? "184" : "47"} detail="discovered" /><DiscoveryCard icon={Network} label="RELATIONSHIPS" value={isComplete ? "312" : "86"} detail="discovered" /><DiscoveryCard icon={FileSearch} label="SOURCES" value={isComplete ? "428" : "73"} detail="collected" /><DiscoveryCard icon={ShieldCheck} label="VERIFIED" value={isComplete ? "91%" : "78%"} detail="evidence confidence" /></section>
    {isComplete && <Card className="completion-card"><div className="completion-icon"><Check size={20} /></div><div className="completion-content"><span className="eyebrow">INVESTIGATION COMPLETE</span><h2>Your dependency intelligence graph is ready.</h2><p>184 entities and 312 relationships were discovered across 428 sources.</p></div><Button size="md" onClick={() => navigate("/graph")}>Explore Dependency Graph<ChevronRight size={16} /></Button></Card>}
  </div></PageContainer>;
}

function AgentPipelineItem({ agent, last }: { agent: Agent; last: boolean }) { const Icon = agent.icon; return <div className="agent-pipeline-item"><div className="agent-status-column"><div className={`agent-status-circle ${agent.status}`}>{agent.status === "completed" ? <Check size={15} /> : agent.status === "running" ? <Loader2 size={15} className="spin" /> : <Icon size={14} />}</div>{!last && <div className={`agent-connector ${agent.status === "completed" ? "completed" : ""}`} />}</div><div className="agent-info"><div className="agent-name-row"><strong>{agent.name}</strong><AgentStatusBadge status={agent.status} /></div><p>{agent.description}</p></div></div>; }
function AgentStatusBadge({ status }: { status: AgentStatus }) { return <span className={`agent-badge ${status}`}>{status === "completed" ? "Completed" : status === "running" ? "Running" : "Waiting"}</span>; }
function ActivityEventItem({ event }: { event: ActivityEvent }) { const Icon = event.icon; return <div className="execution-event"><div className="event-icon"><Icon size={14} /></div><div className="event-content"><strong>{event.title}</strong><span>{event.description}</span><small>{event.time}</small></div></div>; }
function DiscoveryCard({ icon: Icon, label, value, detail }: { icon: ElementType; label: string; value: string; detail: string }) { return <Card className="discovery-card"><div className="discovery-icon"><Icon size={19} /></div><div><span>{label}</span><strong>{value}</strong><small>{detail}</small></div></Card>; }
function formatTime(seconds: number) { return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`; }
export default InvestigationDetails;
