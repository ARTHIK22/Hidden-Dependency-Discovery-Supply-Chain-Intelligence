import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowUpRight, CircleAlert, Clock3, Database, Factory, MapPin, Network, Search, ShieldCheck, Sparkles } from "lucide-react";
import Button from "../../components/ui/Button/Button";
import Card from "../../components/ui/Card/Card";
import Badge from "../../components/ui/Badge/Badge";
import PageContainer from "../../components/layout/PageContainer";
import "./dashboard.css";

const stats = [
	{ label: "Investigations", value: "24", change: "+4 this month", icon: Search },
	{ label: "Entities Discovered", value: "1,284", change: "+182 this week", icon: Database },
	{ label: "Relationships", value: "3,691", change: "+427 this week", icon: Network },
	{ label: "Verified Sources", value: "8,432", change: "+12.4%", icon: ShieldCheck },
];

const investigations = [
	{ name: "Battery Supply Chain", description: "Lithium-ion upstream dependency mapping", status: "Completed" as const, entities: "184 entities", time: "2h ago" },
	{ name: "Semiconductor Network", description: "Critical chip manufacturing dependencies", status: "Running" as const, entities: "97 entities", time: "38m ago" },
	{ name: "EV Components", description: "Tier-2 and Tier-3 supplier discovery", status: "Completed" as const, entities: "243 entities", time: "Yesterday" },
	{ name: "Rare Earth Materials", description: "Geographic dependency investigation", status: "Review" as const, entities: "76 entities", time: "2d ago" },
];

function Overview() {
	const navigate = useNavigate();
	return <PageContainer><div className="dashboard animate-fade">
		<section className="dashboard-hero glass"><div className="hero-content"><div className="hero-label"><Sparkles size={14} />AI INVESTIGATION ENGINE</div><h2>Discover what your<br />business actually depends on.</h2><p>Investigate hidden suppliers, manufacturers, materials and geographic dependencies using autonomous AI research.</p><div className="hero-actions"><Button size="lg" onClick={() => navigate("/investigations/new")}><Search size={17} />Start Investigation<ArrowUpRight size={16} /></Button><Button variant="secondary" size="lg"><Network size={16} />Explore Graph</Button></div></div><div className="hero-orbit"><div className="orbit-ring orbit-ring-one" /><div className="orbit-ring orbit-ring-two" /><div className="orbit-line line-one" /><div className="orbit-line line-two" /><div className="orbit-line line-three" /><div className="orbit-core"><Network size={30} /></div><div className="orbit-node node-one"><Factory size={12} />Supplier</div><div className="orbit-node node-two"><Database size={12} />Material</div><div className="orbit-node node-three"><MapPin size={12} />Region</div></div></section>
		<section className="stats-grid">{stats.map(({ label, value, change, icon: Icon }) => <Card key={label} hover className="stat-card"><div className="stat-icon"><Icon size={18} /></div><div className="stat-content"><span>{label}</span><strong>{value}</strong><small>{change}</small></div></Card>)}</section>
		<section className="dashboard-grid"><Card className="investigations-card"><SectionHeading eyebrow="WORKSPACE" title="Recent Investigations" action="View all" /><div className="investigation-list">{investigations.map((investigation) => <InvestigationRow key={investigation.name} {...investigation} />)}</div></Card><Card className="risk-card"><SectionHeading eyebrow="INTELLIGENCE" title="Dependency Risk" icon={<ShieldCheck size={19} className="section-icon" />} /><div className="risk-score"><div className="risk-number">68</div><div className="risk-score-info"><strong>Moderate Exposure</strong><span>Based on current evidence</span></div></div><div className="risk-bar"><div /></div><div className="risk-scale"><span>Low</span><span>Moderate</span><span>High</span></div><div className="risk-items"><RiskItem label="Geographic concentration" value="High" severity="danger" /><RiskItem label="Single-source dependency" value="Medium" severity="warning" /><RiskItem label="Evidence confidence" value="High" severity="success" /></div></Card></section>
		<section className="bottom-grid"><Card className="dependency-card"><SectionHeading eyebrow="DEPENDENCY INTELLIGENCE" title="Dependency Snapshot" action="Open graph" /><div className="dependency-flow"><DependencyNode type="company" title="Your Company" subtitle="Root organization" /><FlowConnector label="SUPPLIES" /><DependencyNode type="supplier" title="Supplier A" subtitle="Direct supplier" /><FlowConnector label="DEPENDS ON" /><DependencyNode type="material" title="Raw Material" subtitle="Upstream dependency" /><FlowConnector label="LOCATED IN" /><DependencyNode type="region" title="Region X" subtitle="Geographic dependency" /></div></Card><Card className="activity-card"><SectionHeading eyebrow="LIVE" title="Activity" live /><div className="activity-list"><ActivityItem icon={<Network size={14} />} title="Relationship verified" description="ABC → XYZ Manufacturing" time="2 min" /><ActivityItem icon={<Database size={14} />} title="Entity discovered" description="Lithium Processing Facility" time="8 min" /><ActivityItem icon={<ShieldCheck size={14} />} title="Source verified" description="Government registry" time="14 min" /><ActivityItem icon={<CircleAlert size={14} />} title="Potential dependency" description="Geographic concentration" time="21 min" /></div></Card></section>
	</div></PageContainer>;
}

function SectionHeading({ eyebrow, title, action, icon, live }: { eyebrow: string; title: string; action?: string; icon?: ReactNode; live?: boolean }) { return <div className="section-heading"><div><span className="eyebrow">{eyebrow}</span><h3>{title}</h3></div>{action ? <button className="text-button">{action}<ArrowUpRight size={14} /></button> : icon ?? (live && <span className="live-indicator"><span />Live</span>)}</div>; }
function InvestigationRow({ name, description, status, entities, time }: { name: string; description: string; status: "Completed" | "Running" | "Review"; entities: string; time: string }) { const variant = status === "Completed" ? "success" : status === "Running" ? "warning" : "default"; return <div className="investigation-row"><div className="investigation-icon"><Network size={16} /></div><div className="investigation-info"><strong>{name}</strong><span>{description}</span></div><div className="investigation-meta"><Badge variant={variant}>{status}</Badge><small>{entities}</small><small>{time}</small></div></div>; }
function RiskItem({ label, value, severity }: { label: string; value: string; severity: "danger" | "warning" | "success" }) { return <div className="risk-item"><span>{label}</span><strong className={`risk-${severity}`}>{value}</strong></div>; }
function DependencyNode({ type, title, subtitle }: { type: "company" | "supplier" | "material" | "region"; title: string; subtitle: string }) { const icons = { company: Network, supplier: Factory, material: Database, region: MapPin }; const Icon = icons[type]; return <div className={`dependency-node dependency-${type}`}><div className="dependency-node-icon"><Icon size={16} /></div><div><strong>{title}</strong><span>{subtitle}</span></div></div>; }
function FlowConnector({ label }: { label: string }) { return <div className="flow-connector"><span /><small>{label}</small><span /></div>; }
function ActivityItem({ icon, title, description, time }: { icon: ReactNode; title: string; description: string; time: string }) { return <div className="activity-item"><div className="activity-icon">{icon}</div><div className="activity-info"><strong>{title}</strong><span>{description}</span></div><small><Clock3 size={11} />{time}</small></div>; }

export default Overview;
