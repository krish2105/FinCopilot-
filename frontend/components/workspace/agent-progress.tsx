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

export function AgentProgress() {
  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-card">
      <div className="mb-4 flex items-center gap-2">
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-pulse-ring rounded-full bg-accent" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-accent" />
        </span>
        <span className="text-sm font-medium text-foreground">Agents at work</span>
      </div>
      <ul className="flex flex-col gap-2.5">
        {STEPS.map(({ icon: Icon, label }, i) => (
          <motion.li
            key={label}
            className="flex items-center gap-3 text-sm text-muted-foreground"
            initial={{ opacity: 0.35 }}
            animate={{ opacity: [0.35, 1, 0.35] }}
            transition={{
              duration: 1.4,
              repeat: Infinity,
              delay: i * 0.28,
              ease: "easeInOut",
            }}
          >
            <span className="flex h-7 w-7 items-center justify-center rounded-lg border border-border bg-muted/50">
              <Icon className="h-4 w-4 text-accent" />
            </span>
            {label}
          </motion.li>
        ))}
      </ul>
    </div>
  );
}
