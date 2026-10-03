import type { ReactNode } from "react";
import { AlertTriangle, ArrowUpRight, FileText, ShieldAlert } from "lucide-react";
import type { Report } from "../../types/api.types";

type Data = Record<string, unknown>;

export default function ReportDocument({ report }: { report: Report }) {
  const data = asRecord(report.structured_content);
  if (!Object.keys(data).length) return <LegacyReport content={report.content} />;

  const investigation = asRecord(data.investigation);
  const graph = asRecord(data.dependency_graph);
  const verification = asRecord(data.verification);
  const risk = asRecord(data.risk);
  const riskSummary = asRecord(risk.summary);
  const plan = asRecord(data.plan);
  const entities = asRecords(data.entities);
  const relationships = asRecords(data.relationships);
  const evidence = asRecords(data.evidence);
  const unknowns = asRecords(data.unknowns);
  const conflicts = asRecords(data.conflicts);
  const assessments = asRecords(risk.assessments);
  const alerts = asRecords(data.alerts);
  const statuses = asRecord(verification.status_counts);
  const demoOnly = data.demo_only === true;

  return <article className="report-content report-document" aria-label="Investigation report document">
    {demoOnly && <div className="report-document-demo"><ShieldAlert size={17} /><span><strong>DEMO ONLY</strong> — illustrative data. Verification states and evidence confidence are shown as saved.</span></div>}
    <header className="report-document-intro">
      <span className="eyebrow">SAVED INTELLIGENCE RECORD</span>
      <h2>{string(investigation.name, report.title)}</h2>
      <p>{string(investigation.goal, "No investigation goal was saved with this report.")}</p>
      <div className="report-document-meta"><StatusBadge value={string(investigation.status, "UNKNOWN")} /><span>Generated {formatDate(string(data.generated_at, report.created_at))}</span><span>Research: {string(asRecord(data.research).mode, "UNKNOWN")}</span></div>
    </header>

    <div className="report-document-stats" aria-label="Report record counts">
      <span>Entities: {entities.length}</span><span>Relationships: {relationships.length}</span><span>Evidence: {evidence.length}</span><span>Sources: {asRecords(data.sources).length}</span>
    </div>

    <ReportSection number="01" title="Investigation Summary">
      <div className="report-summary-grid">
        <InfoCard label="Investigation status"><StatusBadge value={string(investigation.status, "UNKNOWN")} /><span>{typeof investigation.progress === "number" ? `${Math.round(investigation.progress)}% complete` : "Progress was not recorded"}</span></InfoCard>
        <InfoCard label="Objective"><p>{string(investigation.objective, string(plan.objective, "No objective was saved."))}</p></InfoCard>
        <InfoCard label="Research mode"><p>{string(asRecord(data.research).mode, "UNKNOWN")}</p><small>Sources discovered: {asRecords(data.sources).length}</small></InfoCard>
        <InfoCard label="Investigation target"><p>{string(plan.target, "UNKNOWN")}</p>{string(plan.target_clarification, "") && <small>{string(plan.target_clarification, "")}</small>}</InfoCard>
      </div>
    </ReportSection>

    <ReportSection number="02" title="Entities Discovered" count={entities.length}>
      {entities.length ? <div className="report-record-grid">{entities.map((entity, index) => <div className="report-record-card" key={string(entity.id, `entity-${index}`)}>
        <div className="report-record-top"><span className="report-record-type">{string(entity.entity_type, "Entity")}</span><StatusBadge value={string(asRecord(entity.resolution).status, "UNKNOWN")} /></div>
        <h3>{string(entity.name, "Unnamed entity")}</h3>
        {string(entity.description, "") && <p>{string(entity.description, "")}</p>}
        {string(entity.jurisdiction, "") && <small>Jurisdiction · {string(entity.jurisdiction, "")}</small>}
        <RecordBadges demo={entity.demo_only === true || demoOnly} confidence={asRecord(entity.resolution).confidence} />
      </div>)}</div> : <EmptyRecords>No entity records were saved with this report.</EmptyRecords>}
    </ReportSection>

    <ReportSection number="03" title="Relationships" count={relationships.length}>
      {relationships.length ? <div className="report-relationship-list">{relationships.map((relationship, index) => <div className="report-relationship-card" key={string(relationship.id, `relationship-${index}`)}>
        <div className="report-relationship-flow"><span>{string(relationship.source_entity, "Unknown entity")}</span><i aria-hidden="true">→</i><strong>{string(relationship.relationship_type, "relationship")}</strong><i aria-hidden="true">→</i><span>{string(relationship.target_entity, "Unknown entity")}</span></div>
        <div className="report-record-top"><StatusBadge value={string(relationship.verification_status, "UNKNOWN")} /><RecordBadges demo={relationship.demo_only === true || demoOnly} confidence={relationship.confidence} /></div>
        {string(relationship.evidence_summary, "") && <p>{string(relationship.evidence_summary, "")}</p>}
        <small>{asRecords(relationship.evidence).length} linked evidence {asRecords(relationship.evidence).length === 1 ? "record" : "records"}</small>
      </div>)}</div> : <EmptyRecords>No relationship records were saved. The report does not infer missing dependencies.</EmptyRecords>}
    </ReportSection>

    <ReportSection number="04" title="Findings">
      <p className="report-section-lead">Findings below reflect the saved verification and risk records at report generation time.</p>
      <div className="report-finding-counts">
        <CountCard label="Verified relationships" value={valueOrCount(graph.verified_count, statuses.VERIFIED)} tone="verified" />
        <CountCard label="Conflicted relationships" value={valueOrCount(graph.conflicted_count, statuses.CONFLICTED)} tone="conflicted" />
        <CountCard label="Risk records" value={valueOrCount(risk.record_count, assessments.length)} tone="neutral" />
        <CountCard label="Alerts" value={alerts.length} tone="neutral" />
      </div>
      <div className="report-risk-summary">
        <span className="report-risk-summary-icon"><AlertTriangle size={17} /></span>
        <div><strong>Risk snapshot</strong><p>Overall score: {formatScore(riskSummary.overall_score)} · Level: {string(riskSummary.overall_level, "UNKNOWN")}</p><small>{string(risk.calculated_at, "No risk calculation time was saved.")}</small></div>
      </div>
      {assessments.length > 0 && <div className="report-assessment-list">{assessments.map((assessment, index) => <div className="report-assessment" key={string(assessment.target_id, `assessment-${index}`)}>
        <div><strong>{string(assessment.target_name, string(assessment.entity_name, string(assessment.target_id, "Risk assessment")))}</strong><small>{string(assessment.target_type, "Saved risk assessment")}</small></div>
        <StatusBadge value={string(assessment.level, string(assessment.status, "UNKNOWN"))} /><strong>{formatScore(assessment.score ?? assessment.risk_score)}</strong>
      </div>)}</div>}
      {alerts.length > 0 && <div className="report-alert-list">{alerts.map((alert, index) => <div className="report-alert-item" key={string(alert.id, `alert-${index}`)}><ShieldAlert size={16} /><div><strong>{string(alert.title, "Saved alert")}</strong><p>{string(alert.message, "")}</p></div><StatusBadge value={string(alert.severity, "UNKNOWN")} /></div>)}</div>}
    </ReportSection>

    <ReportSection number="05" title="Unknowns &amp; Conflicts" count={unknowns.length + conflicts.length}>
      {unknowns.length || conflicts.length ? <div className="report-uncertainty-list">
        {unknowns.map((item, index) => <UncertaintyCard key={string(item.id, `unknown-${index}`)} kind={string(item.kind, "Unknown")} status={string(item.status, "UNKNOWN")} reason={string(item.reason, string(item.factor, "No explanation was saved."))} reference={string(item.id, "")} />)}
        {conflicts.map((item, index) => <UncertaintyCard key={string(item.relationship_id, `conflict-${index}`)} kind={`Conflict · ${string(item.relationship_type, "relationship")}`} status="CONFLICTED" reason={string(item.reason, "Conflicting evidence was preserved in the source records.")} reference={string(item.relationship_id, "")} supportingEvidence={asStrings(item.supporting_evidence_ids)} conflictingEvidence={asStrings(item.conflicting_evidence_ids)} />)}
      </div> : <EmptyRecords>No unknown or conflicted records were listed in this saved report.</EmptyRecords>}
    </ReportSection>

    <ReportSection number="06" title="Evidence" count={evidence.length}>
      {evidence.length ? <div className="report-evidence-list">{evidence.map((item, index) => <div className="report-evidence-card" key={string(item.id, `evidence-${index}`)}>
        <div className="report-evidence-heading"><span className="report-evidence-icon"><FileText size={16} /></span><div><span className="report-record-type">{string(item.source_type, "Source record")}</span><h3>{string(item.title, string(item.source, "Untitled evidence"))}</h3></div><StatusBadge value={string(item.verification_status, "UNKNOWN")} /></div>
        <p>{string(item.excerpt, "No excerpt was saved with this evidence record.")}</p>
        <div className="report-evidence-meta"><span>{string(item.source, "Source not recorded")}</span><span>Confidence {formatConfidence(item.confidence)}</span><span>{item.published_date ? `Published ${formatDate(string(item.published_date, ""))}` : `Captured ${formatDate(string(item.captured_at, "Date not recorded"))}`}</span><code>Evidence ID · {string(item.id, "not recorded")}</code>{item.demo_only === true && <span className="report-demo-pill">DEMO</span>}{safeUrl(item.source_url) && <a href={safeUrl(item.source_url)!} target="_blank" rel="noreferrer">Open source <ArrowUpRight size={13} /></a>}</div>
      </div>)}</div> : <EmptyRecords>No evidence records were saved. Missing sources remain unknown.</EmptyRecords>}
      {asRecords(data.sources).length > 0 && <div className="report-source-note">{asRecords(data.sources).length} distinct source {asRecords(data.sources).length === 1 ? "record" : "records"} represented in this report.</div>}
    </ReportSection>

    <ReportSection number="07" title="Limitations">
      <div className="report-limitations"><ShieldAlert size={18} /><div><strong>Persisted records only</strong><p>This report reflects application records saved at the time it was generated. It does not infer missing suppliers, sources, relationships, or evidence. Unknown, conflicted, and demo states retain their saved labels.</p></div></div>
    </ReportSection>
    <footer className="report-document-footer">Report ID <code>{report.id}</code> · Generated {formatDate(report.created_at)}</footer>
  </article>;
}

function ReportSection({ number, title, count, children }: { number: string; title: string; count?: number; children: ReactNode }) {
  return <section className="report-document-section"><header><span>{number}</span><h2>{title}</h2>{count !== undefined && <small>{count}</small>}</header>{children}</section>;
}

function InfoCard({ label, children }: { label: string; children: ReactNode }) { return <div className="report-info-card"><span>{label}</span>{children}</div>; }
function CountCard({ label, value, tone }: { label: string; value: number; tone: string }) { return <div className={`report-count-card ${tone}`}><strong>{value}</strong><span>{label}</span></div>; }
function EmptyRecords({ children }: { children: ReactNode }) { return <p className="report-empty-records">{children}</p>; }
function StatusBadge({ value }: { value: string }) { const normalized = value.toUpperCase().replace(/[^A-Z0-9]+/g, "-"); return <span className={`report-status-badge status-${normalized.toLowerCase()}`}>{value.replace(/_/g, " ")}</span>; }
function RecordBadges({ demo, confidence }: { demo: boolean; confidence: unknown }) { return <span className="report-record-badges">{demo && <span className="report-demo-pill">DEMO</span>}{confidence !== undefined && confidence !== null && <span className="report-confidence">Confidence {formatConfidence(confidence)}</span>}</span>; }
function UncertaintyCard({ kind, status, reason, reference, supportingEvidence = [], conflictingEvidence = [] }: { kind: string; status: string; reason: string; reference?: string; supportingEvidence?: string[]; conflictingEvidence?: string[] }) { return <div className="report-uncertainty-card"><span className="report-uncertainty-icon"><AlertTriangle size={16} /></span><div><div className="report-record-top"><strong>{kind.replace(/_/g, " ")}</strong><StatusBadge value={status} /></div><p>{reason}</p>{reference && <small className="report-uncertainty-reference">Record ID · {reference}</small>}{supportingEvidence.length > 0 && <small className="report-uncertainty-reference">Supporting evidence IDs · {supportingEvidence.join(", ")}</small>}{conflictingEvidence.length > 0 && <small className="report-uncertainty-reference">Conflicting evidence IDs · {conflictingEvidence.join(", ")}</small>}</div></div>; }

function LegacyReport({ content }: { content: string }) {
  return <article className="report-content report-document legacy-report" aria-label="Investigation report document"><MarkdownBlocks content={content} /></article>;
}

function MarkdownBlocks({ content }: { content: string }) {
  const lines = content.split(/\r?\n/);
  const blocks: ReactNode[] = [];
  let index = 0;
  while (index < lines.length) {
    const current = lines[index].trim();
    if (!current) { index += 1; continue; }
    const heading = current.match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
      const title = <InlineMarkdown text={heading[2]} />;
      const key = `heading-${index}`;
      if (heading[1].length <= 2) blocks.push(<h2 key={key}>{title}</h2>);
      else if (heading[1].length === 3) blocks.push(<h3 key={key}>{title}</h3>);
      else blocks.push(<h4 key={key}>{title}</h4>);
      index += 1;
      continue;
    }
    if (/^[-*]\s+/.test(current)) {
      const items: ReactNode[] = [];
      while (index < lines.length && /^\s*[-*]\s+/.test(lines[index])) {
        items.push(<li key={`item-${index}`}><InlineMarkdown text={lines[index].replace(/^\s*[-*]\s+/, "")} /></li>);
        index += 1;
      }
      blocks.push(<ul key={`list-${index}`}>{items}</ul>);
      continue;
    }
    const paragraph: string[] = [];
    while (index < lines.length && lines[index].trim() && !/^(#{1,6})\s+/.test(lines[index].trim()) && !/^\s*[-*]\s+/.test(lines[index])) {
      paragraph.push(lines[index].trim());
      index += 1;
    }
    blocks.push(<p key={`paragraph-${index}`}><InlineMarkdown text={paragraph.join(" ")} /></p>);
  }
  return <div className="legacy-markdown">{blocks}</div>;
}

function InlineMarkdown({ text }: { text: string }) {
  const pieces = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return <>{pieces.map((piece, index) => piece.startsWith("**") && piece.endsWith("**")
    ? <strong key={index}>{piece.slice(2, -2)}</strong>
    : piece.startsWith("`") && piece.endsWith("`")
      ? <code key={index}>{piece.slice(1, -1)}</code>
      : <span key={index}>{piece}</span>)}</>;
}

function asRecord(value: unknown): Data { return typeof value === "object" && value !== null && !Array.isArray(value) ? value as Data : {}; }
function asRecords(value: unknown): Data[] { return Array.isArray(value) ? value.map(asRecord) : []; }
function asStrings(value: unknown): string[] { return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : []; }
function string(value: unknown, fallback: string): string { return typeof value === "string" && value.trim() ? value : fallback; }
function valueOrCount(value: unknown, fallback: unknown): number { return typeof value === "number" ? value : typeof fallback === "number" ? fallback : 0; }
function formatScore(value: unknown): string { return typeof value === "number" && Number.isFinite(value) ? `${Math.round(value)}/100` : "UNKNOWN"; }
function formatConfidence(value: unknown): string { return typeof value === "number" && Number.isFinite(value) ? `${Math.round(value <= 1 ? value * 100 : value)}%` : "UNKNOWN"; }
function formatDate(value: string): string { const date = new Date(value); return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric" }).format(date); }
function safeUrl(value: unknown): string | null { if (typeof value !== "string" || !value.trim()) return null; try { const url = new URL(value); return ["https:", "http:"].includes(url.protocol) ? url.href : null; } catch { return null; } }
