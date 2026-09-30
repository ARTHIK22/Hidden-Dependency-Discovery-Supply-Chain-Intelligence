import { useEffect, useState } from "react";
import { Download, FileText } from "lucide-react";
import { listInvestigations } from "../../features/investigations/investigation.api";
import { generateReport } from "../../features/reports/report.api";
import type { Investigation } from "../../types/investigation.types";
import { userMessage } from "../../services/api/errors";
import "./reports.css";

export default function ReportList() {
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [reports, setReports] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState("");
  const [loading, setLoading] = useState(true);
  async function load() { setLoading(true); setError(""); try { setInvestigations(await listInvestigations({ limit: 100 })); } catch (reason) { setError(userMessage(reason)); } finally { setLoading(false); } }
  useEffect(() => { void load(); }, []);
  async function create(id: string) { setBusyId(id); setError(""); try { const report = await generateReport(id); setReports((current) => [report, ...current]); } catch (reason) { setError(userMessage(reason)); } finally { setBusyId(""); } }
  function download(report: Record<string, unknown>) { const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = `investigation-report-${String(report.id || "report")}.json`; link.click(); URL.revokeObjectURL(url); }
  return <main className="reports-page"><header><span className="eyebrow">STORED FINDINGS</span><h1>Reports</h1><p>Generate a JSON summary from an investigation's saved records.</p></header>{error && <p role="alert">{error} <button type="button" onClick={() => { setError(""); listInvestigations({ limit: 100 }).then(setInvestigations).catch((reason) => setError(userMessage(reason))); }}>Retry investigation list</button></p>}
    <section className="report-investigations"><h2>Investigations</h2>{loading ? <p aria-live="polite">Loading investigations…</p> : investigations.length === 0 ? <p>No investigations are available.</p> : investigations.map((item) => <article key={item.id}><div><FileText size={18} /><strong>{item.name}</strong><small>{item.status} · {item.target || "No target"}</small></div><button type="button" disabled={busyId === item.id} onClick={() => void create(item.id)}>{busyId === item.id ? "Generating…" : "Generate report"}</button></article>)}</section>
    {reports.map((report, index) => <section className="report-view" key={String(report.id || index)}><header><h2>{String((report.investigation as Record<string, unknown> | undefined)?.name || "Investigation report")}</h2><button type="button" onClick={() => download(report)}><Download size={15} /> Download JSON</button></header><pre>{JSON.stringify(report, null, 2)}</pre></section>)}
  </main>;
}
