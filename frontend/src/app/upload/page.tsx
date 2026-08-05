"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { api, me } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export default function UploadPage() {
  const router = useRouter();
  const [status, setStatus] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [transcriptTitle, setTranscriptTitle] = useState("");
  const [transcript, setTranscript] = useState("");

  useEffect(() => {
    me().catch(() => router.push("/login"));
  }, [router]);

  async function uploadFile(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fileInput = form.elements.namedItem("file") as HTMLInputElement;
    if (!fileInput.files?.[0]) return;
    const body = new FormData();
    body.append("file", fileInput.files[0]);
    if (title) body.append("title", title);
    const token = localStorage.getItem("eb_token");
    const res = await fetch(`${API_BASE}/v1/documents`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body,
    });
    if (!res.ok) {
      setStatus(await res.text());
      return;
    }
    const data = await res.json();
    setStatus(`Document ingested. Job: ${data.job_id} (${data.document.id})`);
    form.reset();
    setTitle("");
  }

  async function uploadTranscript(e: FormEvent) {
    e.preventDefault();
    try {
      const data = await api<{ job_id: string; meeting: { id: string } }>("/v1/meetings/transcripts", {
        method: "POST",
        body: JSON.stringify({ title: transcriptTitle, transcript }),
      });
      setStatus(`Meeting ingested. Job: ${data.job_id} (${data.meeting.id})`);
      setTranscriptTitle("");
      setTranscript("");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Failed");
    }
  }

  return (
    <AppShell>
      <h1 className="font-display text-3xl">Ingest</h1>
      <p className="mt-1 text-ink-700">Upload documents and meeting transcripts.</p>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <form onSubmit={uploadFile} className="space-y-3 rounded-lg border border-ink-900/10 bg-white/80 p-4">
          <h2 className="font-medium">Document upload</h2>
          <input
            className="w-full rounded border border-ink-900/15 px-3 py-2"
            placeholder="Title (optional)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <input name="file" type="file" required className="block w-full text-sm" />
          <button className="rounded bg-accent px-4 py-2 text-white">Upload</button>
        </form>

        <form onSubmit={uploadTranscript} className="space-y-3 rounded-lg border border-ink-900/10 bg-white/80 p-4">
          <h2 className="font-medium">Meeting transcript</h2>
          <input
            className="w-full rounded border border-ink-900/15 px-3 py-2"
            placeholder="Meeting title"
            value={transcriptTitle}
            onChange={(e) => setTranscriptTitle(e.target.value)}
            required
          />
          <textarea
            className="min-h-40 w-full rounded border border-ink-900/15 px-3 py-2"
            placeholder="Paste transcript… Include Decision: and Action item: lines for extraction."
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            required
          />
          <button className="rounded bg-accent px-4 py-2 text-white">Ingest transcript</button>
        </form>
      </div>
      {status && <p className="mt-4 text-sm text-ink-800">{status}</p>}
    </AppShell>
  );
}
