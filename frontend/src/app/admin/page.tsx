"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { api, me, User } from "@/lib/api";

type Job = {
  id: string;
  job_type: string;
  status: string;
  error: string | null;
  attempts: number;
  dead_lettered: boolean;
  updated_at: string;
};

export default function AdminPage() {
  const router = useRouter();
  const [users, setUsers] = useState<User[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("changeme");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  async function refresh() {
    setUsers(await api<User[]>("/v1/users"));
    try {
      setJobs(await api<Job[]>("/v1/jobs/failed"));
    } catch {
      setJobs([]);
    }
  }

  useEffect(() => {
    (async () => {
      try {
        const u = await me();
        if (u.role !== "admin") {
          setError("Admin role required");
          return;
        }
        await refresh();
      } catch {
        router.push("/login");
      }
    })();
  }, [router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api("/v1/users", {
        method: "POST",
        body: JSON.stringify({
          email,
          password,
          full_name: fullName || null,
          role: "employee",
        }),
      });
      setEmail("");
      setFullName("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  async function onInvite(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setStatus(null);
    try {
      const res = await api<{ accept_url: string; token: string }>("/v1/auth/invites", {
        method: "POST",
        body: JSON.stringify({ email, role: "employee" }),
      });
      setStatus(`Invite created: ${res.accept_url}`);
      setEmail("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invite failed");
    }
  }

  async function retryJob(id: string) {
    setError(null);
    try {
      await api(`/v1/jobs/${id}/retry`, { method: "POST" });
      setStatus(`Retried job ${id}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Retry failed");
    }
  }

  return (
    <AppShell>
      <h1 className="font-display text-3xl">Admin</h1>
      <p className="mt-1 text-ink-700">Users, invites, and failed ingest jobs (DLQ).</p>
      {error && <p className="mt-3 text-red-700">{error}</p>}
      {status && <p className="mt-3 text-accent">{status}</p>}

      <form onSubmit={onSubmit} className="mt-6 grid gap-3 rounded-lg border border-ink-900/10 bg-white/80 p-4 sm:grid-cols-3">
        <input
          className="rounded border border-ink-900/15 px-3 py-2"
          placeholder="Full name"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
        />
        <input
          className="rounded border border-ink-900/15 px-3 py-2"
          placeholder="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          className="rounded border border-ink-900/15 px-3 py-2"
          placeholder="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <button className="rounded bg-accent px-4 py-2 text-white sm:col-span-2 sm:w-fit">Create user</button>
        <button type="button" onClick={onInvite} className="rounded border border-ink-900/20 px-4 py-2 sm:w-fit">
          Send invite link
        </button>
      </form>

      <section className="mt-8">
        <h2 className="font-display text-xl">Failed ingest jobs</h2>
        {jobs.length === 0 ? (
          <p className="mt-2 text-ink-600">No failed or dead-lettered jobs.</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {jobs.map((j) => (
              <li key={j.id} className="flex flex-wrap items-center justify-between gap-2 rounded border border-ink-900/10 bg-white/80 px-3 py-2 text-sm">
                <span>
                  {j.job_type} · {j.status} · attempts {j.attempts}
                  {j.error && <span className="text-red-700"> — {j.error}</span>}
                </span>
                <button type="button" className="rounded bg-ink-900 px-3 py-1 text-white" onClick={() => retryJob(j.id)}>
                  Retry
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="mt-6 overflow-x-auto rounded-lg border border-ink-900/10 bg-white/80">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-ink-900/10 text-ink-700">
            <tr>
              <th className="px-3 py-2">Name</th>
              <th className="px-3 py-2">Email</th>
              <th className="px-3 py-2">Role</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b border-ink-900/5">
                <td className="px-3 py-2">{u.full_name || "—"}</td>
                <td className="px-3 py-2">{u.email}</td>
                <td className="px-3 py-2">{u.role}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AppShell>
  );
}
