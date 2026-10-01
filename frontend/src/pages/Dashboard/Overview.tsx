import { useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowUpRight, Clock3, Database, Factory, Globe2, Network, Search, ShieldCheck, Sparkles } from "lucide-react";
import Button from "../../components/ui/Button/Button";
import Card from "../../components/ui/Card/Card";
import Badge from "../../components/ui/Badge/Badge";
import PageContainer from "../../components/layout/PageContainer";
import { ErrorState, LoadingState } from "../../components/states/AsyncStates";
import { getDashboardSummary } from "../../services/api/dashboard";
import { getRiskSummary } from "../../features/risks/risk.api";
import type { DashboardSummary } from "../../types/api.types";
import "./dashboard.css";

type RiskSummary = { total: number; high_risk: number; average_score: number };

function Overview() {
	const navigate = useNavigate();
	const [summary, setSummary] = useState<DashboardSummary | null>(null);
	const [risk, setRisk] = useState<RiskSummary | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState(false);

	useEffect(() => {
		const controller = new AbortController();
		Promise.all([
			getDashboardSummary(controller.signal),
			getRiskSummary(controller.signal),
		])
			.then(([dashboard, riskSummary]) => {
				setSummary(dashboard);
				setRisk(riskSummary);
				setError(false);
			})
			.catch((cause) => {
				if (!controller.signal.aborted) {
					console.error("Unable to load dashboard data", cause);
					setError(true);
				}
			})
			.finally(() => {
				if (!controller.signal.aborted) setLoading(false);
			});
		return () => controller.abort();
	}, []);

	if (loading) return <PageContainer><LoadingState label="Loading dashboard data..." /></PageContainer>;
	if (error || !summary || !risk) return <PageContainer><ErrorState title="Dashboard data is unavailable" description="Check the backend connection and database, then retry." action={() => window.location.reload()} /></PageContainer>;

	const stats = [
		{ label: "Investigations", value: summary.total_investigations, change: `${summary.active_investigations} queued or running`, icon: Search },
		{ label: "Entities Discovered", value: summary.discovered_entities, change: "Persisted records", icon: Database },
		{ label: "Relationships", value: summary.relationships, change: "Persisted records", icon: Network },
		{ label: "High Risk", value: summary.high_risk_dependencies, change: `${summary.unread_alerts} unread alerts`, icon: ShieldCheck },
	];

	return <PageContainer><div className="dashboard animate-fade">
		{summary.demo_mode && <div className="demo-mode-banner" role="status"><Sparkles size={16} /><span><strong>Demo mode</strong> · The sample supply-chain records are fictional and are not verified research.</span></div>}
		<section className="dashboard-hero glass"><div className="hero-content"><div className="hero-label"><Sparkles size={14} />SUPPLY CHAIN WORKSPACE</div><h2>Investigate hidden dependencies.</h2><p>Record investigation questions, review persisted entities and relationships, and track the evidence available in your workspace.</p><div className="hero-actions"><Button size="lg" onClick={() => navigate("/investigations/new")}><Search size={17} />Create Investigation<ArrowUpRight size={16} /></Button><Button variant="secondary" size="lg" onClick={() => navigate("/graph")}><Network size={16} />Explore Graph</Button></div></div><div className="hero-orbit"><div className="orbit-ring orbit-ring-one" /><div className="orbit-ring orbit-ring-two" /><div className="orbit-line line-one" /><div className="orbit-line line-two" /><div className="orbit-line line-three" /><div className="orbit-core"><Network size={30} /></div><div className="orbit-node node-one"><Factory size={12} />Supplier</div><div className="orbit-node node-two"><Database size={12} />Material</div><div className="orbit-node node-three"><Globe2 size={12} />Region</div></div></section>
		<section className="stats-grid">{stats.map(({ label, value, change, icon: Icon }) => <Card key={label} hover className="stat-card"><div className="stat-icon"><Icon size={18} /></div><div className="stat-content"><span>{label}</span><strong>{value.toLocaleString()}</strong><small>{change}</small></div></Card>)}</section>
		<section className="dashboard-grid"><Card className="investigations-card"><SectionHeading eyebrow="WORKSPACE" title="Recent Investigations" action="View all" onAction={() => navigate("/investigations")} /><div className="investigation-list">{summary.recent_investigations.length ? summary.recent_investigations.map((item) => <InvestigationRow key={item.id} name={item.name} description={item.goal} status={item.status} entities={item.created_at ? new Date(item.created_at).toLocaleDateString() : ""} time="Created" />) : <p className="empty-event">No investigations have been saved yet.</p>}</div></Card><Card className="risk-card"><SectionHeading eyebrow="INTELLIGENCE" title="Dependency Risk" icon={<ShieldCheck size={19} className="section-icon" />} /><div className="risk-score"><div className="risk-number">{Math.round(risk.average_score)}</div><div className="risk-score-info"><strong>{risk.total ? "Recorded risk score" : "No risk records"}</strong><span>{risk.total ? `${risk.total} persisted risk assessments` : "Risk scores appear when assessments are recorded."}</span></div></div><div className="risk-bar"><div style={{ width: `${Math.min(risk.average_score, 100)}%` }} /></div><div className="risk-scale"><span>Low</span><span>Moderate</span><span>High</span></div><div className="risk-items"><RiskItem label="High or critical records" value={`${risk.high_risk}`} severity={risk.high_risk ? "danger" : "success"} /><RiskItem label="All risk records" value={`${risk.total}`} severity="warning" /><RiskItem label="Risk average" value={`${Math.round(risk.average_score)}/100`} severity="success" /></div></Card></section>
		<section className="bottom-grid"><Card className="dependency-card"><SectionHeading eyebrow="DEPENDENCY INTELLIGENCE" title="Dependency Snapshot" action="Open graph" onAction={() => navigate("/graph")} /><div className="dependency-flow"><p className="empty-event">{summary.relationships ? `${summary.relationships} persisted relationships are available in the graph.` : "No dependency relationships have been recorded yet."}</p></div></Card><Card className="activity-card"><SectionHeading eyebrow="WORKSPACE" title="Activity" live={false} /><div className="activity-list"><ActivityItem icon={<Clock3 size={14} />} title="Activity feed unavailable" description="The backend does not yet record an activity timeline." time="" /></div></Card></section>
	</div></PageContainer>;
}

function SectionHeading({ eyebrow, title, action, icon, live, onAction }: { eyebrow: string; title: string; action?: string; icon?: ReactNode; live?: boolean; onAction?: () => void }) { return <div className="section-heading"><div><span className="eyebrow">{eyebrow}</span><h3>{title}</h3></div>{action ? <button className="text-button" onClick={onAction}>{action}<ArrowUpRight size={14} /></button> : icon ?? (live && <span className="live-indicator"><span />Live</span>)}</div>; }
function InvestigationRow({ name, description, status, entities, time }: { name: string; description: string; status: string; entities: string; time: string }) { const normalized = status.toLowerCase(); const variant = normalized === "completed" ? "success" : normalized === "running" ? "warning" : "default"; return <div className="investigation-row"><div className="investigation-icon"><Network size={16} /></div><div className="investigation-info"><strong>{name}</strong><span>{description}</span></div><div className="investigation-meta"><Badge variant={variant}>{status}</Badge><small>{entities}</small><small>{time}</small></div></div>; }
function RiskItem({ label, value, severity }: { label: string; value: string; severity: "danger" | "warning" | "success" }) { return <div className="risk-item"><span>{label}</span><strong className={`risk-${severity}`}>{value}</strong></div>; }
function ActivityItem({ icon, title, description, time }: { icon: ReactNode; title: string; description: string; time: string }) { return <div className="activity-item"><div className="activity-icon">{icon}</div><div className="activity-info"><strong>{title}</strong><span>{description}</span></div>{time && <small><Clock3 size={11} />{time}</small>}</div>; }

export default Overview;
