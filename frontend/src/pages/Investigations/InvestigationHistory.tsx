import { useEffect, useMemo, useState } from "react";
import { ArrowRight, CheckCircle2, Clock3, Search, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { listInvestigations } from "../../features/investigations/investigation.api";
import { ErrorState, LoadingState } from "../../components/states/AsyncStates";
import type { Investigation } from "../../types/api.types";
import "./investigation-history.css";

export default function InvestigationHistory() {
  const navigate = useNavigate();
  const [items, setItems] = useState<Investigation[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    listInvestigations(undefined, controller.signal)
      .then(({ items: data }) => { setItems(data); setError(false); })
      .catch((cause) => { if (!controller.signal.aborted) { console.error(cause); setError(true); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);

  const filtered = useMemo(() => items.filter((item) =>
    `${item.name} ${item.goal}`.toLowerCase().includes(query.toLowerCase())
  ), [items, query]);

  return (
    <div className="history-page">
      <div className="history-heading">
        <div><span className="eyebrow">INVESTIGATION WORKSPACE</span><h1>Investigation History</h1><p>Review requests saved in the backend queue.</p></div>
        <button className="history-new" onClick={() => navigate("/investigations/new")}><Sparkles size={15} />New investigation</button>
      </div>
      <div className="history-search glass-card"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search investigations..." /></div>
      {loading ? <LoadingState label="Loading investigations..." /> : error ? <ErrorState title="Investigations are unavailable" description="Check the backend and PostgreSQL connection." action={() => window.location.reload()} /> : (
        <div className="history-list">
          {filtered.map((item) => {
            const isCompleted = item.status.toLowerCase() === "completed";
            return <button className="history-row glass-card" key={item.id} onClick={() => navigate(`/investigations/${item.id}`)}>
              <div className="history-icon">{isCompleted ? <CheckCircle2 size={18} /> : <Clock3 size={18} />}</div>
              <div><span className="history-id">{item.id.slice(0, 8).toUpperCase()}</span><h3>{item.name}</h3><p>{new Date(item.created_at).toLocaleString()} · {item.status} · {item.progress}% complete</p></div>
              <span className={`history-status ${isCompleted ? "done" : "review"}`}>{item.status}</span><ArrowRight size={16} />
            </button>;
          })}
          {!filtered.length && <div className="history-row glass-card">{items.length ? "No investigations match this search." : "No investigations have been saved yet."}</div>}
        </div>
      )}
    </div>
  );
}
