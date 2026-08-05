"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { api, me, User } from "@/lib/api";

type Metrics = {
  documents: number;
  meetings: number;
  decisions: number;
  users: number;
  jobs_pending: number;
  jobs_failed: number;
  queries_24h: number;
};

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const u = await me();
        setUser(u);
        setMetrics(await api<Metrics>("/v1/metrics/overview"));
      } catch {
        router.push("/login");
      }
    })();
  }, [router]);

  return (
    <AppShell>
      <div className="mb-8">
        <h1 className="font-display text-3xl">Dashboard</h1>
        <p className="mt-1 text-ink-700">
          {user ? `Signed in as ${user.full_name || user.email} (${user.role})` : "Loading…"}
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Documents", metrics?.documents, false],
          ["Meetings", metrics?.meetings, false],
          ["Decisions", metrics?.decisions, false],
          ["Queries (24h)", metrics?.queries_24h, false],
          ["Users", metrics?.users, false],
          ["Jobs pending", metrics?.jobs_pending, false],
          ["Jobs failed", metrics?.jobs_failed, true],
        ].map(([label, value, alert]) => (
          <div
            key={String(label)}
            className={`rounded-lg border bg-white/80 p-4 ${
              alert && Number(value) > 0
                ? "border-red-300"
                : "border-ink-900/10"
            }`}
          >
            <p className="text-sm text-ink-700">{label}</p>
            <p
              className={`mt-2 font-display text-3xl ${
                alert && Number(value) > 0 ? "text-red-700" : ""
              }`}
            >
              {value ?? "—"}
            </p>
          </div>
        ))}
      </div>
    </AppShell>
  );
}
