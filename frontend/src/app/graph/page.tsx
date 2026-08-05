"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import cytoscape from "cytoscape";
import { AppShell } from "@/components/AppShell";
import { api, me } from "@/lib/api";

type Node = { id: string; label: string; properties: Record<string, unknown> };
type NeighborResponse = { node: Node; neighbors: Node[] };

export default function GraphPage() {
  const router = useRouter();
  const ref = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [query, setQuery] = useState("Document");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    me().catch(() => router.push("/login"));
  }, [router]);

  async function loadNeighbors(nodeId: string, cy: cytoscape.Core) {
    try {
      const data = await api<NeighborResponse>(`/v1/graph/nodes/${encodeURIComponent(nodeId)}/neighbors`);
      const elements: cytoscape.ElementDefinition[] = [
        {
          data: {
            id: data.node.id,
            label: String(data.node.properties.title || data.node.properties.name || data.node.label),
          },
        },
      ];
      for (const n of data.neighbors) {
        if (!n.id) continue;
        elements.push({
          data: {
            id: n.id,
            label: String(n.properties.title || n.properties.name || n.label),
          },
        });
        elements.push({
          data: {
            id: `${data.node.id}-${n.id}-${String(n.properties.via || "RELATED")}`,
            source: data.node.id,
            target: n.id,
            label: String(n.properties.via || ""),
          },
        });
      }
      cy.elements().remove();
      cy.add(elements);
      cy.layout({ name: "cose", animate: false }).run();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Neighbor load failed");
    }
  }

  async function load() {
    setError(null);
    try {
      const nodes = await api<Node[]>("/v1/graph/search", {
        method: "POST",
        body: JSON.stringify({ label: query || null, limit: 40 }),
      });
      if (!ref.current) return;
      if (cyRef.current) {
        cyRef.current.destroy();
      }
      const cy = cytoscape({
        container: ref.current,
        elements: nodes
          .filter((n) => n.id)
          .map((n) => ({
            data: {
              id: n.id,
              label: String(n.properties.title || n.properties.name || n.label),
            },
          })),
        style: [
          {
            selector: "node",
            style: {
              label: "data(label)",
              "background-color": "#2f6fed",
              color: "#0b1220",
              "font-size": "10px",
              "text-wrap": "wrap",
              "text-max-width": "80px",
            },
          },
          {
            selector: "edge",
            style: {
              width: 2,
              "line-color": "#9aa7bc",
              "target-arrow-color": "#9aa7bc",
              "target-arrow-shape": "triangle",
              "curve-style": "bezier",
              label: "data(label)",
              "font-size": "8px",
              color: "#4a5568",
            },
          },
        ],
        layout: { name: "circle" },
      });
      cy.on("tap", "node", (evt) => {
        const id = evt.target.id();
        setSelectedId(id);
        void loadNeighbors(id, cy);
      });
      cyRef.current = cy;
      if (nodes[0]?.id) {
        setSelectedId(nodes[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Graph load failed");
    }
  }

  useEffect(() => {
    load();
    return () => {
      cyRef.current?.destroy();
      cyRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <AppShell>
      <h1 className="font-display text-3xl">Knowledge Graph</h1>
      <p className="mt-1 text-ink-700">
        Browse entities and tap a node to expand relationships.
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        <input
          className="rounded border border-ink-900/15 bg-white px-3 py-2"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Label e.g. Document, Meeting, Decision"
        />
        <button onClick={load} className="rounded bg-accent px-4 py-2 text-white">
          Refresh
        </button>
        {selectedId && (
          <span className="self-center text-xs text-ink-700">Selected: {selectedId}</span>
        )}
      </div>
      {error && <p className="mt-3 text-red-700">{error}</p>}
      <div ref={ref} className="mt-4 h-[480px] rounded-lg border border-ink-900/10 bg-white/90" />
    </AppShell>
  );
}
