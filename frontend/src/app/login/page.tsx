"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("admin@enterprisebrain.local");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-lg flex-col justify-center px-4">
      <div className="mb-10">
        <p className="text-sm uppercase tracking-[0.2em] text-accent">Sign in</p>
        <h1 className="mt-2 font-display text-4xl text-ink-950">Enterprise Brain</h1>
        <p className="mt-3 text-ink-700">
          Organizational memory for evidence-backed answers.
        </p>
      </div>
      <form onSubmit={onSubmit} className="space-y-4 rounded-lg border border-ink-900/10 bg-white/80 p-6 shadow-sm">
        <label className="block text-sm">
          <span className="mb-1 block text-ink-700">Email</span>
          <input
            className="w-full rounded border border-ink-900/15 px-3 py-2"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
            required
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block text-ink-700">Password</span>
          <input
            className="w-full rounded border border-ink-900/15 px-3 py-2"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            required
          />
        </label>
        {error && <p className="text-sm text-red-700">{error}</p>}
        <button
          disabled={loading}
          className="w-full rounded bg-accent px-4 py-2.5 font-medium text-white hover:opacity-95 disabled:opacity-60"
        >
          {loading ? "Signing in…" : "Continue"}
        </button>
        <p className="text-xs text-ink-700">
          Dev users: admin@enterprisebrain.local / admin123 · user@enterprisebrain.local / user123
        </p>
      </form>
    </div>
  );
}
