// PostHog product analytics — guarded. No-op unless NEXT_PUBLIC_POSTHOG_KEY is set.

type PostHogLike = {
  init: (key: string, opts: Record<string, unknown>) => void;
  capture: (event: string, props?: Record<string, unknown>) => void;
};

let posthog: PostHogLike | null = null;
let initialized = false;

export async function initAnalytics() {
  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
  if (!key || initialized || typeof window === "undefined") return;
  initialized = true;
  const mod = await import("posthog-js");
  posthog = mod.default as unknown as PostHogLike;
  posthog.init(key, {
    api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://us.i.posthog.com",
    capture_pageview: false,
    person_profiles: "identified_only",
  });
}

export function track(event: string, props?: Record<string, unknown>) {
  posthog?.capture(event, props);
}

export function pageview(path: string) {
  posthog?.capture("$pageview", { $current_url: path });
}
