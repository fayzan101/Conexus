"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { api, me } from "@/lib/api";

type KPIs = {
  knowledge_health: number;
  decision_count: number;
  document_count: number;
  prediction_count: number;
  high_risk_predictions: number;
  workflow_automation_candidates: number;
  open_opportunities: number;
  open_recommendations: number;
};

type Prediction = { id: string; title: string; probability: number; severity: string };
type Recommendation = { id: string; title: string; action: string; priority: string };
type Report = { id: string; problem: string; executive_summary: string | null };

export default function ExecutivePage() {
  const router = useRouter();
  const [kpis, setKpis] = useState<KPIs | null>(null);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  async function refresh() {
    setKpis(await api<KPIs>("/v1/executive/dashboard"));
    setPredictions(await api<Prediction[]>("/v1/predictions"));
    setRecs(await api<Recommendation[]>("/v1/recommendations"));
  }

  useEffect(() => {
    (async () => {
      try {
        await me();
        await api("/v1/predictions/run", { method: "POST" });
        await api("/v1/workflows/detect", { method: "POST" });
        await api("/v1/opportunities/discover", { method: "POST" });
        await api("/v1/recommendations/generate", { method: "POST" });
        await refresh();
      } catch {
        router.push("/login");
      }
    })();
  }, [router]);

  async function runResearch() {
    setStatus("Running research agent…");
    try {
      const res = await api<Report>("/v1/research/run", {
        method: "POST",
        body: JSON.stringify({ problem: "What are the top organizational risks right now?" }),
      });
      setReport(res);
      setStatus("Research complete");
      await refresh();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Failed");
    }
  }

  return (
    <AppShell>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl">Executive OS</h1>
          <p className="mt-1 text-ink-700">Phase 3 operating-system KPIs, risks, and agents.</p>
        </div>
        <button onClick={runResearch} className="rounded bg-accent px-4 py-2 text-white">
          Run research agent
        </button>
      </div>
      {status && <p className="mb-4 text-sm text-ink-700">{status}</p>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Knowledge health", kpis?.knowledge_health],
          ["Decisions", kpis?.decision_count],
          ["High-risk predictions", kpis?.high_risk_predictions],
          ["Automation candidates", kpis?.workflow_automation_candidates],
          ["Open opportunities", kpis?.open_opportunities],
          ["Recommendations", kpis?.open_recommendations],
          ["Predictions", kpis?.prediction_count],
          ["Documents", kpis?.document_count],
        ].map(([label, value]) => (
          <div key={String(label)} className="rounded-lg border border-ink-900/10 bg-white/80 p-4">
            <p className="text-sm text-ink-700">{label}</p>
            <p className="mt-2 font-display text-3xl">{value ?? "—"}</p>
          </div>
        ))}
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <section>
          <h2 className="font-medium">Predictions</h2>
          <div className="mt-3 space-y-2">
            {predictions.slice(0, 6).map((p) => (
              <article key={p.id} className="rounded border border-ink-900/10 bg-white/80 p-3 text-sm">
                <div className="flex justify-between gap-2">
                  <span>{p.title}</span>
                  <span className="text-ink-700">
                    {p.severity} · {p.probability}
                  </span>
                </div>
              </article>
            ))}
          </div>
        </section>
        <section>
          <h2 className="font-medium">Recommendations</h2>
          <div className="mt-3 space-y-2">
            {recs.slice(0, 6).map((r) => (
              <article key={r.id} className="rounded border border-ink-900/10 bg-white/80 p-3 text-sm">
                <strong>{r.title}</strong>
                <p className="text-ink-700">{r.action}</p>
              </article>
            ))}
          </div>
        </section>
      </div>

      {report && (
        <section className="mt-8 rounded-lg border border-ink-900/10 bg-white/80 p-4">
          <h2 className="font-medium">Latest research report</h2>
          <p className="mt-2 text-sm text-ink-800">{report.executive_summary}</p>
        </section>
      )}
    </AppShell>
  );
}
