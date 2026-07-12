"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  ClipboardList,
  CreditCard,
  FolderLock,
  GaugeCircle,
  LayoutDashboard,
  Menu,
  MessagesSquare,
  Users,
  X,
} from "lucide-react";
import { useState } from "react";
import { Wordmark } from "@/components/brand";
import { ThemeToggle } from "@/components/theme-toggle";
import { cn } from "@/lib/utils";
import { isAuthConfigured } from "@/lib/supabase";

const NAV = [
  { href: "/workspace", label: "Workspace", icon: MessagesSquare },
  { href: "/rooms", label: "Data Rooms", icon: FolderLock },
  { href: "/dashboard", label: "Ticker Dashboard", icon: LayoutDashboard },
  { href: "/audit", label: "Audit Log", icon: ClipboardList },
  { href: "/evaluation", label: "Evaluation", icon: GaugeCircle },
  { href: "/team", label: "Team & Access", icon: Users },
  { href: "/billing", label: "Billing", icon: CreditCard },
];

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav className="flex flex-col gap-1 px-3">
      {NAV.map(({ href, label, icon: Icon }) => {
        const active = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            className={cn(
              "group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
              active
                ? "text-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-muted",
            )}
          >
            {active && (
              <motion.span
                layoutId="nav-active"
                className="absolute inset-0 rounded-lg border border-accent/30 bg-accent/10"
                transition={{ type: "spring", stiffness: 400, damping: 32 }}
              />
            )}
            <Icon className={cn("relative h-[18px] w-[18px]", active && "text-accent")} />
            <span className="relative">{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

function Footerish() {
  return (
    <div className="mt-auto p-4">
      <div className="rounded-lg border border-border bg-muted/40 p-3 text-xs text-muted-foreground">
        <p className="font-medium text-foreground">
          {isAuthConfigured ? "Signed in" : "Demo workspace"}
        </p>
        <p className="mt-0.5">Informational research only — not investment advice.</p>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="flex min-h-dvh bg-background">
      {/* Desktop sidebar */}
      <aside className="sticky top-0 hidden h-dvh w-64 shrink-0 flex-col border-r border-border bg-card/40 lg:flex">
        <div className="flex h-16 items-center px-5">
          <Wordmark />
        </div>
        <div className="mt-2 flex-1 overflow-y-auto scrollbar-thin">
          <NavLinks />
        </div>
        <Footerish />
      </aside>

      {/* Mobile drawer */}
      <AnimatePresence>
        {open && (
          <>
            <motion.div
              className="fixed inset-0 z-40 bg-black/50 lg:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setOpen(false)}
            />
            <motion.aside
              className="fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-border bg-card lg:hidden"
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", stiffness: 380, damping: 38 }}
            >
              <div className="flex h-16 items-center justify-between px-5">
                <Wordmark />
                <button
                  aria-label="Close menu"
                  onClick={() => setOpen(false)}
                  className="rounded-lg p-2 text-muted-foreground hover:bg-muted"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
              <div className="mt-2 flex-1 overflow-y-auto scrollbar-thin">
                <NavLinks onNavigate={() => setOpen(false)} />
              </div>
              <Footerish />
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Main column */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-4 border-b border-border bg-background/80 px-4 backdrop-blur-md sm:px-6">
          <div className="flex items-center gap-3">
            <button
              aria-label="Open menu"
              onClick={() => setOpen(true)}
              className="rounded-lg p-2 text-muted-foreground hover:bg-muted lg:hidden"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="lg:hidden">
              <Wordmark />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <a
              href="https://github.com/krish2105/FinCopilot-"
              target="_blank"
              rel="noreferrer"
              className="hidden rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground hover:bg-muted sm:inline-flex"
            >
              GitHub
            </a>
            <ThemeToggle />
          </div>
        </header>
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
