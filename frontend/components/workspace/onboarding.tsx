"use client";

import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Circle, Rocket, X } from "lucide-react";
import { useEffect, useState } from "react";

export interface OnboardStep {
  label: string;
  done: boolean;
  href?: string;
}

const KEY = "fincopilot-onboarding-dismissed";

export function Onboarding({ steps }: { steps: OnboardStep[] }) {
  const [dismissed, setDismissed] = useState(true);
  useEffect(() => {
    setDismissed(localStorage.getItem(KEY) === "1");
  }, []);

  const allDone = steps.every((s) => s.done);
  if (dismissed || allDone) return null;

  function dismiss() {
    localStorage.setItem(KEY, "1");
    setDismissed(true);
  }

  const completed = steps.filter((s) => s.done).length;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6 rounded-xl border border-accent/30 bg-accent/[0.06] p-5 text-left"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent/15">
              <Rocket className="h-4 w-4 text-accent" />
            </div>
            <div>
              <p className="text-sm font-semibold text-foreground">Get started</p>
              <p className="text-xs text-muted-foreground">
                {completed}/{steps.length} complete
              </p>
            </div>
          </div>
          <button
            onClick={dismiss}
            aria-label="Dismiss"
            className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <ul className="mt-3 flex flex-col gap-1.5">
          {steps.map((s) => {
            const Icon = s.done ? CheckCircle2 : Circle;
            const inner = (
              <span
                className={`flex items-center gap-2.5 rounded-lg px-2 py-1.5 text-sm ${
                  s.done ? "text-muted-foreground line-through" : "text-foreground"
                }`}
              >
                <Icon className={`h-4 w-4 ${s.done ? "text-positive" : "text-muted-foreground"}`} />
                {s.label}
              </span>
            );
            return (
              <li key={s.label}>
                {s.href && !s.done ? (
                  <Link href={s.href} className="block transition-colors hover:bg-muted/50 rounded-lg">
                    {inner}
                  </Link>
                ) : (
                  inner
                )}
              </li>
            );
          })}
        </ul>
      </motion.div>
    </AnimatePresence>
  );
}
