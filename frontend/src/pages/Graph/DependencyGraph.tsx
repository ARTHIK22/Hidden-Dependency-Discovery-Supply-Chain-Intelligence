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
  ShieldCheck,
  X,
  type LucideIcon,
} from "lucide-react";
import "./graph.css";
import { getDependencyGraph } from "../../features/relationships/relationship.api";
import { ErrorState, LoadingState } from "../../components/states/AsyncStates";
import type { GraphNode } from "../../types/api.types";

type EntityType = string;

type EntityNodeData = Record<string, unknown> & {
  label: string;
  type: EntityType;
  risk: number;
  status: string;
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
  const riskClass =
    data.risk >= 85
      ? "critical"
      : data.risk >= 70
        ? "high"
        : data.risk >= 50
          ? "medium"
          : "low";

  return (
    <div className={`graph-node ${riskClass}`}>
      <Handle type="target" position={Position.Left} />
      <div className="graph-node-icon"><Icon size={17} /></div>
      <div className="graph-node-content">
        <strong>{data.label}</strong>
        <span>{data.status}</span>
      </div>
      <div className="graph-node-risk">{data.risk}</div>
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
  const [search, setSearch] = useState("");
  const [riskOnly, setRiskOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    getDependencyGraph(controller.signal)
      .then((graph) => {
        setNodes(graph.nodes.map((node: GraphNode) => ({ ...node, type: "entity", data: { ...node.data, type: normalizeEntityType(node.data.type) } })));
        setEdges(graph.edges as Edge[]);
        setLoadError(false);
      })
      .catch((cause) => { if (!controller.signal.aborted) { console.error(cause); setLoadError(true); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [setNodes, setEdges]);
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

  const filteredNodes = useMemo(() => {
    const query = search.toLowerCase();
    return nodes
      .filter((node) => {
        const matchesSearch = node.data.label.toLowerCase().includes(query);
        const matchesRisk = !riskOnly || node.data.risk >= 70;
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
  }, [nodes, search, riskOnly, selectedId, connectedNodeIds]);

  const selectedNode = nodes.find((node) => node.id === selectedId);
  const selectedRelationship = edges.find((edge) => edge.source === selectedId || edge.target === selectedId);
  const verificationStatus = (selectedRelationship?.data as { verificationStatus?: string } | undefined)?.verificationStatus;
  const visibleNodeIds = new Set(filteredNodes.map((node) => node.id));
  const visibleEdges = edges
    .filter(
      (edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target),
    )
    .map((edge) => {
      const isConnected = edge.source === selectedId || edge.target === selectedId;
      return {
        ...edge,
        animated: isConnected,
        style: {
          stroke: isConnected ? "var(--clay-dark)" : "var(--clay-light)",
          strokeWidth: isConnected ? 2.8 : 1.7,
        },
      };
    });

  const handleNodeClick = (_event: MouseEvent, node: Node<EntityNodeData>) => {
    setSelectedId(node.id);
  };

  return (
    <div className="graph-page">
      <div className="graph-header">
        <div>
          <span className="eyebrow">INTELLIGENCE GRAPH</span>
          <h1>Dependency Graph</h1>
          <p>Explore hidden relationships and upstream dependencies.</p>
        </div>
        <div className="graph-header-stats">
          <div><strong>{nodes.length}</strong><span>Entities</span></div>
          <div><strong>{edges.length}</strong><span>Relationships</span></div>
          <div><strong>{nodes.filter((node) => node.data.risk >= 70).length}</strong><span>High Risk</span></div>
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
        <button
          className={`graph-filter ${riskOnly ? "active" : ""}`}
          onClick={() => setRiskOnly((value) => !value)}
        >
          <Filter size={15} />
          High Risk
        </button>
      </div>

      <div className="graph-workspace">
        <ReactFlow
          nodes={filteredNodes}
          edges={visibleEdges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
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
              const risk = Number((node.data as EntityNodeData | undefined)?.risk ?? 0);
              if (risk >= 85) return "#b56f68";
              if (risk >= 70) return "#c39b55";
              if (risk >= 50) return "#a97858";
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
            <span className="eyebrow">ENTITY</span>
            <h2>{selectedNode.data.label}</h2>
            <div
              className={`inspector-risk ${
                selectedNode.data.risk >= 85
                  ? "critical"
                  : selectedNode.data.risk >= 70
                    ? "high"
                    : "normal"
              }`}
            >
              <div>
                <span>Risk Score</span>
                <strong>{selectedNode.data.risk}/100</strong>
              </div>
              <AlertTriangle size={18} />
            </div>
            <div className="inspector-section">
              <span>Status</span>
              <strong>{selectedNode.data.status}</strong>
            </div>
            <div className="inspector-section">
              <span>Entity Type</span>
              <strong>{selectedNode.data.type}</strong>
            </div>
            <div className="inspector-section">
              <span>Verification</span>
              <strong className="verified"><ShieldCheck size={15} />{verificationStatus || "No evidence status recorded"}</strong>
            </div>
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
      </div>
    </div>
  );
}

function normalizeEntityType(type: string): EntityType {
  return type.toLowerCase();
}
