"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { api, me } from "@/lib/api";

type Decision = {
  id: string;
  title: string;
  status: string;
  context?: string | null;
  evidence?: string | null;
};

export default function DecisionsPage() {
  const router = useRouter();
  const [items, setItems] = useState<Decision[]>([]);
  const [title, setTitle] = useState("");
  const [context, setContext] = useState("");

  async function refresh() {
    setItems(await api<Decision[]>("/v1/decisions"));
  }

  useEffect(() => {
    (async () => {
      try {
        await me();
        await refresh();
      } catch {
        router.push("/login");
      }
    })();
  }, [router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    await api("/v1/decisions", {
      method: "POST",
      body: JSON.stringify({ title, context, status: "proposed" }),
    });
    setTitle("");
    setContext("");
    await refresh();
  }

  return (
    <AppShell>
      <h1 className="font-display text-3xl">Decision Intelligence</h1>
      <p className="mt-1 text-ink-700">Record and review organizational decisions.</p>

      <form onSubmit={onSubmit} className="mt-6 space-y-3 rounded-lg border border-ink-900/10 bg-white/80 p-4">
        <input
          className="w-full rounded border border-ink-900/15 px-3 py-2"
          placeholder="Decision title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <textarea
          className="min-h-24 w-full rounded border border-ink-900/15 px-3 py-2"
          placeholder="Context"
          value={context}
          onChange={(e) => setContext(e.target.value)}
        />
        <button className="rounded bg-accent px-4 py-2 text-white">Create decision</button>
      </form>

      <div className="mt-6 space-y-3">
        {items.map((d) => (
          <article key={d.id} className="rounded-lg border border-ink-900/10 bg-white/80 p-4">
            <div className="flex justify-between gap-3">
              <h2 className="font-medium">{d.title}</h2>
              <span className="text-xs uppercase tracking-wide text-ink-700">{d.status}</span>
            </div>
            {d.context && <p className="mt-2 text-sm text-ink-800">{d.context}</p>}
            {d.evidence && <p className="mt-1 text-xs text-ink-700">Evidence: {d.evidence}</p>}
          </article>
        ))}
      </div>
    </AppShell>
  );
}
