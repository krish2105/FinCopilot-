import type { MetadataRoute } from "next";

// PWA manifest — makes FinCopilot installable on phones and desktops ("Add to
// Home Screen"), launching standalone without browser chrome. Zero cost, and it
// makes the retail experience feel like a real app.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "FinCopilot — Agentic Financial Analyst",
    short_name: "FinCopilot",
    description:
      "A multi-agent AI analyst that reads real SEC filings and returns fully cited answers — or honestly says 'insufficient evidence'.",
    start_url: "/workspace",
    display: "standalone",
    background_color: "#0a0a0b",
    theme_color: "#0a0a0b",
    orientation: "portrait-primary",
    categories: ["finance", "productivity", "business"],
    icons: [
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" },
    ],
  };
}
