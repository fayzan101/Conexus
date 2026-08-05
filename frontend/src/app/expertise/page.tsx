"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { api, me } from "@/lib/api";

type Expert = {
  person: string;
  score: number;
  confidence: number;
  topics: string[];
  evidence: string[];
};

type Score = {
  entity_id: string;
  entity_type: string;
  freshness: number;
  trust: number;
  risk: number;
  suggested_update: string | null;
};

export default function ExpertisePage() {
  const router = useRouter();
  const [topic, setTopic] = useState("Phoenix");
  const [experts, setExperts] = useState<Expert[]>([]);
  const [scores, setScores] = useState<Score[]>([]);

  async function load(topicQuery?: string) {
    const data = await api<{ experts: Expert[] }>(
      `/v1/expertise${topicQuery ? `?topic=${encodeURIComponent(topicQuery)}` : ""}`
    );
    setExperts(data.experts);
    setScores(await api<Score[]>("/v1/freshness"));
  }

  useEffect(() => {
    (async () => {
      try {
        await me();
        await api("/v1/freshness/refresh", { method: "POST" });
        await load();
      } catch {
        router.push("/login");
      }
    })();
  }, [router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    await load(topic);
  }

  return (
    <AppShell>
      <h1 className="font-display text-3xl">Expertise & Freshness</h1>
      <p className="mt-1 text-ink-700">Discover experts and review knowledge health scores.</p>

      <form onSubmit={onSubmit} className="mt-6 flex gap-2">
        <input
          className="rounded border border-ink-900/15 bg-white px-3 py-2"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="Topic"
        />
        <button className="rounded bg-accent px-4 py-2 text-white">Find experts</button>
      </form>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <section>
          <h2 className="font-medium">Experts</h2>
          <div className="mt-3 space-y-3">
            {experts.map((ex) => (
              <article key={ex.person} className="rounded-lg border border-ink-900/10 bg-white/80 p-3 text-sm">
                <div className="flex justify-between">
                  <strong>{ex.person}</strong>
                  <span>score {ex.score} · conf {ex.confidence}</span>
                </div>
                <p className="text-ink-700">{ex.topics.join(", ")}</p>
              </article>
            ))}
            {experts.length === 0 && <p className="text-sm text-ink-700">No expertise signals yet.</p>}
          </div>
        </section>
        <section>
          <h2 className="font-medium">Knowledge risk</h2>
          <div className="mt-3 space-y-3">
            {scores.map((s) => (
              <article key={s.entity_id} className="rounded-lg border border-ink-900/10 bg-white/80 p-3 text-sm">
                <div className="flex justify-between">
                  <span>{s.entity_type}</span>
                  <span>risk {s.risk}</span>
                </div>
                <p className="text-ink-700">
                  freshness {s.freshness} · trust {s.trust}
                </p>
                {s.suggested_update && <p className="mt-1 text-xs">{s.suggested_update}</p>}
              </article>
            ))}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
