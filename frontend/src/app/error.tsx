"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mx-auto max-w-lg px-4 py-16">
      <h1 className="font-display text-3xl">Page error</h1>
      <p className="mt-2 text-ink-700">{error.message || "This page failed to load."}</p>
      <button className="mt-6 rounded bg-accent px-4 py-2 text-white" onClick={() => reset()}>
        Retry
      </button>
    </div>
  );
}
