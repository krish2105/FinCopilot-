"use client";

import type { Citation } from "@/lib/api";
import { cn } from "@/lib/utils";

/** Renders answer text, turning [n] markers into clickable citation chips. */
export function CitationText({
  text,
  citations,
  onCite,
  className,
}: {
  text: string;
  citations: Citation[];
  onCite: (marker: string) => void;
  className?: string;
}) {
  const byMarker = new Map(citations.map((c) => [c.marker, c]));
  const parts = text.split(/(\[\d+\])/g);

  return (
    <p className={cn("leading-relaxed", className)}>
      {parts.map((part, i) => {
        if (/^\[\d+\]$/.test(part) && byMarker.has(part)) {
          const c = byMarker.get(part)!;
          return (
            <button
              key={i}
              onClick={() => onCite(part)}
              title={`${c.ticker} ${c.doc_type}${c.page != null ? ` p.${c.page}` : ""}`}
              className="mx-0.5 inline-flex -translate-y-0.5 items-center rounded-md border border-accent/30 bg-accent/10 px-1.5 text-[11px] font-medium font-mono text-accent align-middle transition-colors hover:bg-accent/20 hover:border-accent/50 cursor-pointer"
            >
              {part.slice(1, -1)}
            </button>
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </p>
  );
}
