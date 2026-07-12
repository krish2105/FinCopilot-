"use client";

import { AnimatePresence, motion } from "framer-motion";
import { MessageSquare, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type ConversationMeta } from "@/lib/api";
import { timeAgo } from "@/lib/utils";

export function HistoryPanel({
  open,
  onClose,
  onSelect,
}: {
  open: boolean;
  onClose: () => void;
  onSelect: (id: string) => void;
}) {
  const [convs, setConvs] = useState<ConversationMeta[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    api
      .conversations()
      .then((r) => setConvs(r.conversations))
      .catch(() => setConvs([]))
      .finally(() => setLoading(false));
  }, [open]);

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className="fixed inset-0 z-40 bg-black/50 backdrop-blur-[1px]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.aside
            className="fixed inset-y-0 left-0 z-50 flex w-full max-w-sm flex-col border-r border-border bg-card shadow-2xl"
            initial={{ x: "-100%" }}
            animate={{ x: 0 }}
            exit={{ x: "-100%" }}
            transition={{ type: "spring", stiffness: 380, damping: 40 }}
          >
            <div className="flex items-center justify-between border-b border-border px-5 py-4">
              <div className="flex items-center gap-2">
                <MessageSquare className="h-4 w-4 text-accent" />
                <span className="text-sm font-semibold">History</span>
              </div>
              <button
                aria-label="Close history"
                onClick={onClose}
                className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto scrollbar-thin p-2">
              {loading ? (
                <p className="p-4 text-sm text-muted-foreground">Loading…</p>
              ) : convs.length === 0 ? (
                <p className="p-4 text-sm text-muted-foreground">No past conversations yet.</p>
              ) : (
                <ul className="flex flex-col">
                  {convs.map((c) => (
                    <li key={c.id}>
                      <button
                        onClick={() => {
                          onSelect(c.id);
                          onClose();
                        }}
                        className="flex w-full flex-col gap-0.5 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-muted cursor-pointer"
                      >
                        <span className="truncate text-sm text-foreground">
                          {c.title || "Untitled"}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {timeAgo(c.created_at)}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
