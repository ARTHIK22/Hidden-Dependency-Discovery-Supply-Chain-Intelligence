import type { ReactNode } from "react";
import { useState } from "react";
import { ArrowLeft, ArrowRight, Building2, Check, Database, Globe2, Layers3, Network, Search, ShieldCheck, Sparkles, Target } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { createInvestigation, startInvestigation } from "../../features/investigations/investigation.api";
import { userMessage } from "../../services/api/errors";
import Button from "../../components/ui/Button/Button";
import Card from "../../components/ui/Card/Card";
import PageContainer from "../../components/layout/PageContainer";
import "./investigation.css";

type InvestigationDepth = "standard" | "deep" | "maximum";

function CreateInvestigation() {
  const navigate = useNavigate();
  const [goal, setGoal] = useState("");
  const [depth, setDepth] = useState<InvestigationDepth>("deep");
  const [includeGeography, setIncludeGeography] = useState(true);
  const [includeMaterials, setIncludeMaterials] = useState(true);
  const [includeManufacturers, setIncludeManufacturers] = useState(true);
  const [sourceVerification, setSourceVerification] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const canStart = goal.trim().length >= 20;
  const handleStart = async () => {
    if (!canStart) return;

    setError(""); setBusy(true);
    try {
      const investigation = await createInvestigation({ name: goal.trim().slice(0, 255), description: goal.trim(), priority: "medium" });
      sessionStorage.setItem("active_investigation_id", investigation.id);
      await startInvestigation(investigation.id);
      navigate(`/investigations/${investigation.id}`);
    } catch (reason) { setError(userMessage(reason)); } finally { setBusy(false); }
  };

  return <PageContainer><div className="create-investigation animate-fade">
    <div className="investigation-page-header"><button className="back-button" onClick={() => navigate("/")}><ArrowLeft size={16} />Back to Overview</button><div className="investigation-title-row"><div><div className="eyebrow">NEW INVESTIGATION</div><h1>What should we investigate?</h1><p>Describe the dependency question in natural language. The investigation engine will determine what to research and how deeply to follow the dependency chain.</p></div><div className="investigation-title-icon"><Sparkles size={25} /></div></div></div>
    <div className="investigation-builder"><div className="investigation-main">
      <Card className="goal-card"><div className="card-heading"><div className="heading-icon"><Target size={18} /></div><div><h2>Investigation Goal</h2><p>Tell the system what you want to discover.</p></div></div><label className="field-label">Investigation objective</label><textarea className="investigation-textarea" value={goal} onChange={(event) => setGoal(event.target.value)} placeholder="Example: Investigate the hidden dependencies of our battery supply chain and identify suppliers, manufacturers, raw materials and geographic dependencies that could create operational risk." /><div className="textarea-footer"><span>{goal.length} characters</span><span>Minimum 20 characters</span></div><div className="example-section"><span className="field-label">Try an example</span><button className="example-prompt" onClick={() => setGoal("Investigate the upstream dependencies of our battery supply chain and identify suppliers, manufacturers, raw materials and geographic dependencies that could create disruption risk.")}><Search size={14} />Battery supply chain dependencies</button><button className="example-prompt" onClick={() => setGoal("Map the hidden upstream dependencies of our semiconductor suppliers and identify critical manufacturers, materials and geographic concentrations.")}><Network size={14} />Semiconductor dependency mapping</button></div></Card>
      <Card className="scope-card"><div className="card-heading"><div className="heading-icon"><Layers3 size={18} /></div><div><h2>Dependency Scope</h2><p>Scope options are not yet supported by the backend.</p></div></div><div className="scope-grid"><ScopeOption icon={<Building2 size={18} />} title="Manufacturers" description="Not applied by the current API" enabled={includeManufacturers} disabled onClick={() => undefined} /><ScopeOption icon={<Database size={18} />} title="Materials" description="Not applied by the current API" enabled={includeMaterials} disabled onClick={() => undefined} /><ScopeOption icon={<Globe2 size={18} />} title="Geography" description="Not applied by the current API" enabled={includeGeography} disabled onClick={() => undefined} /><ScopeOption icon={<ShieldCheck size={18} />} title="Verification" description="Uses stored relationship evidence" enabled={sourceVerification} disabled onClick={() => undefined} /></div></Card>
    </div><aside className="investigation-sidebar">
      <Card className="depth-card"><div className="card-heading"><div className="heading-icon"><Network size={18} /></div><div><h2>Investigation Depth</h2><p>Depth controls are not accepted by the backend yet.</p></div></div><div className="depth-options"><DepthOption title="Standard" description="Not applied by the current API" selected={depth === "standard"} disabled onClick={() => undefined} /><DepthOption title="Deep" description="Not applied by the current API" selected={depth === "deep"} recommended disabled onClick={() => undefined} /><DepthOption title="Maximum" description="Not applied by the current API" selected={depth === "maximum"} disabled onClick={() => undefined} /></div></Card>
      <Card className="engine-card"><div className="engine-header"><div className="engine-icon"><Sparkles size={17} /></div><div><span>INVESTIGATION ENGINE</span><strong>Local analysis</strong></div></div><div className="engine-flow"><EngineStep number="01" title="Plan" active /><EngineLine /><EngineStep number="02" title="Stored evidence" /><EngineLine /><EngineStep number="03" title="Verify" /><EngineLine /><EngineStep number="04" title="Risk & report" /></div><div className="engine-note"><ShieldCheck size={14} />External research is not configured; this run analyzes stored records and marks research skipped.</div></Card>
      <div className="start-investigation">{error && <p role="alert" className="auth-error">{error}</p>}<Button size="lg" fullWidth disabled={!canStart || busy} onClick={handleStart}>{busy ? "Saving and analyzing…" : "Start Investigation"}<ArrowRight size={17} /></Button>{!canStart && <span>Describe an investigation goal to continue.</span>}<small>Selected depth and scope controls are not yet supported by the backend.</small></div>
    </aside></div>
  </div></PageContainer>;
}

function ScopeOption({ icon, title, description, enabled, disabled, onClick }: { icon: ReactNode; title: string; description: string; enabled: boolean; disabled?: boolean; onClick: () => void }) { return <button className={`scope-option ${enabled ? "enabled" : ""}`} onClick={onClick} disabled={disabled} type="button"><div className="scope-icon">{icon}</div><div className="scope-content"><strong>{title}</strong><span>{description}</span></div><div className="scope-check">{enabled && <Check size={13} />}</div></button>; }
function DepthOption({ title, description, selected, recommended, disabled, onClick }: { title: string; description: string; selected: boolean; recommended?: boolean; disabled?: boolean; onClick: () => void }) { return <button type="button" disabled={disabled} className={`depth-option ${selected ? "selected" : ""}`} onClick={onClick}><div className="depth-radio">{selected && <span />}</div><div className="depth-content"><div className="depth-title"><strong>{title}</strong>{recommended && <span className="recommended">RECOMMENDED</span>}</div><p>{description}</p></div></button>; }
function EngineStep({ number, title, active = false }: { number: string; title: string; active?: boolean }) { return <div className={`engine-step ${active ? "active" : ""}`}><span>{number}</span><strong>{title}</strong></div>; }
function EngineLine() { return <div className="engine-line" />; }
export default CreateInvestigation;
