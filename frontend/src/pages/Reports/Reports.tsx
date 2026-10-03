import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Download, FileText, ShieldAlert, Sparkles, TrendingUp } from "lucide-react";
import { useToast } from "../../components/toast/ToastProvider";
import { ErrorState, LoadingState } from "../../components/states/AsyncStates";
import { listInvestigations, getInvestigation } from "../../features/investigations/investigation.api";
import { downloadReport, generateReport, listReports } from "../../features/exports/export.api";
import type { Investigation, InvestigationDetail, Report } from "../../types/api.types";
import ReportDocument from "./ReportDocument";
import "./reports.css";

export default function Reports() {
  const { toast } = useToast();
  const [reports, setReports] = useState<Report[]>([]);
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [selectedInvestigationId, setSelectedInvestigationId] = useState("");
  const [detail, setDetail] = useState<InvestigationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);

  const reload = async (signal?: AbortSignal) => {
    const [reportList, investigationList] = await Promise.all([
      listReports(undefined, signal),
      listInvestigations(undefined, signal),
    ]);
    setReports(reportList.items);
    setInvestigations(investigationList.items);
    setSelectedInvestigationId((current) => current || investigationList.items[0]?.id || "");
  };

  useEffect(() => {
    const controller = new AbortController();
    reload(controller.signal)
      .then(() => setError(false))
      .catch((cause) => { if (!controller.signal.aborted) { console.error(cause); setError(true); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!selectedReport) { setDetail(null); return; }
    const controller = new AbortController();
    getInvestigation(selectedReport.investigation_id, controller.signal)
      .then(setDetail)
      .catch((cause) => { if (!controller.signal.aborted) console.error(cause); });
    return () => controller.abort();
  }, [selectedReport]);

  const createReport = async () => {
    if (!selectedInvestigationId) return;
    setBusy(true);
    try {
      const report = await generateReport(selectedInvestigationId);
      setReports((current) => [report, ...current.filter((item) => item.id !== report.id)]);
      setSelectedReport(report);
      toast.success("Report generated from persisted investigation records.");
    } catch (cause) { toast.error(cause instanceof Error ? cause.message : "Unable to generate this report."); }
    finally { setBusy(false); }
  };

  const exportReport = async (format: "json" | "csv" | "txt" = "txt") => {
    if (!selectedReport) return;
    try {
      const content = await downloadReport(selectedReport.id, format);
      const url = URL.createObjectURL(content);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `report-${selectedReport.id}.${format}`;
      anchor.click();
      URL.revokeObjectURL(url);
      toast.success(`${format.toUpperCase()} report downloaded.`);
    } catch (cause) { toast.error(cause instanceof Error ? cause.message : "Unable to download this report."); }
  };

  if (loading) return <LoadingState label="Loading reports..." />;
  if (error) return <ErrorState title="Reports are unavailable" description="Check the backend and PostgreSQL connection." action={() => window.location.reload()} />;

  const reportInvestigation = selectedReport ? objectValue(selectedReport.structured_content?.investigation) : {};
  const entityCount = arrayValue(selectedReport?.structured_content?.entities).length;
  const relationshipCount = arrayValue(selectedReport?.structured_content?.relationships).length;

  return <div className="reports-page">
    <section className={`report-hero glass-card${selectedReport ? " report-hero-detail" : ""}`} aria-labelledby="report-title">
      <div className="report-heading">
        {selectedReport && <button className="report-back" type="button" onClick={() => { setSelectedReport(null); setDetail(null); }}><ArrowLeft size={16} /> Back to reports</button>}
        <span className="eyebrow">INVESTIGATION REPORTS</span>
        <h1 id="report-title">{selectedReport ? stringValue(reportInvestigation.name, cleanReportTitle(selectedReport.title)) : "Reports"}</h1>
        <p>Reports summarize persisted investigation data; they do not synthesize research findings.</p>
      </div>
      <div className="report-controls" aria-label="Report actions">
        {selectedReport && <div className="report-export-actions" aria-label="Export report">
          <button className="report-export" onClick={() => void exportReport("txt")}><Download size={16} />Export report</button>
          <button className="report-export report-format-export" onClick={() => void exportReport("json")}>JSON</button>
          <button className="report-export report-format-export" onClick={() => void exportReport("csv")}>CSV</button>
        </div>}
        <div className="report-generation-controls">
          <label htmlFor="report-investigation">Generate from investigation</label>
          <select id="report-investigation" aria-label="Investigation for report" value={selectedInvestigationId} onChange={(event) => setSelectedInvestigationId(event.target.value)}>
            <option value="">Select an investigation</option>
            {investigations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
          <button className="report-export report-generate-button" onClick={() => void createReport()} disabled={!selectedInvestigationId || busy}>{busy ? "Generating..." : "Generate report"}</button>
        </div>
      </div>
    </section>

    {selectedReport ? <>
      <div className="report-metrics">
        <Metric icon={<FileText size={19} />} label="Entities" value={detail?.entities_count ?? (selectedReport.structured_content ? entityCount : "—")} />
        <Metric icon={<TrendingUp size={19} />} label="Relationships" value={detail?.relationships_count ?? (selectedReport.structured_content ? relationshipCount : "—")} />
        <Metric icon={<ShieldAlert size={19} />} label="Evidence records" value={detail?.evidence_count ?? arrayValue(selectedReport.structured_content?.evidence).length} />
        <Metric icon={<Sparkles size={19} />} label="Generated" value={formatDate(selectedReport.created_at)} />
      </div>
      <ReportDocument report={selectedReport} />
    </> : <section className="saved-reports" aria-labelledby="saved-reports-heading">
      <header className="saved-reports-heading"><div><span className="eyebrow">SAVED RECORDS</span><h2 id="saved-reports-heading">Saved reports</h2></div><span className="saved-report-count">{reports.length} {reports.length === 1 ? "report" : "reports"}</span></header>
      {reports.length ? <div className="saved-report-list">{reports.map((report) => {
        const investigation = objectValue(report.structured_content?.investigation);
        const title = stringValue(investigation.name, cleanReportTitle(report.title));
        const goal = stringValue(investigation.goal, "No investigation goal was saved with this report.");
        return <article className="saved-report-card glass-card" key={report.id}>
          <div className="saved-report-icon"><FileText size={19} /></div>
          <div className="saved-report-copy"><span className="saved-report-kind">INVESTIGATION REPORT</span><h3>{title}</h3><p>{goal}</p><div className="saved-report-meta"><span className="saved-report-status"><i />Generated</span><span>{formatDate(report.created_at)}</span>{report.structured_content?.demo_only === true && <span className="report-demo-pill">DEMO ONLY</span>}</div></div>
          <button className="saved-report-open" type="button" onClick={() => setSelectedReport(report)}>Open Report <ArrowRight size={16} /></button>
        </article>;
      })}</div> : <div className="report-empty glass-card"><div className="saved-report-icon"><FileText size={19} /></div><div><h3>No reports yet</h3><p>Choose a saved investigation above, then generate a report from its persisted records.</p></div></div>}
      {!reports.length && !investigations.length && <p className="report-empty-note">No investigation records are available.</p>}
    </section>}
  </div>;
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) { return <div className="metric-card glass-card">{icon}<span>{label}</span><strong>{value}</strong></div>; }
function objectValue(value: unknown): Record<string, unknown> { return typeof value === "object" && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : {}; }
function arrayValue(value: unknown): unknown[] { return Array.isArray(value) ? value : []; }
function stringValue(value: unknown, fallback: string): string { return typeof value === "string" && value.trim() ? value : fallback; }
function cleanReportTitle(value: string): string { return value.replace(/\s*—\s*Investigation Report\s*$/i, "") || value; }
function formatDate(value: string): string { const date = new Date(value); return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric" }).format(date); }
