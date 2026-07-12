"use client";

import { motion } from "framer-motion";
import {
  BadgeCheck,
  Compass,
  Calculator,
  ShieldCheck,
  ScanSearch,
} from "lucide-react";

const STEPS = [
  { icon: Compass, label: "Classifying & routing" },
  { icon: ScanSearch, label: "Researching evidence" },
  { icon: Calculator, label: "Analyzing figures" },
  { icon: ShieldCheck, label: "Checking compliance" },
  { icon: BadgeCheck, label: "Verifying faithfulness" },
];

export function AgentProgress({
  currentStep,
  streamText,
}: {
  currentStep?: string;
  streamText?: string;
}) {
  const activeIdx = STEPS.findIndex((s) => s.label === currentStep);
  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-card">
      <div className="mb-4 flex items-center gap-2">
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-pulse-ring rounded-full bg-accent" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-accent" />
        </span>
        <span className="text-sm font-medium text-foreground">
          {currentStep || "Agents at work"}
        </span>
      </div>
      <ul className="flex flex-col gap-2.5">
        {STEPS.map(({ icon: Icon, label }, i) => {
          const done = activeIdx >= 0 && i < activeIdx;
          const active = i === activeIdx || (activeIdx < 0);
          return (
            <motion.li
              key={label}
              className={`flex items-center gap-3 text-sm ${done ? "text-positive" : "text-muted-foreground"}`}
              animate={active && activeIdx < 0 ? { opacity: [0.4, 1, 0.4] } : { opacity: 1 }}
              transition={{ duration: 1.4, repeat: activeIdx < 0 ? Infinity : 0, delay: i * 0.28 }}
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-lg border border-border bg-muted/50">
                <Icon className={`h-4 w-4 ${done ? "text-positive" : "text-accent"}`} />
              </span>
              {label}
            </motion.li>
          );
        })}
      </ul>
      {streamText && (
        <p className="mt-4 border-t border-border pt-3 text-sm leading-relaxed text-foreground">
          {streamText}
          <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-accent align-middle" />
        </p>
      )}
    </div>
  );
}
