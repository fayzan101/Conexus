"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type Status = {
  product: string;
  version: string;
  overall: string;
  components: { name: string; status: string }[];
  updated_at: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export default function StatusPage() {
  const [data, setData] = useState<Status | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/v1/status`);
        if (!res.ok) throw new Error(await res.text());
        setData(await res.json());
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load status");
      }
    })();
  }, []);

  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      <p className="text-sm text-ink-600">
        <Link href="/login" className="text-accent">
          Sign in
        </Link>
      </p>
      <h1 className="mt-4 font-display text-4xl">System status</h1>
      {error && <p className="mt-4 text-red-700">{error}</p>}
      {data && (
        <>
          <p className="mt-2 text-ink-700">
            {data.product} v{data.version} · {data.overall}
          </p>
          <p className="text-sm text-ink-500">Updated {data.updated_at}</p>
          <ul className="mt-8 space-y-3">
            {data.components.map((c) => (
              <li key={c.name} className="flex items-center justify-between rounded border border-ink-900/10 bg-white/80 px-4 py-3">
                <span>{c.name}</span>
                <span className={c.status === "operational" ? "text-accent" : "text-red-700"}>{c.status}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </main>
  );
}
