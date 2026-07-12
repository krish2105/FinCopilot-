"use client";

import { motion } from "framer-motion";
import { BadgeCheck, Clock, Quote } from "lucide-react";
import { RouteBadge } from "@/components/route-badge";
import { Badge } from "@/components/ui/badge";

/** A static, premium mock of a cited answer — the hero proof visual. */
export function SampleAnswer() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24, rotateX: 6 }}
      animate={{ opacity: 1, y: 0, rotateX: 0 }}
      transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1], delay: 0.15 }}
      className="w-full max-w-lg"
    >
      <div className="rounded-2xl border border-border bg-card/80 p-1.5 shadow-card backdrop-blur">
        <div className="rounded-xl border border-border/60 bg-background/60 p-5">
          {/* Query */}
          <div className="mb-4 flex justify-end">
            <span className="rounded-2xl rounded-tr-sm bg-accent px-3.5 py-2 text-xs font-medium text-accent-foreground">
              What risk factors does Apple disclose?
            </span>
          </div>

          {/* Meta */}
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <RouteBadge route="hybrid" />
            <Badge variant="positive">
              <BadgeCheck className="h-3.5 w-3.5" /> Verified
            </Badge>
            <span className="ml-auto flex items-center gap-2 text-[11px] text-muted-foreground">
              <Clock className="h-3 w-3" /> 41 ms
              <Quote className="h-3 w-3" /> 6 sources
            </span>
          </div>

          {/* Answer */}
          <p className="text-sm leading-relaxed text-foreground">
            Apple discloses supply-chain concentration, foreign-exchange volatility, and intense
            competition as principal risks
            <Chip n="1" /> , alongside litigation and regulatory exposure
            <Chip n="3" /> .
          </p>

          {/* Faithfulness */}
          <div className="mt-4 border-t border-border pt-3">
            <div className="mb-1 flex items-center justify-between text-[11px]">
              <span className="flex items-center gap-1 font-medium text-foreground">
                <BadgeCheck className="h-3 w-3 text-positive" /> Faithfulness
              </span>
              <span className="font-mono text-muted-foreground">100%</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-muted">
              <motion.div
                className="h-full rounded-full bg-positive"
                initial={{ width: 0 }}
                animate={{ width: "100%" }}
                transition={{ duration: 1, delay: 0.6 }}
              />
            </div>
          </div>

          {/* Sources */}
          <div className="mt-3 flex flex-wrap gap-1.5">
            {["AAPL 10-K p.26 · Item 1A", "AAPL 10-Q p.25 · Legal"].map((s, i) => (
              <span
                key={s}
                className="rounded-md border border-border bg-muted/40 px-2 py-1 text-[10px] text-muted-foreground"
              >
                <span className="font-mono text-accent">[{i === 0 ? 1 : 3}]</span> {s}
              </span>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function Chip({ n }: { n: string }) {
  return (
    <span className="mx-0.5 inline-flex -translate-y-0.5 items-center rounded-md border border-accent/30 bg-accent/10 px-1.5 align-middle text-[10px] font-medium font-mono text-accent">
      {n}
    </span>
  );
}
