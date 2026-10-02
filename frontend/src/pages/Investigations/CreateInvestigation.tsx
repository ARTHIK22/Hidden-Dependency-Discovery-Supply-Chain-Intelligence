import type { ReactNode } from "react";
import { useState } from "react";
import { ArrowLeft, ArrowRight, Building2, Check, Database, Globe2, Layers3, Network, Search, ShieldCheck, Sparkles, Target } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { createInvestigation } from "../../features/investigations/investigation.api";
import Button from "../../components/ui/Button/Button";
import Card from "../../components/ui/Card/Card";
import PageContainer from "../../components/layout/PageContainer";
import { useToast } from "../../components/toast/ToastProvider";
import "./investigation.css";

type InvestigationDepth = "standard" | "deep" | "maximum";

function CreateInvestigation() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [goal, setGoal] = useState("");
  const [depth, setDepth] = useState<InvestigationDepth>("deep");
  const [includeGeography, setIncludeGeography] = useState(true);
  const [includeMaterials, setIncludeMaterials] = useState(true);
  const [includeManufacturers, setIncludeManufacturers] = useState(true);
  const [sourceVerification, setSourceVerification] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const canStart = goal.trim().length >= 20;
  const handleStart = async () => {
    if (!canStart) return;

    setSubmitting(true);
    try {
      const data = await createInvestigation({
        goal: goal.trim(),
        scope_manufacturers: includeManufacturers,
        scope_materials: includeMaterials,
        scope_geography: includeGeography,
        scope_verification: sourceVerification,
        depth,
      });
      sessionStorage.setItem(
        "active_investigation_id",
        data.investigation.id
      );

      toast.success("Investigation plan is ready.");
      navigate(`/investigations/${data.investigation.id}`);
    } catch (error) {
      console.error(error);
      toast.error(error instanceof Error ? error.message : "Unable to save the investigation.");
    } finally {
      setSubmitting(false);
    }
  };

  return <PageContainer><div className="create-investigation animate-fade">
      <div className="investigation-page-header"><button className="back-button" onClick={() => navigate("/")}><ArrowLeft size={16} />Back to Overview</button><div className="investigation-title-row"><div><div className="eyebrow">NEW INVESTIGATION</div><h1>What would you like to investigate?</h1><p>Turn a supply-chain goal into a structured investigation plan. External research has not started in this phase.</p></div><div className="investigation-title-icon"><Sparkles size={25} /></div></div></div>
    <div className="investigation-builder"><div className="investigation-main">
      <Card className="goal-card"><div className="card-heading"><div className="heading-icon"><Target size={18} /></div><div><h2>Investigation Goal</h2><p>Tell the system what you want to discover.</p></div></div><label className="field-label">Investigation objective</label><textarea className="investigation-textarea" value={goal} onChange={(event) => setGoal(event.target.value)} placeholder="Example: Investigate the hidden dependencies of our battery supply chain and identify suppliers, manufacturers, raw materials and geographic dependencies that could create operational risk." /><div className="textarea-footer"><span>{goal.length} characters</span><span>Minimum 20 characters</span></div><div className="example-section"><span className="field-label">Try an example</span><button className="example-prompt" onClick={() => setGoal("Investigate the upstream dependencies of our battery supply chain and identify suppliers, manufacturers, raw materials and geographic dependencies that could create disruption risk.")}><Search size={14} />Battery supply chain dependencies</button><button className="example-prompt" onClick={() => setGoal("Map the hidden upstream dependencies of our semiconductor suppliers and identify critical manufacturers, materials and geographic concentrations.")}><Network size={14} />Semiconductor dependency mapping</button></div></Card>
      <Card className="scope-card"><div className="card-heading"><div className="heading-icon"><Layers3 size={18} /></div><div><h2>Dependency Scope</h2><p>Choose which dimensions the investigation should follow.</p></div></div><div className="scope-grid"><ScopeOption icon={<Building2 size={18} />} title="Manufacturers" description="Factories and production entities" enabled={includeManufacturers} onClick={() => setIncludeManufacturers(!includeManufacturers)} /><ScopeOption icon={<Database size={18} />} title="Materials" description="Raw materials and components" enabled={includeMaterials} onClick={() => setIncludeMaterials(!includeMaterials)} /><ScopeOption icon={<Globe2 size={18} />} title="Geography" description="Regions and facilities" enabled={includeGeography} onClick={() => setIncludeGeography(!includeGeography)} /><ScopeOption icon={<ShieldCheck size={18} />} title="Verification" description="Source-backed relationships" enabled={sourceVerification} onClick={() => setSourceVerification(!sourceVerification)} /></div></Card>
    </div><aside className="investigation-sidebar">
      <Card className="depth-card"><div className="card-heading"><div className="heading-icon"><Network size={18} /></div><div><h2>Investigation Depth</h2><p>How far should the dependency graph expand?</p></div></div><div className="depth-options"><DepthOption title="Standard" description="Direct and immediate upstream dependencies" selected={depth === "standard"} onClick={() => setDepth("standard")} /><DepthOption title="Deep" description="Follow multiple upstream dependency levels" selected={depth === "deep"} recommended onClick={() => setDepth("deep")} /><DepthOption title="Maximum" description="Continue expanding until evidence becomes limited" selected={depth === "maximum"} onClick={() => setDepth("maximum")} /></div></Card>
      <Card className="engine-card"><div className="engine-header"><div className="engine-icon"><Sparkles size={17} /></div><div><span>PLANNER STATUS</span><strong>{submitting ? "Planning..." : "Ready"}</strong></div></div><div className="engine-flow"><EngineStep number="01" title="Plan goal" active={submitting} /><EngineLine /><EngineStep number="02" title="Save plan" /></div><div className="engine-note"><ShieldCheck size={14} />The plan is stored in PostgreSQL. Research has not started.</div></Card>
      <div className="start-investigation"><Button size="lg" fullWidth disabled={!canStart || submitting} onClick={handleStart}>{submitting ? "Planning investigation..." : "Save Investigation"}<ArrowRight size={17} /></Button>{!canStart && <span>Describe an investigation goal to continue.</span>}</div>
    </aside></div>
  </div></PageContainer>;
}

function ScopeOption({ icon, title, description, enabled, onClick }: { icon: ReactNode; title: string; description: string; enabled: boolean; onClick: () => void }) { return <button className={`scope-option ${enabled ? "enabled" : ""}`} onClick={onClick} type="button"><div className="scope-icon">{icon}</div><div className="scope-content"><strong>{title}</strong><span>{description}</span></div><div className="scope-check">{enabled && <Check size={13} />}</div></button>; }
function DepthOption({ title, description, selected, recommended, onClick }: { title: string; description: string; selected: boolean; recommended?: boolean; onClick: () => void }) { return <button type="button" className={`depth-option ${selected ? "selected" : ""}`} onClick={onClick}><div className="depth-radio">{selected && <span />}</div><div className="depth-content"><div className="depth-title"><strong>{title}</strong>{recommended && <span className="recommended">RECOMMENDED</span>}</div><p>{description}</p></div></button>; }
function EngineStep({ number, title, active = false }: { number: string; title: string; active?: boolean }) { return <div className={`engine-step ${active ? "active" : ""}`}><span>{number}</span><strong>{title}</strong></div>; }
function EngineLine() { return <div className="engine-line" />; }
export default CreateInvestigation;
