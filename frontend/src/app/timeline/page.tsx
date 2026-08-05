"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { api, me } from "@/lib/api";

type Event = {
  id: string;
  event_type: string;
  title: string;
  summary: string | null;
  occurred_at: string;
  source_system: string | null;
};

export default function TimelinePage() {
  const router = useRouter();
  const [events, setEvents] = useState<Event[]>([]);

  useEffect(() => {
    (async () => {
      try {
        await me();
        setEvents(await api<Event[]>("/v1/timeline"));
      } catch {
        router.push("/login");
      }
    })();
  }, [router]);

  return (
    <AppShell>
      <h1 className="font-display text-3xl">Company Timeline</h1>
      <p className="mt-1 text-ink-700">Chronological organizational memory.</p>
      <ol className="mt-8 space-y-4 border-l border-ink-900/15 pl-6">
        {events.map((e) => (
          <li key={e.id} className="relative">
            <span className="absolute -left-[1.6rem] top-1 h-3 w-3 rounded-full bg-accent" />
            <p className="text-xs uppercase tracking-wide text-ink-700">
              {e.event_type} · {new Date(e.occurred_at).toLocaleString()}
            </p>
            <h2 className="font-medium">{e.title}</h2>
            {e.summary && <p className="text-sm text-ink-800">{e.summary}</p>}
          </li>
        ))}
        {events.length === 0 && <p className="text-sm text-ink-700">No events yet. Sync a connector or create one via API.</p>}
      </ol>
    </AppShell>
  );
}
