"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { api, me } from "@/lib/api";

type Slo = {
  all_ok: boolean;
  pageable: boolean;
  budgets: { search_p95_ms: number; chat_p95_ms: number; error_rate: number };
  observed: {
    search_p95_ms: number | null;
    chat_p95_ms: number | null;
    error_rate: number;
    ingest_queue_depth: number;
    acl_drop_total: number;
    grounded_ratio: number | null;
  };
  ok: { search_p95: boolean; chat_p95: boolean; error_rate: boolean };
};

type Budget = {
  tenant_id: string;
  daily_token_limit: number;
  tokens_used_today: number;
  remaining: number;
  model_route: string;
};

type Backup = {
  rpo_rto: Record<string, { cadence: string; rpo_hours: number; rto_hours: number }>;
  drills: { id: string; store: string; status: string; environment: string; performed_at: string | null }[];
};

type Profile = {
  environment: string;
  deploy_mode: string;
  modes: Record<string, { tested: boolean; environment: string | null }>;
};

export default function OpsPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [slo, setSlo] = useState<Slo | null>(null);
  const [budget, setBudget] = useState<Budget | null>(null);
  const [backup, setBackup] = useState<Backup | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [store, setStore] = useState("postgres");
  const [limit, setLimit] = useState("100000");

  async function refresh() {
    setSlo(await api<Slo>("/v1/ops/slo"));
    setBudget(await api<Budget>("/v1/ops/llm-budget"));
    setBackup(await api<Backup>("/v1/ops/backup"));
    setProfile(await api<Profile>("/v1/ops/deploy-profile"));
  }

  useEffect(() => {
    (async () => {
      try {
        const u = await me();
        if (u.role !== "admin" && u.role !== "ai_administrator") {
          setError("Admin or AI administrator role required");
          return;
        }
        await refresh();
      } catch {
        router.push("/login");
      }
    })();
  }, [router]);

  async function onDrill(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const res = await api<{ id: string; store: string }>("/v1/ops/backup-drills", {
        method: "POST",
        body: JSON.stringify({ store, environment: "staging", notes: "Recorded from ops UI" }),
      });
      setStatus(`Recorded ${res.store} restore drill ${res.id}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Drill failed");
    }
  }

  async function onQuota(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api("/v1/ops/llm-budget", {
        method: "PUT",
        body: JSON.stringify({ daily_token_limit: Number(limit) }),
      });
      setStatus("Updated LLM daily token budget");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Quota update failed");
    }
  }

  async function onChaos() {
    setError(null);
    try {
      const res = await api<{ id: string }>("/v1/ops/chaos/failover", {
        method: "POST",
        body: JSON.stringify({ component: "api", environment: "staging" }),
      });
      setStatus(`Recorded simulated failover ${res.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chaos test failed");
    }
  }

  return (
    <AppShell>
      <h1 className="font-display text-3xl">Platform ops</h1>
      <p className="mt-1 text-ink-700">SLOs, LLM cost controls, backup drills, and deploy proofs.</p>
      {error && <p className="mt-3 text-red-700">{error}</p>}
      {status && <p className="mt-3 text-accent">{status}</p>}

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Search P95 (ms)", slo?.observed.search_p95_ms, slo?.ok.search_p95],
          ["Chat P95 (ms)", slo?.observed.chat_p95_ms, slo?.ok.chat_p95],
          ["Error rate", slo?.observed.error_rate, slo?.ok.error_rate],
          ["ACL drops", slo?.observed.acl_drop_total, true],
        ].map(([label, value, ok]) => (
          <div
            key={String(label)}
            className={`rounded-lg border bg-white/80 p-4 ${ok === false ? "border-red-300" : "border-ink-900/10"}`}
          >
            <p className="text-sm text-ink-700">{label}</p>
            <p className={`mt-2 font-display text-3xl ${ok === false ? "text-red-700" : ""}`}>
              {value === null || value === undefined ? "—" : String(value)}
            </p>
          </div>
        ))}
      </div>

      <section className="mt-8 rounded-lg border border-ink-900/10 bg-white/80 p-4">
        <h2 className="font-display text-xl">LLM budget</h2>
        <p className="mt-1 text-sm text-ink-700">
          Used {budget?.tokens_used_today ?? "—"} / {budget?.daily_token_limit ?? "—"} tokens today
          {budget?.model_route ? ` · route ${budget.model_route}` : ""}
        </p>
        <form onSubmit={onQuota} className="mt-3 flex flex-wrap gap-2">
          <input
            className="rounded border border-ink-900/15 px-3 py-2"
            value={limit}
            onChange={(e) => setLimit(e.target.value)}
          />
          <button className="rounded bg-accent px-4 py-2 text-white">Set daily limit</button>
        </form>
      </section>

      <section className="mt-8 rounded-lg border border-ink-900/10 bg-white/80 p-4">
        <h2 className="font-display text-xl">Backup / restore drills</h2>
        <form onSubmit={onDrill} className="mt-3 flex flex-wrap gap-2">
          <select
            className="rounded border border-ink-900/15 px-3 py-2"
            value={store}
            onChange={(e) => setStore(e.target.value)}
          >
            <option value="postgres">postgres</option>
            <option value="neo4j">neo4j</option>
            <option value="qdrant">qdrant</option>
            <option value="object">object</option>
          </select>
          <button className="rounded bg-ink-900 px-4 py-2 text-white">Record restore drill</button>
          <button type="button" className="rounded border border-ink-900/20 px-4 py-2" onClick={onChaos}>
            Simulate API failover
          </button>
        </form>
        <ul className="mt-3 space-y-1 text-sm">
          {(backup?.drills || []).slice(0, 8).map((d) => (
            <li key={d.id}>
              {d.store} · {d.status} · {d.environment} · {d.performed_at || "—"}
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-8 rounded-lg border border-ink-900/10 bg-white/80 p-4">
        <h2 className="font-display text-xl">Deploy matrix</h2>
        <p className="mt-1 text-sm text-ink-700">
          Active: {profile?.deploy_mode} in {profile?.environment}
        </p>
        <ul className="mt-3 text-sm">
          {profile &&
            Object.entries(profile.modes).map(([mode, info]) => (
              <li key={mode}>
                {mode}: {info.tested ? "proven" : "not yet proven"}
                {info.environment ? ` (${info.environment})` : ""}
              </li>
            ))}
        </ul>
      </section>
    </AppShell>
  );
}
