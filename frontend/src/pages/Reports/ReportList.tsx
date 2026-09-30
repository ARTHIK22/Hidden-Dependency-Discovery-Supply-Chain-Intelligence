import { useEffect, useState } from "react";
import { Download, FileText } from "lucide-react";
import { listInvestigations } from "../../features/investigations/investigation.api";
import { downloadReport, generateReport, listReports } from "../../features/reports/report.api";
import type { Investigation, Report } from "../../types/api.types";
import { userMessage } from "../../services/api/errors";
import "./reports.css";

export default function ReportList() {
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [investigationTotal, setInvestigationTotal] = useState(0);
  const [reportTotal, setReportTotal] = useState(0);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState("");
  const [loading, setLoading] = useState(true);
  async function load() { setLoading(true); setError(""); try { const [investigationList, reportList] = await Promise.all([listInvestigations({ limit: 100 }), listReports()]); setInvestigations(investigationList.items); setInvestigationTotal(investigationList.total); setReports(reportList.items); setReportTotal(reportList.total); } catch (reason) { setError(userMessage(reason)); } finally { setLoading(false); } }
  useEffect(() => { void load(); }, []);
  async function create(id: string) { setBusyId(id); setError(""); try { const report = await generateReport(id); setReports((current) => [report, ...current]); setReportTotal((current) => current + 1); } catch (reason) { setError(userMessage(reason)); } finally { setBusyId(""); } }
  async function download(report: Report) { try { const content = await downloadReport(report.id); const blob = new Blob([content], { type: "text/plain;charset=utf-8" }); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = `investigation-report-${report.id}.txt`; link.click(); URL.revokeObjectURL(url); } catch (reason) { setError(userMessage(reason)); } }
  return <main className="reports-page"><header><span className="eyebrow">STORED FINDINGS</span><h1>Reports</h1><p>Generate and download a text report from an investigation's saved records.</p></header>{error && <p role="alert">{error} <button type="button" onClick={() => void load()}>Retry</button></p>}
    <section className="report-investigations"><h2>Investigations ({investigationTotal})</h2>{loading ? <p aria-live="polite">Loading investigations…</p> : investigations.length === 0 ? <p>No investigations are available.</p> : investigations.map((item) => <article key={item.id}><div><FileText size={18} /><strong>{item.name}</strong><small>{item.status} · {item.goal}</small></div><button type="button" disabled={busyId === item.id} onClick={() => void create(item.id)}>{busyId === item.id ? "Generating…" : "Generate report"}</button></article>)}</section>
    <h2>Saved reports ({reportTotal})</h2>{reports.map((report) => <section className="report-view" key={report.id}><header><h2>{report.title}</h2><button type="button" onClick={() => void download(report)}><Download size={15} /> Download report</button></header><pre>{report.content}</pre></section>)}
  </main>;
}
