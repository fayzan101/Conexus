"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { api, me } from "@/lib/api";

type Account = {
  id: string;
  provider: string;
  display_name: string | null;
  status: string;
  last_sync_at: string | null;
};

export default function ConnectorsPage() {
  const router = useRouter();
  const [providers, setProviders] = useState<string[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [provider, setProvider] = useState("slack");
  const [token, setToken] = useState("xoxb-demo");
  const [fixture, setFixture] = useState('[{"ts":"1710000000.1","channel":"eng","text":"Project Phoenix sync","user":"U1"}]');
  const [status, setStatus] = useState<string | null>(null);

  async function refresh() {
    const list = await api<{ providers: string[] }>("/v1/connectors");
    setProviders(list.providers);
    setAccounts(await api<Account[]>("/v1/connectors/accounts"));
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

  async function onConnect(e: FormEvent) {
    e.preventDefault();
    setStatus(null);
    try {
      const messages = JSON.parse(fixture);
      const account = await api<Account>(`/v1/connectors/${provider}/connect`, {
        method: "POST",
        body: JSON.stringify({
          display_name: `${provider} pilot`,
          credentials: { access_token: token, messages, items: messages, issues: messages, files: messages },
        }),
      });
      const sync = await api<{ stored: number }>(`/v1/connectors/accounts/${account.id}/sync`, {
        method: "POST",
      });
      setStatus(`Connected ${provider}; synced ${sync.stored} artifact(s)`);
      await refresh();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Failed");
    }
  }

  return (
    <AppShell>
      <h1 className="font-display text-3xl">Connectors</h1>
      <p className="mt-1 text-ink-700">Phase 2 sync adapters (fixture/token mode for pilots).</p>

      <form onSubmit={onConnect} className="mt-6 space-y-3 rounded-lg border border-ink-900/10 bg-white/80 p-4">
        <select
          className="w-full rounded border border-ink-900/15 px-3 py-2"
          value={provider}
          onChange={(e) => setProvider(e.target.value)}
        >
          {providers.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <input
          className="w-full rounded border border-ink-900/15 px-3 py-2"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          placeholder="Access token"
        />
        <textarea
          className="min-h-28 w-full rounded border border-ink-900/15 px-3 py-2 font-mono text-xs"
          value={fixture}
          onChange={(e) => setFixture(e.target.value)}
        />
        <button className="rounded bg-accent px-4 py-2 text-white">Connect & sync</button>
      </form>
      {status && <p className="mt-3 text-sm text-ink-800">{status}</p>}

      <div className="mt-6 space-y-2">
        {accounts.map((a) => (
          <div key={a.id} className="rounded border border-ink-900/10 bg-white/80 px-3 py-2 text-sm">
            <strong>{a.provider}</strong> · {a.display_name} · {a.status}
          </div>
        ))}
      </div>
    </AppShell>
  );
}
