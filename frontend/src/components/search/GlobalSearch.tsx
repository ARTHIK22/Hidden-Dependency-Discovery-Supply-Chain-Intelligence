import { useEffect, useState } from "react";
import {
  Search,
  X,
  ArrowUp,
  ArrowDown,
  CornerDownLeft,
  Network,
  Building2,
  type LucideIcon,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { searchWorkspace } from "../../features/entities/entity.api";
import "./global-search.css";

type SearchType = "investigation" | "entity";

type SearchItem = {
  id: string;
  title: string;
  subtitle: string;
  type: SearchType;
  path: string;
  icon: LucideIcon;
};

const filters: { label: string; value: SearchType | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Investigations", value: "investigation" },
  { label: "Entities", value: "entity" },
];

export default function GlobalSearch() {
  const navigate = useNavigate();

  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<SearchType | "all">("all");
  const [selected, setSelected] = useState(0);
  const [results, setResults] = useState<SearchItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState(false);
  const visibleResults = filter === "all" ? results : results.filter((item) => item.type === filter);

  useEffect(() => {
    const term = query.trim();
    if (!open || term.length < 2) {
      setResults([]);
      setSearching(false);
      setSearchError(false);
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setSearching(true);
      searchWorkspace(term, controller.signal)
        .then(({ items }) => {
          setResults(items.map((item) => ({
            id: item.id,
            title: item.label,
            subtitle: item.type === "entity" ? "Entity" : "Investigation",
            type: item.type === "entity" ? "entity" : "investigation",
            path: item.path,
            icon: item.type === "entity" ? Building2 : Network,
          })));
          setSearchError(false);
          setSelected(0);
        })
        .catch((cause) => { if (!controller.signal.aborted) { console.error(cause); setSearchError(true); } })
        .finally(() => { if (!controller.signal.aborted) setSearching(false); });
    }, 180);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [open, query]);

  useEffect(() => {
    const handleKeyboard = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen(true);
      }

      if (
        event.key === "/" &&
        !["INPUT", "TEXTAREA"].includes(
          (event.target as HTMLElement)?.tagName
        )
      ) {
        event.preventDefault();
        setOpen(true);
      }

      if (!open) return;

      if (event.key === "Escape") {
        setOpen(false);
      }

      if (event.key === "ArrowDown") {
        event.preventDefault();
        setSelected((prev) =>
          visibleResults.length ? (prev + 1) % visibleResults.length : 0
        );
      }

      if (event.key === "ArrowUp") {
        event.preventDefault();
        setSelected((prev) =>
          visibleResults.length ? (prev - 1 + visibleResults.length) % visibleResults.length : 0
        );
      }

      if (event.key === "Enter" && visibleResults[selected]) {
        event.preventDefault();
        navigate(visibleResults[selected].path);
        setOpen(false);
      }
    };

    window.addEventListener("keydown", handleKeyboard);
    return () => window.removeEventListener("keydown", handleKeyboard);
  }, [open, visibleResults, selected, navigate]);

  useEffect(() => {
    if (!open) return;

    setSelected(0);

    const timer = setTimeout(() => {
      document.getElementById("global-search-input")?.focus();
    }, 50);

    return () => clearTimeout(timer);
  }, [open, filter]);

  const openSearch = () => setOpen(true);

  return (
    <>
      <button
        className="global-search-trigger"
        onClick={openSearch}
        type="button"
        aria-label="Search anything"
        aria-haspopup="dialog"
        aria-expanded={open}
      >
        <Search size={18} />
        <span>Search anything...</span>
        <kbd>Ctrl K</kbd>
      </button>

      {open && (
        <div
          className="search-overlay"
          onMouseDown={() => setOpen(false)}
          role="presentation"
        >
          <div
            className="search-modal"
            onMouseDown={(event) => event.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="Global search"
          >
            <div className="search-input-wrap">
              <Search size={21} />

              <input
                id="global-search-input"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search investigations, entities, evidence..."
                autoComplete="off"
                aria-label="Search investigations, entities, evidence, and risks"
              />

              <button
                className="search-close"
                onClick={() => setOpen(false)}
                type="button"
                aria-label="Close search"
              >
                <X size={18} />
              </button>
            </div>

            <div className="search-filters" aria-label="Filter search results">
              {filters.map((item) => (
                <button
                  key={item.value}
                  className={filter === item.value ? "active" : ""}
                  onClick={() => setFilter(item.value)}
                  type="button"
                  aria-pressed={filter === item.value}
                >
                  {item.label}
                </button>
              ))}
            </div>

            <div className="search-results">
              {searching ? (
                <div className="search-empty"><Search size={32} /><strong>Searching...</strong><span>Looking through saved entities and investigations.</span></div>
              ) : searchError ? (
                <div className="search-empty"><Search size={32} /><strong>Search is unavailable</strong><span>Check the backend connection.</span></div>
              ) : query.trim().length < 2 ? (
                <div className="search-empty"><Search size={32} /><strong>Search saved records</strong><span>Enter at least two characters.</span></div>
              ) : visibleResults.length === 0 ? (
                <div className="search-empty">
                  <Search size={32} />
                  <strong>No results found</strong>
                  <span>Try another term. Search currently covers entities and investigations.</span>
                </div>
              ) : (
                visibleResults.map((item, index) => {
                  const Icon = item.icon;

                  return (
                    <button
                      key={item.id}
                      className={`search-result ${
                        selected === index ? "selected" : ""
                      }`}
                      onMouseEnter={() => setSelected(index)}
                      onClick={() => {
                        navigate(item.path);
                        setOpen(false);
                      }}
                      type="button"
                    >
                      <div className="result-icon">
                        <Icon size={18} />
                      </div>

                      <div className="result-content">
                        <strong>{item.title}</strong>
                        <span>{item.subtitle}</span>
                      </div>

                      {selected === index && (
                        <CornerDownLeft size={16} className="result-enter" />
                      )}
                    </button>
                  );
                })
              )}
            </div>

            <div className="search-footer">
              <span>
                <ArrowUp size={14} />
                <ArrowDown size={14} />
                Navigate
              </span>

              <span>
                <CornerDownLeft size={14} />
                Open
              </span>

              <span>
                <kbd>ESC</kbd>
                Close
              </span>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
