"use client";

import { Suspense } from "react";
import ConnectorsInner from "./ConnectorsInner";

export default function ConnectorsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-ink-600">Loading connectors…</div>}>
      <ConnectorsInner />
    </Suspense>
  );
}
