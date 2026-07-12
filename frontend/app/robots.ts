import type { MetadataRoute } from "next";

const SITE =
  process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") || "https://fin-copilot-six.vercel.app";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      // Private app surfaces shouldn't be indexed; marketing + answer pages should.
      disallow: ["/workspace", "/rooms", "/dashboard", "/audit", "/evaluation", "/team", "/billing"],
    },
    sitemap: `${SITE}/sitemap.xml`,
  };
}
