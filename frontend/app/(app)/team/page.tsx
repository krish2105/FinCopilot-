"use client";

import { motion } from "framer-motion";
import { Copy, KeyRound, Mail, Trash2, UserPlus, Users } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { PageHeader, EmptyState } from "@/components/ui/page-header";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Skeleton } from "@/components/ui/misc";

interface Member {
  id: string;
  email: string;
  role: string;
}
interface Invite {
  id: string;
  email: string;
  role: string;
}
interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  last_used: string | null;
}

const ROLE_VARIANT: Record<string, "accent" | "positive" | "outline"> = {
  owner: "positive",
  admin: "accent",
};

export default function TeamPage() {
  const [members, setMembers] = useState<Member[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [seats, setSeats] = useState({ used: 0, limit: 1 });
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [keyName, setKeyName] = useState("");
  const [newKey, setNewKey] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([api.members(), api.invites().catch(() => ({ invites: [] })), api.apiKeys()])
      .then(([m, inv, k]) => {
        setMembers(m.members);
        setSeats({ used: m.seats_used, limit: m.seats_limit });
        setInvites(inv.invites);
        setKeys(k.keys);
        setOffline(false);
      })
      .catch(() => setOffline(true))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => load(), [load]);

  async function sendInvite() {
    if (!email.trim()) return;
    try {
      await api.invite(email.trim(), role);
      setEmail("");
      toast.success("Invite created");
      load();
    } catch (err) {
      toast.error("Invite failed", { description: err instanceof Error ? err.message : undefined });
    }
  }

  async function createKey() {
    try {
      const { api_key } = await api.createApiKey(keyName.trim() || "default");
      setNewKey(api_key);
      setKeyName("");
      load();
    } catch (err) {
      toast.error("Could not create key", {
        description: err instanceof Error ? err.message : undefined,
      });
    }
  }

  if (offline) {
    return (
      <div className="p-4 sm:p-6 lg:p-8">
        <PageHeader title="Team" />
        <div className="mt-6">
          <EmptyState
            icon={Users}
            title="Backend unreachable"
            description="Start the API and set NEXT_PUBLIC_API_URL to manage your team and API keys."
          />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-4 sm:p-6 lg:p-8">
      <PageHeader
        title="Team & Access"
        description="Invite teammates, manage roles, and issue API keys. Seats are enforced by your plan."
      >
        <Badge variant="outline">
          {seats.used}/{seats.limit} seats
        </Badge>
      </PageHeader>

      {/* Invite */}
      <Card className="p-5">
        <div className="mb-3 flex items-center gap-2">
          <UserPlus className="h-4 w-4 text-accent" />
          <h3 className="text-sm font-semibold">Invite a teammate</h3>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <div className="relative flex-1">
            <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="email"
              placeholder="teammate@firm.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="pl-9"
            />
          </div>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="h-10 rounded-lg border border-input bg-background px-3 text-sm cursor-pointer"
          >
            <option value="viewer">Viewer</option>
            <option value="member">Member</option>
            <option value="admin">Admin</option>
          </select>
          <Button onClick={sendInvite}>Invite</Button>
        </div>
      </Card>

      {/* Members */}
      <Card className="overflow-hidden p-0">
        <div className="border-b border-border px-5 py-3">
          <h3 className="text-sm font-semibold">Members</h3>
        </div>
        {loading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-10" />
            ))}
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {members.map((m) => (
              <li key={m.id} className="flex items-center justify-between px-5 py-3">
                <span className="text-sm text-foreground">{m.email || m.id}</span>
                <div className="flex items-center gap-3">
                  <Badge variant={ROLE_VARIANT[m.role] ?? "outline"}>{m.role}</Badge>
                </div>
              </li>
            ))}
            {invites.map((inv) => (
              <li key={inv.id} className="flex items-center justify-between px-5 py-3">
                <span className="text-sm text-muted-foreground">
                  {inv.email} <span className="text-xs">· pending</span>
                </span>
                <div className="flex items-center gap-2">
                  <Badge variant="warning">{inv.role}</Badge>
                  <button
                    onClick={() => api.revokeInvite(inv.id).then(load)}
                    aria-label="Revoke"
                    className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-danger"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {/* API keys */}
      <Card className="p-5">
        <div className="mb-3 flex items-center gap-2">
          <KeyRound className="h-4 w-4 text-accent" />
          <h3 className="text-sm font-semibold">API keys</h3>
        </div>
        {newKey && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mb-3 flex items-center justify-between gap-3 rounded-lg border border-accent/30 bg-accent/[0.06] p-3"
          >
            <code className="truncate font-mono text-xs text-foreground">{newKey}</code>
            <button
              onClick={() => {
                navigator.clipboard.writeText(newKey);
                toast.success("Copied — it won't be shown again");
              }}
              className="flex shrink-0 items-center gap-1 text-xs text-accent hover:underline"
            >
              <Copy className="h-3.5 w-3.5" /> Copy
            </button>
          </motion.div>
        )}
        <div className="flex gap-2">
          <Input
            placeholder="Key name (e.g. prod)"
            value={keyName}
            onChange={(e) => setKeyName(e.target.value)}
            className="flex-1"
          />
          <Button variant="secondary" onClick={createKey}>
            Create key
          </Button>
        </div>
        {keys.length > 0 && (
          <ul className="mt-3 divide-y divide-border">
            {keys.map((k) => (
              <li key={k.id} className="flex items-center justify-between py-2.5">
                <span className="text-sm text-foreground">
                  {k.name} <span className="font-mono text-xs text-muted-foreground">{k.prefix}…</span>
                </span>
                <button
                  onClick={() => api.deleteApiKey(k.id).then(load)}
                  aria-label="Revoke key"
                  className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-danger"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
