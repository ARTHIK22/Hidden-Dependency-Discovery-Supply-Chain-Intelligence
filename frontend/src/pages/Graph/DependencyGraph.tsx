import {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useEffect, useMemo, useState, type MouseEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  Building2,
  ExternalLink,
  Factory,
  Filter,
  MapPin,
  Network,
  Package,
  Search,
  X,
  type LucideIcon,
} from "lucide-react";
import "./graph.css";
import { getDependencyGraph } from "../../features/relationships/relationship.api";
import { ErrorState, LoadingState } from "../../components/states/AsyncStates";
import type { GraphNode, RiskFactor } from "../../types/api.types";

type EntityType = string;

type EntityNodeData = Record<string, unknown> & {
  label: string;
  type: EntityType;
  risk: number | null;
  status: string;
  riskStatus?: string;
  riskReason?: string | null;
  riskFactors?: RiskFactor[];
  propagatedRisk?: number | null;
  demoOnly?: boolean;
  aliases?: string[];
  resolutionStatus?: string | null;
  resolutionConfidence?: number | null;
  evidenceCount?: number;
};

const entityIcons: Record<string, LucideIcon> = {
  company: Building2,
  supplier: Building2,
  manufacturer: Factory,
  material: Package,
  facility: Factory,
  region: MapPin,
};

function EntityNode({ data }: { data: EntityNodeData }) {
  const Icon = entityIcons[data.type] ?? Building2;
  const riskClass = data.risk === null
    ? "unknown"
    : data.risk >= 75
      ? "critical"
      : data.risk >= 50
        ? "high"
        : data.risk >= 25
          ? "medium"
          : "low";

  return (
    <div className={`graph-node ${riskClass}`}>
      <Handle type="target" position={Position.Left} />
      <div className="graph-node-icon"><Icon size={17} /></div>
      <div className="graph-node-content">
        <strong>{data.label}</strong>
        <span>{data.status}</span>
        {data.demoOnly && <em>DEMO DATA</em>}
      </div>
      <div className="graph-node-risk">{data.risk === null ? "UNKNOWN" : Math.round(data.risk)}</div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

const nodeTypes = { entity: EntityNode };

export default function DependencyGraph() {
  const navigate = useNavigate();
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<EntityNodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [graphFilter, setGraphFilter] = useState<"All" | "High Risk" | "Critical" | "Verified" | "Conflicted" | "Unknown">("All");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [hasMoreEntities, setHasMoreEntities] = useState(false);
  const [hasMoreRelationships, setHasMoreRelationships] = useState(false);
  const [graphLimit, setGraphLimit] = useState(500);
  const [graphOffset, setGraphOffset] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    getDependencyGraph(controller.signal, graphLimit, graphOffset)
      .then((graph) => {
        setNodes(graph.nodes.map((node: GraphNode) => ({ ...node, type: "entity", data: { ...node.data, type: normalizeEntityType(node.data.type) } })));
        setEdges(graph.edges as Edge[]);
        setHasMoreEntities(Boolean(graph.has_more_entities));
        setHasMoreRelationships(Boolean(graph.has_more_relationships));
        setGraphLimit(graph.limit ?? 500);
        setLoadError(false);
      })
      .catch((cause) => { if (!controller.signal.aborted) { console.error(cause); setLoadError(true); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [graphLimit, graphOffset, setNodes, setEdges]);
  const connectedNodeIds = useMemo(() => {
    const connected = new Set<string>();

    if (selectedId) {
      edges.forEach((edge) => {
        if (edge.source === selectedId) connected.add(edge.target);
        if (edge.target === selectedId) connected.add(edge.source);
      });
    }

    return connected;
  }, [edges, selectedId]);
  const relationshipNodes = useMemo(() => {
    const verified = new Set<string>();
    const conflicted = new Set<string>();
    for (const edge of edges) {
      const status = String((edge.data as { verificationStatus?: string } | undefined)?.verificationStatus ?? "").toUpperCase();
      if (status === "VERIFIED") { verified.add(edge.source); verified.add(edge.target); }
      if (status === "CONFLICTED" || status === "REJECTED") { conflicted.add(edge.source); conflicted.add(edge.target); }
    }
    return { verified, conflicted };
  }, [edges]);

  const filteredNodes = useMemo(() => {
    const query = search.toLowerCase();
    return nodes
      .filter((node) => {
        const matchesSearch = node.data.label.toLowerCase().includes(query);
        const score = node.data.risk;
        const matchesRisk = graphFilter === "All"
          || (graphFilter === "High Risk" && score !== null && score >= 50)
          || (graphFilter === "Critical" && score !== null && score >= 75)
          || (graphFilter === "Verified" && relationshipNodes.verified.has(node.id))
          || (graphFilter === "Conflicted" && relationshipNodes.conflicted.has(node.id))
          || (graphFilter === "Unknown" && (score === null || node.data.riskStatus === "UNKNOWN"));
        return matchesSearch && matchesRisk;
      })
      .map((node) => ({
        ...node,
        style: {
          opacity:
            selectedId &&
            node.id !== selectedId &&
            !connectedNodeIds.has(node.id)
              ? 0.28
              : 1,
          transition: "opacity 180ms ease",
        },
      }));
  }, [nodes, search, graphFilter, selectedId, connectedNodeIds, relationshipNodes]);

  const selectedNode = nodes.find((node) => node.id === selectedId);
  const includesDemoData = nodes.some((node) => node.data.demoOnly)
    || edges.some((edge) => Boolean((edge.data as { demoOnly?: boolean } | undefined)?.demoOnly));
  const selectedRelationship = edges.find((edge) => edge.id === selectedEdgeId)
    ?? (selectedId ? edges.find((edge) => edge.source === selectedId || edge.target === selectedId) : undefined);
  const visibleNodeIds = new Set(filteredNodes.map((node) => node.id));
  const visibleEdges = edges
    .filter(
      (edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target),
    )
    .map((edge) => {
      const isConnected = edge.source === selectedId || edge.target === selectedId;
      const status = String((edge.data as { verificationStatus?: string } | undefined)?.verificationStatus ?? "").toUpperCase();
      const stroke = status === "VERIFIED" ? "#758d68"
        : status === "SUPPORTED" ? "#bc9856"
          : status === "CONFLICTED" || status === "REJECTED" ? "#b56f68"
            : "#a9aa9f";
      return {
        ...edge,
        animated: isConnected,
        style: {
          stroke: isConnected ? "var(--clay-dark)" : stroke,
          strokeWidth: isConnected ? 2.8 : status === "VERIFIED" ? 2.3 : 1.7,
          strokeDasharray: ["INSUFFICIENT_EVIDENCE", "PENDING"].includes(status) ? "5 5" : undefined,
        },
      };
    });

  const handleNodeClick = (_event: MouseEvent, node: Node<EntityNodeData>) => {
    setSelectedId(node.id);
    setSelectedEdgeId(null);
  };

  return (
    <div className="graph-page">
      <div className="graph-header">
        <div>
          <span className="eyebrow">INTELLIGENCE GRAPH</span>
          <h1>Dependency Graph</h1>
          <p>Explore hidden relationships and upstream dependencies.</p>
          {includesDemoData && <p className="graph-demo-notice">DEMO DATA — fictional development fixtures are included in this graph.</p>}
          {(hasMoreEntities || hasMoreRelationships) && <p className="graph-limit-notice">This graph page is bounded to {graphLimit} entities and {graphLimit * 2} relationships. Evidence previews show up to three recent records per relationship.</p>}
        </div>
        <div className="graph-header-stats">
          <div><strong>{nodes.length}</strong><span>Entities</span></div>
          <div><strong>{edges.length}</strong><span>Relationships</span></div>
          <div><strong>{nodes.filter((node) => node.data.risk !== null && node.data.risk >= 50).length}</strong><span>High Risk</span></div>
        </div>
      </div>

      <div className="graph-toolbar">
        <div className="graph-search">
          <Search size={17} />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search entities..."
          />
          {search && (
            <button aria-label="Clear search" onClick={() => setSearch("")}>
              <X size={14} />
            </button>
          )}
        </div>
        <div className="graph-filter-list" aria-label="Graph filters">{(["All", "High Risk", "Critical", "Verified", "Conflicted", "Unknown"] as const).map((filter) => <button key={filter} className={`graph-filter ${graphFilter === filter ? "active" : ""}`} onClick={() => setGraphFilter(filter)} type="button">{filter === "All" && <Filter size={15} />}{filter}</button>)}</div>
      </div>
      <div className="graph-status-legend" aria-label="Relationship verification statuses">
        <span><i className="verified" />Verified</span><span><i className="supported" />Supported</span>
        <span><i className="conflicted" />Conflicted / rejected</span><span><i className="insufficient" />Insufficient evidence</span>
      </div>
      {(graphOffset > 0 || hasMoreEntities) && <div className="graph-page-controls" role="group" aria-label="Dependency graph pages">
        <span>Entity page {Math.floor(graphOffset / graphLimit) + 1}</span>
        <button type="button" disabled={graphOffset === 0} onClick={() => setGraphOffset(Math.max(0, graphOffset - graphLimit))}>Previous page</button>
        <button type="button" disabled={!hasMoreEntities} onClick={() => setGraphOffset(graphOffset + graphLimit)}>Next page</button>
      </div>}

      <div className="graph-workspace">
        <ReactFlow
          nodes={filteredNodes}
          edges={visibleEdges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          onEdgeClick={(_event, edge) => { setSelectedEdgeId(edge.id); setSelectedId(null); }}
          nodeTypes={nodeTypes}
          fitView
          minZoom={0.3}
          maxZoom={1.8}
          proOptions={{ hideAttribution: true }}
        >
          <Background gap={24} size={1} />
          <Controls />
          <MiniMap
            nodeColor={(node) => {
              const risk = (node.data as EntityNodeData | undefined)?.risk;
              if (risk === null || risk === undefined) return "#a9aa9f";
              if (risk >= 75) return "#b56f68";
              if (risk >= 50) return "#c39b55";
              if (risk >= 25) return "#a97858";
              return "#758d68";
            }}
          />
        </ReactFlow>

        {loading && <div className="graph-data-overlay"><LoadingState label="Loading dependency graph..." /></div>}
        {!loading && loadError && <div className="graph-data-overlay"><ErrorState title="Dependency graph is unavailable" description="Check the backend and PostgreSQL connection." action={() => window.location.reload()} /></div>}
        {!loading && !loadError && nodes.length === 0 && <div className="graph-data-overlay"><div className="empty-state glass-card"><Network size={24} /><h3>No dependency records yet</h3><p>The graph will display entities and relationships once they are persisted.</p></div></div>}

        {selectedNode && (
          <aside className="graph-inspector">
            <button className="inspector-close" aria-label="Close entity details" onClick={() => setSelectedId(null)}>
              <X size={17} />
            </button>
            <div className="inspector-icon">
              {(() => {
                const Icon = entityIcons[selectedNode.data.type] ?? Building2;
                return <Icon size={21} />;
              })()}
            </div>
            <span className="eyebrow">{(selectedNode.data as EntityNodeData).demoOnly ? "DEMO ENTITY" : "ENTITY"}</span>
            <h2>{selectedNode.data.label}</h2>
            <div
              className={`inspector-risk ${
                selectedNode.data.risk !== null && selectedNode.data.risk >= 75
                  ? "critical"
                  : selectedNode.data.risk !== null && selectedNode.data.risk >= 50
                    ? "high"
                    : "normal"
              }`}
            >
              <div>
                <span>Risk Score</span>
                <strong>{selectedNode.data.risk === null ? "UNKNOWN" : `${Math.round(selectedNode.data.risk)}/100`}</strong>
              </div>
              <AlertTriangle size={18} />
            </div>
            {(selectedNode.data as EntityNodeData).riskReason && <p className="graph-resolution-note">{(selectedNode.data as EntityNodeData).riskReason}</p>}
            {(selectedNode.data as EntityNodeData).riskFactors?.map((factor) => <div className="inspector-section" key={factor.key}><span>{factor.label}</span><strong>{factor.status === "UNKNOWN" || factor.score === null ? "UNKNOWN" : `${factor.score}/100`}</strong><small>{factor.explanation}</small></div>)}
            <div className="inspector-section">
              <span>Status</span>
              <strong>{selectedNode.data.status}</strong>
            </div>
            <div className="inspector-section">
              <span>Entity Type</span>
              <strong>{selectedNode.data.type}</strong>
            </div>
            <div className="inspector-section"><span>Resolution status</span><strong>{String((selectedNode.data as EntityNodeData).resolutionStatus ?? "Unresolved").replace(/_/g, " ")}</strong></div>
            <div className="inspector-section"><span>Resolution confidence</span><strong>{(selectedNode.data as EntityNodeData).resolutionConfidence == null ? "Not scored" : `${Math.round(Number((selectedNode.data as EntityNodeData).resolutionConfidence) * 100)}%`}</strong></div>
            <div className="inspector-section"><span>Evidence records</span><strong>{Number((selectedNode.data as EntityNodeData).evidenceCount ?? 0)}</strong></div>
            <div className="inspector-section"><span>Aliases</span><strong>{((selectedNode.data as EntityNodeData).aliases ?? []).join(", ") || "No recorded aliases"}</strong></div>
            {["UNRESOLVED", "POSSIBLE_DUPLICATE"].includes(String((selectedNode.data as EntityNodeData).resolutionStatus ?? "UNRESOLVED").toUpperCase()) && <p className="graph-resolution-note">Entity identity could not be confidently resolved.</p>}
            <div className="inspector-section"><span>Related entities</span><strong>{[...connectedNodeIds].map((id) => nodes.find((node) => node.id === id)?.data.label).filter(Boolean).join(", ") || "No connected entities"}</strong></div>
            <div className="inspector-section"><span>Relationships</span><strong>{edges.filter((edge) => edge.source === selectedNode.id || edge.target === selectedNode.id).length}</strong></div>
            <div className="inspector-actions">
              <button onClick={() => navigate("/evidence")}>
                <ExternalLink size={15} />
                View Evidence
              </button>
              <button
                onClick={() => {
                  const nodeId = selectedNode?.id;

                  if (!nodeId) return;

                  const connected = edges.filter(
                    (edge) => edge.source === nodeId || edge.target === nodeId,
                  );

                  console.log("Connected dependencies:", connected);
                }}
              >
                Explore Dependencies
              </button>
            </div>
          </aside>
        )}
        {!selectedNode && selectedRelationship && <RelationshipInspector edge={selectedRelationship} nodes={nodes} onClose={() => setSelectedEdgeId(null)} />}
      </div>
    </div>
  );
}

function RelationshipInspector({ edge, nodes, onClose }: { edge: Edge; nodes: Node<EntityNodeData>[]; onClose: () => void }) {
  const data = (edge.data ?? {}) as {
    relationshipType?: string; verificationStatus?: string; confidence?: number | null;
    evidenceCount?: number; evidenceTruncated?: boolean; sources?: string[]; verifiedAt?: string | null;
    riskScore?: number | null; riskLevel?: string | null; riskReason?: string | null; riskFactors?: RiskFactor[];
    supportingEvidenceCount?: number; conflictingEvidenceCount?: number; explanation?: string;
    evidenceItems?: Array<{ id: string; source: string; sourceType: string; url: string | null; title: string; excerpt: string; capturedAt: string | null; publishedDate: string | null; verificationStatus: string }>;
    verification?: { explanation?: string };
  };
  const source = nodes.find((node) => node.id === edge.source)?.data.label ?? "Unknown entity";
  const target = nodes.find((node) => node.id === edge.target)?.data.label ?? "Unknown entity";
  const status = data.verificationStatus ?? "PENDING";
  return <aside className="graph-inspector relationship-inspector">
    <button className="inspector-close" aria-label="Close relationship details" onClick={onClose}><X size={17} /></button>
    <span className="eyebrow">RELATIONSHIP</span>
    <h2>{data.relationshipType ?? String(edge.label ?? "Dependency")}</h2>
    <div className="inspector-section"><span>From</span><strong>{source}</strong></div>
    <div className="inspector-section"><span>To</span><strong>{target}</strong></div>
    <div className="inspector-section"><span>Verification status</span><strong>{status.replace(/_/g, " ")}</strong></div>
    <div className="inspector-section"><span>Confidence</span><strong>{data.confidence == null ? "Not scored" : `${Math.round(data.confidence * 100)}%`}</strong></div>
    <div className="inspector-section"><span>Evidence records</span><strong>{data.evidenceCount ?? data.evidenceItems?.length ?? 0}</strong></div>
    <div className="inspector-section"><span>Sources</span><strong>{data.sources?.join(", ") || "No source recorded"}</strong></div>
    <div className="inspector-section"><span>Last verification</span><strong>{data.verifiedAt ? new Date(data.verifiedAt).toLocaleString() : "Not verified"}</strong></div>
    <div className="inspector-section"><span>Relationship risk</span><strong>{data.riskScore == null ? "UNKNOWN" : `${Math.round(data.riskScore)}/100 · ${data.riskLevel ?? "UNRATED"}`}</strong></div>
    {data.riskReason && <p className="graph-resolution-note">{data.riskReason}</p>}
    {(data.riskFactors ?? []).map((factor) => <div className="inspector-section" key={factor.key}><span>{factor.label}</span><strong>{factor.status === "UNKNOWN" || factor.score === null ? "UNKNOWN" : `${factor.score}/100`}</strong><small>{factor.explanation}</small></div>)}
    {data.verification?.explanation && <p className="graph-resolution-note">{data.verification.explanation}</p>}
    {Boolean(data.conflictingEvidenceCount) && <p className="graph-conflict-note">{data.conflictingEvidenceCount} conflicting item(s) preserved alongside {data.supportingEvidenceCount ?? 0} supporting item(s).</p>}
    {data.evidenceTruncated && <p className="graph-resolution-note">Showing the three most recent linked evidence records for this relationship.</p>}
    <div className="graph-evidence-list">{(data.evidenceItems ?? []).map((item) => <article key={item.id} className={`graph-evidence-item ${item.verificationStatus}`}>
      <strong>{item.title || item.source}</strong><span>{item.source} · {item.verificationStatus.replace(/_/g, " ")}</span>
      <p>{item.excerpt}</p>{item.url && <a href={item.url} target="_blank" rel="noreferrer">Open source <ExternalLink size={12} /></a>}
      <small>{item.publishedDate ?? item.capturedAt ?? "Source date unavailable"}</small>
    </article>)}</div>
  </aside>;
}

function normalizeEntityType(type: string): EntityType {
  return type.toLowerCase();
}
