import { GitBranch, Layers, Workflow } from "lucide-react";
import { cn } from "@/lib/utils";
import { ROUTE_LABEL } from "@/lib/api";

const ROUTE_META: Record<
  string,
  { icon: typeof Layers; color: string; ring: string }
> = {
  hybrid: {
    icon: Layers,
    color: "text-route-hybrid",
    ring: "border-route-hybrid/30 bg-route-hybrid/10",
  },
  agentic: {
    icon: Workflow,
    color: "text-route-agentic",
    ring: "border-route-agentic/30 bg-route-agentic/10",
  },
  graphrag: {
    icon: GitBranch,
    color: "text-route-graphrag",
    ring: "border-route-graphrag/30 bg-route-graphrag/10",
  },
};

export function RouteBadge({ route, className }: { route: string; className?: string }) {
  const meta = ROUTE_META[route] ?? ROUTE_META.hybrid;
  const Icon = meta.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
        meta.ring,
        meta.color,
        className,
      )}
      title={`Answered via the ${ROUTE_LABEL[route] ?? route} pipeline`}
    >
      <Icon className="h-3.5 w-3.5" />
      {ROUTE_LABEL[route] ?? route}
    </span>
  );
}
