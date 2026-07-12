"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, History, Plus, Share2, Sparkles } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { api, type AgentAnswer, type Citation } from "@/lib/api";
import { track } from "@/lib/analytics";
import { cn } from "@/lib/utils";
import { AgentProgress } from "@/components/workspace/agent-progress";
import { AnswerCard } from "@/components/workspace/answer-card";
import { HistoryPanel } from "@/components/workspace/history-panel";
import { Onboarding } from "@/components/workspace/onboarding";
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

function WorkspaceInner() {
  const [tickers, setTickers] = useState<string[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [rooms, setRooms] = useState<{ id: string; name: string }[]>([]);
  const [roomId, setRoomId] = useState<string>("");
  const [input, setInput] = useState("");
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [loading, setLoading] = useState(false);
  const [slow, setSlow] = useState(false);
  const [streamStep, setStreamStep] = useState("");
  const [streamText, setStreamText] = useState("");
  const [activeCite, setActiveCite] = useState<Citation | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const params = useSearchParams();
  const autoRan = useRef(false);

  async function loadConversation(id: string) {
    try {
      const { messages } = await api.conversation(id);
      const ex: Exchange[] = [];
      messages.forEach((m, i) => {
        if (m.role === "user") ex.push({ id: Date.now() + i, query: m.content });
        else if (m.role === "assistant" && ex.length) ex[ex.length - 1].answer = m.answer;
      });
      setExchanges(ex);
    } catch {
      toast.error("Could not load conversation");
    }
  }

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
    setSlow(false);
    setStreamStep("");
    setStreamText("");
    track("query_asked", { scoped: Boolean(roomId), tickers: selected.length });
    // Cold-start masking: the free backend can sleep and take ~50s on first hit.
    const slowTimer = setTimeout(() => setSlow(true), 8000);
    try {
      await api.askStream(query, selected, roomId || undefined, {
        onStep: (label) => setStreamStep(label),
        onToken: (t) => setStreamText((s) => s + t),
        onAnswer: (answer) =>
          setExchanges((e) => e.map((x) => (x.id === id ? { ...x, answer } : x))),
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Request failed";
      setExchanges((e) => e.map((x) => (x.id === id ? { ...x, error: msg } : x)));
      toast.error("Could not reach the API", {
        description: "The backend may be waking up — try again in a moment.",
      });
    } finally {
      clearTimeout(slowTimer);
      setLoading(false);
      setSlow(false);
      setStreamStep("");
      setStreamText("");
    }
  }

  // Shareable permalink: /workspace?q=... re-runs the question for a visitor.
  function shareQuery(q: string) {
    const url = `${window.location.origin}/workspace?q=${encodeURIComponent(q)}`;
    navigator.clipboard?.writeText(url).then(
      () => toast.success("Share link copied", { description: "Anyone with the link can re-run this question." }),
      () => toast.error("Couldn't copy link"),
    );
  }

  // Auto-run a shared question once on load.
  useEffect(() => {
    const q = params.get("q");
    if (q && !autoRan.current) {
      autoRan.current = true;
      submit(q);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  function openCite(marker: string, answer: AgentAnswer) {
    const c = answer.citations.find((x) => x.marker === marker);
    if (c) setActiveCite(c);
  }

  const empty = exchanges.length === 0;

  return (
    <div className="relative mx-auto flex h-[calc(100dvh-4rem)] max-w-3xl flex-col">
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-2.5 sm:px-6">
        <button
          onClick={() => setHistoryOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground hover:bg-muted"
        >
          <History className="h-3.5 w-3.5" /> History
        </button>
        {exchanges.length > 0 && (
          <button
            onClick={() => setExchanges([])}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground hover:bg-muted"
          >
            <Plus className="h-3.5 w-3.5" /> New chat
          </button>
        )}
      </div>

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
            <div className="mt-7 w-full">
              <Onboarding
                steps={[
                  { label: "Ask your first question", done: false },
                  { label: "Create a private data room", done: rooms.length > 0, href: "/rooms" },
                  { label: "Upload a document to a room", done: false, href: "/rooms" },
                ]}
              />
              <div className="grid w-full gap-2 sm:grid-cols-2">
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
                  <div className="flex flex-col gap-2">
                    <AnswerCard answer={ex.answer} onCite={(m) => openCite(m, ex.answer!)} />
                    <button
                      onClick={() => shareQuery(ex.query)}
                      className="inline-flex w-fit items-center gap-1.5 rounded-lg px-2 py-1 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground hover:bg-muted cursor-pointer"
                    >
                      <Share2 className="h-3.5 w-3.5" /> Share
                    </button>
                  </div>
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
                  <AgentProgress currentStep={streamStep} streamText={streamText} />
                  {slow && (
                    <p className="mt-2 text-center text-xs text-muted-foreground">
                      Waking the free backend — the first request after idle can take ~50s. Hang tight.
                    </p>
                  )}
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
      <HistoryPanel
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        onSelect={loadConversation}
      />
    </div>
  );
}

export default function WorkspacePage() {
  // useSearchParams (for shareable ?q= links) must live inside a Suspense boundary.
  return (
    <Suspense fallback={null}>
      <WorkspaceInner />
    </Suspense>
  );
}
