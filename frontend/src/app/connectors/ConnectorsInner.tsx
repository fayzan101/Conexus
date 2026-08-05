"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { api, me } from "@/lib/api";

type Account = {
  id: string;
  provider: string;
  display_name: string | null;
  status: string;
  last_sync_at: string | null;
  last_error: string | null;
  health_ok: boolean | null;
  health_detail: string | null;
};

type HealthRow = {
  account_id: string;
  provider: string;
  ok: boolean;
  detail: string;
  lag_seconds: number | null;
  status: string;
  last_sync_at: string | null;
  last_error: string | null;
};

export default function ConnectorsInner() {
  const router = useRouter();
  const params = useSearchParams();
  const [providers, setProviders] = useState<string[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [health, setHealth] = useState<HealthRow[]>([]);
  const [provider, setProvider] = useState("slack");
  const [token, setToken] = useState("xoxb-demo");
  const [fixture, setFixture] = useState(
    '[{"ts":"1710000000.1","channel":"eng","text":"Project Phoenix sync","user":"U1"}]',
  );
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    const list = await api<{ providers: string[] }>("/v1/connectors");
    setProviders(list.providers);
    setAccounts(await api<Account[]>("/v1/connectors/accounts"));
    try {
      setHealth(await api<HealthRow[]>("/v1/connectors/health"));
    } catch {
      setHealth([]);
    }
  }

  useEffect(() => {
    (async () => {
      try {
        await me();
        await refresh();
        const connected = params.get("connected");
        if (connected) setStatus(`OAuth connected: ${connected}`);
      } catch {
        router.push("/login");
      }
    })();
  }, [router, params]);

  async function onConnect(e: FormEvent) {
    e.preventDefault();
    setStatus(null);
    setError(null);
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
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  async function startOAuth(p: "slack" | "github") {
    setError(null);
    try {
      const res = await api<{ authorize_url: string }>(`/v1/connectors/${p}/oauth/start`);
      window.location.href = res.authorize_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "OAuth start failed");
    }
  }

  return (
    <AppShell>
      <h1 className="font-display text-3xl">Connectors</h1>
      <p className="mt-1 text-ink-700">Pilot hardening: OAuth for Slack/GitHub, health, fixture fallback.</p>
      {error && <p className="mt-3 text-red-700">{error}</p>}
      {status && <p className="mt-3 text-accent">{status}</p>}

      <section className="mt-6">
        <h2 className="font-display text-xl">Connector health</h2>
        {health.length === 0 ? (
          <p className="mt-2 text-ink-600">No connector accounts yet. Connect Slack or GitHub to see health.</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {health.map((h) => (
              <li key={h.account_id} className="rounded border border-ink-900/10 bg-white/80 px-3 py-2 text-sm">
                <span className={h.ok ? "text-green-800" : "text-red-700"}>{h.ok ? "OK" : "DOWN"}</span>
                {" · "}
                {h.provider} — {h.detail || h.status}
                {h.lag_seconds != null && ` · lag ${Math.round(h.lag_seconds)}s`}
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="mt-6 flex flex-wrap gap-2">
        <button
          type="button"
          className="rounded bg-accent px-3 py-2 text-sm text-white"
          onClick={() => startOAuth("slack")}
        >
          Connect Slack (OAuth)
        </button>
        <button
          type="button"
          className="rounded bg-ink-900 px-3 py-2 text-sm text-white"
          onClick={() => startOAuth("github")}
        >
          Connect GitHub (OAuth)
        </button>
      </div>

      <form onSubmit={onConnect} className="mt-6 space-y-3 rounded-lg border border-ink-900/10 bg-white/80 p-4">
        <p className="text-sm text-ink-600">Fixture / token mode (local pilots without OAuth apps)</p>
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
          placeholder="access token"
        />
        <textarea
          className="h-28 w-full rounded border border-ink-900/15 px-3 py-2 font-mono text-xs"
          value={fixture}
          onChange={(e) => setFixture(e.target.value)}
        />
        <button type="submit" className="rounded bg-accent px-4 py-2 text-white">
          Connect & sync
        </button>
      </form>

      <section className="mt-8">
        <h2 className="font-display text-xl">Accounts</h2>
        {accounts.length === 0 ? (
          <p className="mt-2 text-ink-600">No accounts connected.</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {accounts.map((a) => (
              <li key={a.id} className="rounded border border-ink-900/10 bg-white/70 px-3 py-2 text-sm">
                {a.provider} · {a.display_name || a.id} · {a.status}
                {a.last_error && <span className="text-red-700"> — {a.last_error}</span>}
              </li>
            ))}
          </ul>
        )}
      </section>
    </AppShell>
  );
}
