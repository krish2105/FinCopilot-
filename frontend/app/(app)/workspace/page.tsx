"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { api, type AgentAnswer, type Citation } from "@/lib/api";
import { cn } from "@/lib/utils";
import { AgentProgress } from "@/components/workspace/agent-progress";
import { AnswerCard } from "@/components/workspace/answer-card";
import { SourcePanel } from "@/components/workspace/source-panel";
import { Button } from "@/components/ui/button";

interface Exchange {
  id: number;
  query: string;
  answer?: AgentAnswer;
  error?: string;
}

const SUGGESTIONS = [
  "What risk factors does Apple disclose?",
  "Which companies share competition risk?",
  "Compare Apple net sales and Microsoft revenue",
  "What was Apple's total net sales?",
];

export default function WorkspacePage() {
  const [tickers, setTickers] = useState<string[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [rooms, setRooms] = useState<{ id: string; name: string }[]>([]);
  const [roomId, setRoomId] = useState<string>("");
  const [input, setInput] = useState("");
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeCite, setActiveCite] = useState<Citation | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api
      .meta()
      .then((m) => setTickers(m.tickers || []))
      .catch(() => {});
    api
      .workspaces()
      .then((r) => setRooms(r.workspaces.map((w) => ({ id: w.id, name: w.name }))))
      .catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [exchanges, loading]);

  async function submit(q: string) {
    const query = q.trim();
    if (!query || loading) return;
    const id = Date.now();
    setExchanges((e) => [...e, { id, query }]);
    setInput("");
    setLoading(true);
    try {
      const answer = await api.ask(query, selected, roomId || undefined);
      setExchanges((e) => e.map((x) => (x.id === id ? { ...x, answer } : x)));
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Request failed";
      setExchanges((e) => e.map((x) => (x.id === id ? { ...x, error: msg } : x)));
      toast.error("Could not reach the API", {
        description: "Make sure the backend is running and NEXT_PUBLIC_API_URL is set.",
      });
    } finally {
      setLoading(false);
    }
  }

  function openCite(marker: string, answer: AgentAnswer) {
    const c = answer.citations.find((x) => x.marker === marker);
    if (c) setActiveCite(c);
  }

  const empty = exchanges.length === 0;

  return (
    <div className="relative mx-auto flex h-[calc(100dvh-4rem)] max-w-3xl flex-col">
      {/* Scroll area */}
      <div className="flex-1 overflow-y-auto scrollbar-thin px-4 py-6 sm:px-6">
        {empty ? (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mx-auto flex max-w-xl flex-col items-center pt-10 text-center"
          >
            <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl border border-accent/30 bg-accent/10">
              <Sparkles className="h-6 w-6 text-accent" />
            </div>
            <h1 className="text-2xl font-semibold tracking-tight">Ask about real filings</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              A team of agents retrieves evidence, runs the analysis, checks compliance, and
              returns a fully cited answer — or refuses when the evidence isn&apos;t there.
            </p>
            <div className="mt-7 grid w-full gap-2 sm:grid-cols-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => submit(s)}
                  className="rounded-xl border border-border bg-card p-3.5 text-left text-sm text-muted-foreground transition-all hover:border-accent/40 hover:text-foreground hover:shadow-card cursor-pointer"
                >
                  {s}
                </button>
              ))}
            </div>
          </motion.div>
        ) : (
          <div className="flex flex-col gap-8">
            {exchanges.map((ex) => (
              <div key={ex.id} className="flex flex-col gap-4">
                <div className="flex justify-end">
                  <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-accent px-4 py-2.5 text-sm font-medium text-accent-foreground shadow-glow">
                    {ex.query}
                  </div>
                </div>
                {ex.answer && (
                  <AnswerCard answer={ex.answer} onCite={(m) => openCite(m, ex.answer!)} />
                )}
                {ex.error && (
                  <div className="rounded-xl border border-danger/30 bg-danger/[0.07] p-4 text-sm text-danger">
                    {ex.error}
                  </div>
                )}
              </div>
            ))}
            <AnimatePresence>
              {loading && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                >
                  <AgentProgress />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Composer */}
      <div className="border-t border-border bg-background/80 p-4 backdrop-blur-md sm:px-6">
        {rooms.length > 0 && (
          <div className="mb-2.5 flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Scope
            </span>
            <select
              value={roomId}
              onChange={(e) => setRoomId(e.target.value)}
              className="rounded-full border border-border bg-card px-2.5 py-0.5 text-[11px] text-foreground focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer"
            >
              <option value="">Public + all rooms</option>
              {rooms.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name} (+ public)
                </option>
              ))}
            </select>
          </div>
        )}
        {tickers.length > 0 && (
          <div className="mb-2.5 flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Filter
            </span>
            {tickers.map((t) => {
              const on = selected.includes(t);
              return (
                <button
                  key={t}
                  onClick={() =>
                    setSelected((s) => (on ? s.filter((x) => x !== t) : [...s, t]))
                  }
                  className={cn(
                    "rounded-full border px-2.5 py-0.5 font-mono text-[11px] transition-colors cursor-pointer",
                    on
                      ? "border-accent/40 bg-accent/15 text-accent"
                      : "border-border text-muted-foreground hover:text-foreground",
                  )}
                >
                  {t}
                </button>
              );
            })}
          </div>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submit(input);
          }}
          className="flex items-end gap-2 rounded-2xl border border-border bg-card p-2 shadow-card focus-within:ring-2 focus-within:ring-ring"
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit(input);
              }
            }}
            rows={1}
            placeholder="Ask about a filing, ratio, risk, or relationship…"
            className="max-h-32 flex-1 resize-none bg-transparent px-2.5 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none scrollbar-thin"
          />
          <Button
            type="submit"
            size="icon"
            disabled={!input.trim() || loading}
            aria-label="Send"
            className="shrink-0 rounded-xl"
          >
            <ArrowUp className="h-4 w-4" />
          </Button>
        </form>
      </div>

      <SourcePanel citation={activeCite} onClose={() => setActiveCite(null)} />
    </div>
  );
}
