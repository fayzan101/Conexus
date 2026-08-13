"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { logout } from "@/lib/api";

const links = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/executive", label: "Executive" },
  { href: "/search", label: "Search" },
  { href: "/chat", label: "Assistant" },
  { href: "/upload", label: "Ingest" },
  { href: "/connectors", label: "Connectors" },
  { href: "/timeline", label: "Timeline" },
  { href: "/expertise", label: "Expertise" },
  { href: "/graph", label: "Graph" },
  { href: "/decisions", label: "Decisions" },
  { href: "/admin", label: "Admin" },
  { href: "/ops", label: "Ops" },
  { href: "/ga", label: "GA" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <div className="min-h-screen">
      <header className="border-b border-ink-900/10 bg-white/70 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <Link href="/dashboard" className="font-display text-xl tracking-tight text-ink-950">
            Enterprise Brain
          </Link>
          <nav className="flex flex-wrap items-center gap-1 text-sm">
            {links.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={`rounded px-2.5 py-1.5 transition ${
                  pathname === l.href
                    ? "bg-accent text-white"
                    : "text-ink-800 hover:bg-accent-soft"
                }`}
              >
                {l.label}
              </Link>
            ))}
            <button
              className="ml-2 rounded px-2.5 py-1.5 text-ink-700 hover:bg-sand-100"
              onClick={() => {
                logout();
                router.push("/login");
              }}
            >
              Sign out
            </button>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
    </div>
  );
}
