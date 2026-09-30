import { useEffect, useState } from "react";
import { BarChart3, Download, FileText, ShieldAlert, Sparkles, TrendingUp } from "lucide-react";
import { useToast } from "../../components/toast/ToastProvider";
import { ErrorState, LoadingState } from "../../components/states/AsyncStates";
import { listInvestigations, getInvestigation } from "../../features/investigations/investigation.api";
import { downloadReport, generateReport, listReports } from "../../features/exports/export.api";
import type { Investigation, InvestigationDetail, Report } from "../../types/api.types";
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
    setSelectedReport((current) => current ?? reportList.items[0] ?? null);
    setSelectedInvestigationId((current) => current || investigationList.items[0]?.id || "");
  };

  useEffect(() => {
    const controller = new AbortController();
    reload(controller.signal).then(() => setError(false)).catch((cause) => { if (!controller.signal.aborted) { console.error(cause); setError(true); } }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!selectedReport) { setDetail(null); return; }
    const controller = new AbortController();
    getInvestigation(selectedReport.investigation_id, controller.signal).then(setDetail).catch((cause) => { if (!controller.signal.aborted) console.error(cause); });
    return () => controller.abort();
  }, [selectedReport]);

  const createReport = async () => {
    if (!selectedInvestigationId) return;
    setBusy(true);
    try {
      const report = await generateReport(selectedInvestigationId);
      setReports((current) => [report, ...current]);
      setSelectedReport(report);
      toast.success("Report generated from persisted investigation records.");
    } catch (cause) { toast.error(cause instanceof Error ? cause.message : "Unable to generate this report."); }
    finally { setBusy(false); }
  };

  const exportReport = async () => {
    if (!selectedReport) return;
    try {
      const content = await downloadReport(selectedReport.id);
      const url = URL.createObjectURL(new Blob([content], { type: "text/plain;charset=utf-8" }));
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `report-${selectedReport.id}.txt`;
      anchor.click();
      URL.revokeObjectURL(url);
      toast.success("Report downloaded.");
    } catch (cause) { toast.error(cause instanceof Error ? cause.message : "Unable to download this report."); }
  };

  if (loading) return <LoadingState label="Loading reports..." />;
  if (error) return <ErrorState title="Reports are unavailable" description="Check the backend and PostgreSQL connection." action={() => window.location.reload()} />;

  return <div className="reports-page">
    <div className="report-hero glass-card"><div><span className="eyebrow">INVESTIGATION REPORTS</span><h1>{selectedReport?.title || "Reports"}</h1><p>Reports summarize persisted investigation data; they do not synthesize research findings.</p></div><div className="report-controls">{selectedReport && <button className="report-export" onClick={() => void exportReport()}><Download size={16} />Export report</button>}<select aria-label="Investigation for report" value={selectedInvestigationId} onChange={(event) => setSelectedInvestigationId(event.target.value)}><option value="">Select an investigation</option>{investigations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select><button className="report-export" onClick={() => void createReport()} disabled={!selectedInvestigationId || busy}>{busy ? "Generating..." : "Generate report"}</button></div></div>
    {selectedReport ? <>
      <div className="report-metrics"><Metric icon={<FileText size={19} />} label="Entities" value={detail?.entities_count ?? "—"} /><Metric icon={<TrendingUp size={19} />} label="Relationships" value={detail?.relationships_count ?? "—"} /><Metric icon={<ShieldAlert size={19} />} label="Risk records" value={detail?.risk_count ?? "—"} /><Metric icon={<Sparkles size={19} />} label="Created" value={new Date(selectedReport.created_at).toLocaleDateString()} /></div>
      <div className="report-grid"><section className="report-card glass-card"><div className="section-title"><BarChart3 size={18} /><div><h2>Persisted report content</h2><span>Generated by the backend from saved records</span></div></div><pre className="summary-text report-content">{selectedReport.content}</pre></section><section className="report-card glass-card"><div className="section-title"><FileText size={18} /><div><h2>Investigation</h2><span>{detail?.status || "Loading saved investigation"}</span></div></div><p className="summary-text">{detail?.goal || "The associated investigation details could not be loaded."}</p><div className="report-callout"><ShieldAlert size={17} /><span>This report reflects database contents at the time it was generated.</span></div></section></div>
    </> : <div className="report-card glass-card"><div className="section-title"><FileText size={18} /><div><h2>No reports yet</h2><span>Choose a saved investigation to generate a data summary.</span></div></div>{investigations.length ? <p className="summary-text">Select an investigation above, then choose Generate report.</p> : <p className="summary-text">No investigation records are available.</p>}</div>}
    {reports.length > 1 && <div className="report-history">{reports.map((report) => <button key={report.id} className="report-export" onClick={() => setSelectedReport(report)}>{report.title} · {new Date(report.created_at).toLocaleDateString()}</button>)}</div>}
  </div>;
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) { return <div className="metric-card glass-card">{icon}<span>{label}</span><strong>{value}</strong></div>; }
