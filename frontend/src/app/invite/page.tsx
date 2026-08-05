"use client";

import { FormEvent, Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

function InviteForm() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token") || "";
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const data = await api<{ access_token: string; refresh_token?: string }>("/v1/auth/invites/accept", {
        method: "POST",
        body: JSON.stringify({ token, password, full_name: fullName || null }),
      });
      localStorage.setItem("eb_token", data.access_token);
      if (data.refresh_token) localStorage.setItem("eb_refresh", data.refresh_token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invite accept failed");
    }
  }

  if (!token) {
    return (
      <div className="mx-auto max-w-lg px-4 py-16">
        <h1 className="font-display text-3xl">Invalid invite</h1>
        <p className="mt-2 text-ink-600">Missing invite token in the URL.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-lg flex-col justify-center px-4">
      <h1 className="font-display text-3xl">Accept invite</h1>
      <p className="mt-2 text-ink-700">Set your password to join Enterprise Brain.</p>
      {error && <p className="mt-3 text-red-700">{error}</p>}
      <form onSubmit={onSubmit} className="mt-6 space-y-3 rounded-lg border border-ink-900/10 bg-white/80 p-4">
        <input
          className="w-full rounded border border-ink-900/15 px-3 py-2"
          placeholder="Full name"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
        />
        <input
          className="w-full rounded border border-ink-900/15 px-3 py-2"
          type="password"
          placeholder="Password (min 8)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          minLength={8}
          required
        />
        <button className="rounded bg-accent px-4 py-2 text-white">Join</button>
      </form>
    </div>
  );
}

export default function InvitePage() {
  return (
    <Suspense fallback={<div className="p-8 text-ink-600">Loading invite…</div>}>
      <InviteForm />
    </Suspense>
  );
}
