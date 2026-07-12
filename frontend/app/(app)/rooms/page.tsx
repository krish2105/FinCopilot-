"use client";

import { motion } from "framer-motion";
import { FileText, FolderLock, Loader2, Plus, Trash2, Upload } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { api, type DocumentMeta, type Workspace } from "@/lib/api";
import { track } from "@/lib/analytics";
import { timeAgo } from "@/lib/utils";
import { PageHeader, EmptyState } from "@/components/ui/page-header";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Skeleton } from "@/components/ui/misc";

export default function RoomsPage() {
  const [rooms, setRooms] = useState<Workspace[]>([]);
  const [active, setActive] = useState<Workspace | null>(null);
  const [docs, setDocs] = useState<DocumentMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);
  const [newName, setNewName] = useState("");
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const loadRooms = useCallback(() => {
    setLoading(true);
    api
      .workspaces()
      .then((r) => {
        setRooms(r.workspaces);
        setActive((a) => a ?? r.workspaces[0] ?? null);
        setOffline(false);
      })
      .catch(() => setOffline(true))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => loadRooms(), [loadRooms]);

  const loadDocs = useCallback((ws: Workspace) => {
    api.documents(ws.id).then((r) => setDocs(r.documents)).catch(() => setDocs([]));
  }, []);

  useEffect(() => {
    if (active) loadDocs(active);
  }, [active, loadDocs]);

  async function createRoom() {
    if (!newName.trim()) return;
    try {
      const ws = await api.createWorkspace(newName.trim());
      setNewName("");
      setRooms((r) => [...r, ws]);
      setActive(ws);
      toast.success(`Data room "${ws.name}" created`);
    } catch {
      toast.error("Could not create data room");
    }
  }

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !active) return;
    setUploading(true);
    try {
      await api.uploadDocument(active.id, file);
      track("document_uploaded", { ext: file.name.split(".").pop() });
      toast.success(`${file.name} ingested`);
      loadDocs(active);
    } catch (err) {
      toast.error("Upload failed", {
        description: err instanceof Error ? err.message : undefined,
      });
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function removeDoc(id: string) {
    try {
      await api.deleteDocument(id);
      setDocs((d) => d.filter((x) => x.id !== id));
    } catch {
      toast.error("Delete failed");
    }
  }

  if (offline) {
    return (
      <div className="p-4 sm:p-6 lg:p-8">
        <PageHeader title="Data Rooms" />
        <div className="mt-6">
          <EmptyState
            icon={FolderLock}
            title="Backend unreachable"
            description="Start the API and set NEXT_PUBLIC_API_URL to manage private data rooms."
          />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-4 sm:p-6 lg:p-8">
      <PageHeader
        title="Data Rooms"
        description="Private, tenant-isolated document collections. Upload filings or PDFs and ask questions scoped to just that room — nothing leaks across tenants."
      />

      <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
        {/* Rooms list */}
        <Card className="p-4">
          <div className="mb-3 flex gap-2">
            <Input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && createRoom()}
              placeholder="New data room…"
              className="h-9"
            />
            <Button size="icon" onClick={createRoom} aria-label="Create" className="h-9 w-9 shrink-0">
              <Plus className="h-4 w-4" />
            </Button>
          </div>
          {loading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-10" />
              ))}
            </div>
          ) : (
            <ul className="flex flex-col gap-1">
              {rooms.map((ws) => (
                <li key={ws.id}>
                  <button
                    onClick={() => setActive(ws)}
                    className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors cursor-pointer ${
                      active?.id === ws.id
                        ? "bg-accent/10 text-accent border border-accent/30"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    }`}
                  >
                    <FolderLock className="h-4 w-4" />
                    <span className="truncate">{ws.name}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {/* Documents */}
        <Card className="p-5">
          {active ? (
            <>
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <h3 className="text-sm font-semibold">{active.name}</h3>
                <>
                  <input
                    ref={fileRef}
                    type="file"
                    accept=".pdf,.txt,.md,.csv,.html,.htm"
                    onChange={onUpload}
                    className="hidden"
                  />
                  <Button size="sm" onClick={() => fileRef.current?.click()} disabled={uploading}>
                    {uploading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Upload className="h-4 w-4" />
                    )}
                    Upload document
                  </Button>
                </>
              </div>
              {docs.length === 0 ? (
                <EmptyState
                  icon={FileText}
                  title="No documents yet"
                  description="Upload a PDF, filing, or text file. It's chunked, embedded, and searchable only within this room."
                />
              ) : (
                <ul className="flex flex-col divide-y divide-border">
                  {docs.map((d) => (
                    <motion.li
                      key={d.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex items-center justify-between gap-3 py-3"
                    >
                      <div className="flex min-w-0 items-center gap-3">
                        <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                        <div className="min-w-0">
                          <p className="truncate text-sm text-foreground">{d.filename}</p>
                          <p className="text-xs text-muted-foreground">
                            {d.chunk_count} chunks · {timeAgo(d.created_at)}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={d.status === "ready" ? "positive" : "warning"}>
                          {d.status}
                        </Badge>
                        <button
                          onClick={() => removeDoc(d.id)}
                          aria-label="Delete"
                          className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-danger"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </motion.li>
                  ))}
                </ul>
              )}
            </>
          ) : (
            <EmptyState
              icon={FolderLock}
              title="Create your first data room"
              description="Group a deal's documents together and ask questions scoped to just those files."
            />
          )}
        </Card>
      </div>
    </div>
  );
}
