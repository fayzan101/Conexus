"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html>
      <body className="mx-auto flex min-h-screen max-w-lg flex-col justify-center px-4">
        <h1 className="font-display text-3xl">Something went wrong</h1>
        <p className="mt-2 text-ink-700">{error.message || "Unexpected error"}</p>
        <button className="mt-6 w-fit rounded bg-accent px-4 py-2 text-white" onClick={() => reset()}>
          Try again
        </button>
      </body>
    </html>
  );
}
