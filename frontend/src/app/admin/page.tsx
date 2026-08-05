"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { api, me, User } from "@/lib/api";

export default function AdminPage() {
  const router = useRouter();
  const [users, setUsers] = useState<User[]>([]);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("changeme");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setUsers(await api<User[]>("/v1/users"));
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

  return (
    <AppShell>
      <h1 className="font-display text-3xl">Admin</h1>
      <p className="mt-1 text-ink-700">User management for the tenant.</p>
      {error && <p className="mt-3 text-red-700">{error}</p>}

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
        <button className="rounded bg-accent px-4 py-2 text-white sm:col-span-3 sm:w-fit">Invite user</button>
      </form>

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
