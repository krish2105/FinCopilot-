import type { MetadataRoute } from "next";

const SITE =
  process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") || "https://fin-copilot-six.vercel.app";

// Curated questions that get their own crawlable answer page (/a/[q]).
const EXPLORE_QUESTIONS = [
  "What risk factors does Apple disclose?",
  "What supply-chain risks does Microsoft cite?",
  "Which companies share competition risk?",
  "What was Apple's total net sales?",
  "Compare Apple net sales and Microsoft revenue",
  "What is NVIDIA's gross margin trend?",
  "Who are Apple's key executives?",
  "What are 3M's subsidiaries?",
  "Which companies face regulatory risk?",
];

export default function sitemap(): MetadataRoute.Sitemap {
  const staticRoutes = [
    "",
    "/explore",
    "/pricing",
    "/docs",
    "/trust",
    "/status",
    "/legal/terms",
    "/legal/privacy",
    "/legal/dpa",
    "/legal/subprocessors",
  ].map((path) => ({
    url: `${SITE}${path}`,
    changeFrequency: "weekly" as const,
    priority: path === "" ? 1 : 0.7,
  }));

  const answerRoutes = EXPLORE_QUESTIONS.map((q) => ({
    url: `${SITE}/a/${encodeURIComponent(q)}`,
    changeFrequency: "weekly" as const,
    priority: 0.6,
  }));

  return [...staticRoutes, ...answerRoutes];
}
