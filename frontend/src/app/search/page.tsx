"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { api, me } from "@/lib/api";

type Hit = {
  id: string;
  score: number;
  snippet: string;
  source: { title?: string; type?: string; retrieval?: string };
};

export default function SearchPage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<"semantic" | "hybrid">("hybrid");
  const [results, setResults] = useState<Hit[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    me().catch(() => router.push("/login"));
  }, [router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const data = await api<{ results: Hit[] }>("/v1/search", {
        method: "POST",
        body: JSON.stringify({ query, limit: 10, mode }),
      });
      setResults(data.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    }
  }

  return (
    <AppShell>
      <h1 className="font-display text-3xl">Enterprise Search</h1>
      <p className="mt-1 text-ink-700">Semantic or hybrid retrieval with citations.</p>
      <form onSubmit={onSubmit} className="mt-6 flex flex-wrap gap-2">
        <input
          className="min-w-[16rem] flex-1 rounded border border-ink-900/15 bg-white px-3 py-2"
          placeholder="Who approved Project Phoenix?"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select
          className="rounded border border-ink-900/15 bg-white px-3 py-2"
          value={mode}
          onChange={(e) => setMode(e.target.value as "semantic" | "hybrid")}
        >
          <option value="hybrid">Hybrid</option>
          <option value="semantic">Semantic</option>
        </select>
        <button className="rounded bg-accent px-4 py-2 text-white">Search</button>
      </form>
      {error && <p className="mt-3 text-red-700">{error}</p>}
      <div className="mt-6 space-y-3">
        {results.map((r) => (
          <article key={r.id} className="rounded-lg border border-ink-900/10 bg-white/80 p-4">
            <div className="flex items-baseline justify-between gap-3">
              <h2 className="font-medium">{r.source.title || "Untitled"}</h2>
              <span className="text-xs text-ink-700">
                {r.source.type}
                {r.source.retrieval ? ` · ${r.source.retrieval}` : ""} · {r.score.toFixed(3)}
              </span>
            </div>
            <p className="mt-2 text-sm text-ink-800">{r.snippet}</p>
          </article>
        ))}
      </div>
    </AppShell>
  );
}
