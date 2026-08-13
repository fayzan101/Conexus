"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { api, me } from "@/lib/api";

type BoardPack = {
  audience: string;
  kpis: { key: string; name: string; value: number | null; target: number | null; on_target: boolean | null }[];
};

type Ready = {
  ga_version: string;
  ready: boolean;
  compliance_ready: boolean;
  eval_gates_green: boolean;
};

export default function GaPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [pack, setPack] = useState<BoardPack | null>(null);
  const [ready, setReady] = useState<Ready | null>(null);
  const [publicStatus, setPublicStatus] = useState<{ overall: string; version: string } | null>(null);
  const [problem, setProblem] = useState("Why is knowledge freshness dropping?");

  async function refresh() {
    setPack(await api<BoardPack>("/v1/executive/board-pack"));
    setReady(await api<Ready>("/v1/ga/readiness"));
    setPublicStatus(await api<{ overall: string; version: string }>("/v1/status"));
  }

  useEffect(() => {
    (async () => {
      try {
        const u = await me();
        if (u.role !== "admin" && u.role !== "manager" && u.role !== "ai_administrator") {
          setError("Manager/admin role required for GA console");
          return;
        }
        await refresh();
      } catch {
        router.push("/login");
      }
    })();
  }, [router]);

  async function runAgent(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const res = await api<{ id: string; status: string }>("/v1/agents/run", {
        method: "POST",
        body: JSON.stringify({ problem, tools: ["search", "draft_doc"] }),
      });
      setStatus(`Agent run ${res.id} → ${res.status}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Agent failed");
    }
  }

  async function runEvals() {
    setError(null);
    try {
      const res = await api<{ all_passed: boolean }>("/v1/evals/run", {
        method: "POST",
        body: JSON.stringify({ recall_at_5: 0.8, citation_rate: 0.95 }),
      });
      setStatus(`Eval gates ${res.all_passed ? "green" : "red"}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eval failed");
    }
  }

  return (
    <AppShell>
      <h1 className="font-display text-3xl">GA maturity</h1>
      <p className="mt-1 text-ink-700">Board pack, agent HITL, eval gates, and readiness for v{ready?.ga_version || "1.0.0"}.</p>
      {error && <p className="mt-3 text-red-700">{error}</p>}
      {status && <p className="mt-3 text-accent">{status}</p>}

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Public status", publicStatus?.overall],
          ["GA ready", ready?.ready ? "yes" : "no"],
          ["Compliance", ready?.compliance_ready ? "yes" : "no"],
          ["Eval gates", ready?.eval_gates_green ? "green" : "red"],
        ].map(([label, value]) => (
          <div key={String(label)} className="rounded-lg border border-ink-900/10 bg-white/80 p-4">
            <p className="text-sm text-ink-700">{label}</p>
            <p className="mt-2 font-display text-2xl">{value ?? "—"}</p>
          </div>
        ))}
      </div>

      <section className="mt-8 rounded-lg border border-ink-900/10 bg-white/80 p-4">
        <h2 className="font-display text-xl">Board pack KPIs</h2>
        <ul className="mt-3 space-y-1 text-sm">
          {(pack?.kpis || []).map((k) => (
            <li key={k.key}>
              {k.name}: {k.value ?? "—"}
              {k.target != null ? ` (target ${k.target})` : ""}
              {k.on_target === false ? " · off target" : ""}
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-8 rounded-lg border border-ink-900/10 bg-white/80 p-4">
        <h2 className="font-display text-xl">Research agent</h2>
        <form onSubmit={runAgent} className="mt-3 flex flex-wrap gap-2">
          <input
            className="min-w-[16rem] flex-1 rounded border border-ink-900/15 px-3 py-2"
            value={problem}
            onChange={(e) => setProblem(e.target.value)}
          />
          <button className="rounded bg-accent px-4 py-2 text-white">Run agent</button>
          <button type="button" className="rounded border border-ink-900/20 px-4 py-2" onClick={runEvals}>
            Run eval gates
          </button>
        </form>
      </section>
    </AppShell>
  );
}
