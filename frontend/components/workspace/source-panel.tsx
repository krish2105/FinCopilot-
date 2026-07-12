"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ExternalLink, FileText, X } from "lucide-react";
import type { Citation } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

export function SourcePanel({
  citation,
  onClose,
}: {
  citation: Citation | null;
  onClose: () => void;
}) {
  return (
    <AnimatePresence>
      {citation && (
        <>
          <motion.div
            className="fixed inset-0 z-40 bg-black/50 backdrop-blur-[1px] lg:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.aside
            className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-border bg-card shadow-2xl"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 380, damping: 40 }}
          >
            <div className="flex items-center justify-between border-b border-border px-5 py-4">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-accent" />
                <span className="text-sm font-semibold">Source {citation.marker}</span>
              </div>
              <button
                aria-label="Close source"
                onClick={onClose}
                className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="flex flex-1 flex-col gap-4 overflow-y-auto scrollbar-thin p-5">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="accent" className="font-mono">
                  {citation.ticker}
                </Badge>
                <Badge variant="outline">{citation.doc_type}</Badge>
                {citation.page != null && (
                  <Badge variant="outline">p.{citation.page}</Badge>
                )}
              </div>

              {citation.section && (
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Section
                  </p>
                  <p className="mt-1 text-sm text-foreground">{citation.section}</p>
                </div>
              )}

              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Excerpt
                </p>
                <blockquote className="mt-2 rounded-lg border-l-2 border-accent bg-muted/40 p-4 text-sm leading-relaxed text-foreground">
                  {citation.excerpt || "(no excerpt captured)"}
                </blockquote>
              </div>

              {citation.title && (
                <p className="text-xs text-muted-foreground">{citation.title}</p>
              )}
            </div>

            {citation.source_url && (
              <div className="border-t border-border p-4">
                <a
                  href={citation.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center justify-center gap-2 rounded-lg border border-border py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-muted"
                >
                  View original filing
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              </div>
            )}
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
