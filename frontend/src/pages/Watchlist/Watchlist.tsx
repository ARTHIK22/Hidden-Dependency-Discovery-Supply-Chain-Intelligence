import {
  Building2,
  ChevronRight,
  Factory,
  Globe2,
  MoreHorizontal,
  Package,
  Plus,
  Search,
  Star,
  TrendingUp,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";
import "./watchlist.css";

type WatchItem = {
  id: number;
  name: string;
  type: "Supplier" | "Material" | "Facility" | "Region";
  description: string;
  risk: "Critical" | "High" | "Medium" | "Low";
  score: number;
  change: string;
  updated: string;
};

const watchItems: WatchItem[] = [
  {
    id: 1,
    name: "Supplier B",
    type: "Supplier",
    description: "Primary battery material supplier",
    risk: "High",
    score: 78,
    change: "+8%",
    updated: "2h ago",
  },
  {
    id: 2,
    name: "Lithium",
    type: "Material",
    description: "Critical raw material dependency",
    risk: "High",
    score: 74,
    change: "+5%",
    updated: "4h ago",
  },
  {
    id: 3,
    name: "Processing Facility D",
    type: "Facility",
    description: "Upstream lithium processing facility",
    risk: "Critical",
    score: 91,
    change: "+12%",
    updated: "5h ago",
  },
  {
    id: 4,
    name: "Region A",
    type: "Region",
    description: "Geographic dependency concentration",
    risk: "Medium",
    score: 61,
    change: "+3%",
    updated: "Yesterday",
  },
];

const iconMap = {
  Supplier: Building2,
  Material: Package,
  Facility: Factory,
  Region: Globe2,
};

function Watchlist() {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("All");

  const filteredItems = useMemo(() => {
    return watchItems.filter((item) => {
      const matchesSearch =
        item.name.toLowerCase().includes(query.toLowerCase()) ||
        item.type.toLowerCase().includes(query.toLowerCase());

      const matchesFilter =
        filter === "All" || item.type === filter;

      return matchesSearch && matchesFilter;
    });
  }, [query, filter]);

  return (
    <div className="watchlist-page">
      <section className="watchlist-header">
        <div>
          <span className="watchlist-eyebrow">CONTINUOUS MONITORING</span>

          <h1>Watchlist</h1>

          <p>
            Keep important dependencies under continuous observation and quickly
            identify changes in risk.
          </p>
        </div>

        <button className="add-watch-button">
          <Plus size={17} />
          Add to Watchlist
        </button>
      </section>

      <section className="watchlist-summary">
        <div className="watch-summary-card">
          <div className="watch-summary-icon">
            <Star size={20} />
          </div>

          <div>
            <strong>{watchItems.length}</strong>
            <span>Watched Items</span>
          </div>
        </div>

        <div className="watch-summary-card">
          <div className="watch-summary-icon critical">
            <TrendingUp size={20} />
          </div>

          <div>
            <strong>3</strong>
            <span>Risk Increasing</span>
          </div>
        </div>

        <div className="watch-summary-card">
          <div className="watch-summary-icon">
            <Building2 size={20} />
          </div>

          <div>
            <strong>4</strong>
            <span>Dependencies</span>
          </div>
        </div>
      </section>

      <section className="watchlist-container">
        <div className="watchlist-toolbar">
          <div className="watch-search">
            <Search size={17} />

            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search watchlist..."
            />

            {query && (
              <button onClick={() => setQuery("")} type="button">
                <X size={15} />
              </button>
            )}
          </div>

          <div className="watch-filters">
            {["All", "Supplier", "Material", "Facility", "Region"].map(
              (item) => (
                <button
                  key={item}
                  className={filter === item ? "active" : ""}
                  onClick={() => setFilter(item)}
                  type="button"
                >
                  {item}
                </button>
              )
            )}
          </div>
        </div>

        <div className="watchlist-list">
          {filteredItems.map((item) => {
            const Icon = iconMap[item.type];

            return (
              <article className="watch-card" key={item.id}>
                <div className="watch-icon">
                  <Icon size={21} />
                </div>

                <div className="watch-main">
                  <div className="watch-title-row">
                    <div>
                      <span className="watch-type">{item.type}</span>

                      <h3>{item.name}</h3>
                    </div>

                    <button className="watch-menu" type="button">
                      <MoreHorizontal size={18} />
                    </button>
                  </div>

                  <p>{item.description}</p>

                  <div className="watch-meta">
                    <span>Updated {item.updated}</span>

                    <span className="watch-dot">•</span>

                    <span>Risk changed {item.change}</span>
                  </div>
                </div>

                <div className="watch-risk">
                  <span className={`risk-badge ${item.risk.toLowerCase()}`}>
                    {item.risk}
                  </span>

                  <div className="risk-score">
                    <strong>{item.score}</strong>
                    <span>/100</span>
                  </div>
                </div>

                <button className="watch-open" type="button">
                  <ChevronRight size={18} />
                </button>
              </article>
            );
          })}

          {filteredItems.length === 0 && (
            <div className="watch-empty">
              <Star size={26} />
              <h3>No watched items found</h3>
              <p>
                Try another search or add a new dependency to your watchlist.
              </p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

export default Watchlist;
