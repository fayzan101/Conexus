"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { api, me } from "@/lib/api";

type Message = {
  id?: string;
  role: string;
  content: string;
  confidence?: number | null;
  sources?: Array<{ title?: string; snippet?: string; score?: number }>;
  blocked_reason?: string | null;
  acl_summary?: { blocked?: number; blocked_reasons?: string[] } | null;
};

export default function ChatPage() {
  const router = useRouter();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        await me();
        const session = await api<{ id: string }>("/v1/chat/sessions", { method: "POST" });
        setSessionId(session.id);
      } catch {
        router.push("/login");
      }
    })();
  }, [router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!sessionId || !input.trim()) return;
    const content = input.trim();
    setInput("");
    setMessages((m) => [...m, { role: "user", content }]);
    setError(null);
    try {
      const reply = await api<Message>(`/v1/chat/sessions/${sessionId}/messages`, {
        method: "POST",
        body: JSON.stringify({ content }),
      });
      setMessages((m) => [...m, reply]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat failed");
    }
  }

  return (
    <AppShell>
      <h1 className="font-display text-3xl">AI Assistant</h1>
      <p className="mt-1 text-ink-700">Evidence-backed answers with confidence and sources.</p>
      <div className="mt-6 space-y-4 rounded-lg border border-ink-900/10 bg-white/80 p-4">
        {messages.length === 0 && (
          <p className="text-sm text-ink-700">Ask about decisions, projects, or uploaded knowledge.</p>
        )}
        {messages.map((m, i) => (
          <div key={m.id || i} className={m.role === "user" ? "text-right" : ""}>
            <div
              className={`inline-block max-w-[90%] rounded-lg px-3 py-2 text-sm ${
                m.role === "user" ? "bg-accent text-white" : "bg-sand-100 text-ink-900"
              }`}
            >
              <p>{m.content}</p>
              {m.role === "assistant" && m.confidence != null && (
                <p className="mt-2 text-xs opacity-80">Confidence: {m.confidence}</p>
              )}
              {m.role === "assistant" && m.blocked_reason && (
                <p className="mt-2 text-xs text-red-800">{m.blocked_reason}</p>
              )}
            </div>
            {m.sources && m.sources.length > 0 && (
              <ul className="mt-2 space-y-1 text-left text-xs text-ink-700">
                {m.sources.map((s, idx) => (
                  <li key={idx}>
                    Source: {s.title || "Untitled"} {s.score != null ? `(${s.score.toFixed(2)})` : ""}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
      {error && <p className="mt-3 text-red-700">{error}</p>}
      <form onSubmit={onSubmit} className="mt-4 flex gap-2">
        <input
          className="flex-1 rounded border border-ink-900/15 bg-white px-3 py-2"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Why was this architecture chosen?"
        />
        <button className="rounded bg-accent px-4 py-2 text-white">Send</button>
      </form>
    </AppShell>
  );
}
