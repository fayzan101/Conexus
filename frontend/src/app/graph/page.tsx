"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import cytoscape from "cytoscape";
import { AppShell } from "@/components/AppShell";
import { api, me } from "@/lib/api";

type Node = { id: string; label: string; properties: Record<string, unknown> };

export default function GraphPage() {
  const router = useRouter();
  const ref = useRef<HTMLDivElement>(null);
  const [query, setQuery] = useState("Document");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    me().catch(() => router.push("/login"));
  }, [router]);

  async function load() {
    setError(null);
    try {
      const nodes = await api<Node[]>("/v1/graph/search", {
        method: "POST",
        body: JSON.stringify({ label: query || null, limit: 40 }),
      });
      if (!ref.current) return;
      const cy = cytoscape({
        container: ref.current,
        elements: nodes.map((n) => ({
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
        ],
        layout: { name: "circle" },
      });
      return () => cy.destroy();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Graph load failed");
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <AppShell>
      <h1 className="font-display text-3xl">Knowledge Graph</h1>
      <p className="mt-1 text-ink-700">Browse core entities extracted into Neo4j.</p>
      <div className="mt-4 flex gap-2">
        <input
          className="rounded border border-ink-900/15 bg-white px-3 py-2"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Label e.g. Document, Meeting, Decision"
        />
        <button onClick={load} className="rounded bg-accent px-4 py-2 text-white">
          Refresh
        </button>
      </div>
      {error && <p className="mt-3 text-red-700">{error}</p>}
      <div ref={ref} className="mt-4 h-[480px] rounded-lg border border-ink-900/10 bg-white/90" />
    </AppShell>
  );
}
