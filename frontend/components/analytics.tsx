"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { initAnalytics, pageview } from "@/lib/analytics";

export function Analytics() {
  const pathname = usePathname();
  useEffect(() => {
    initAnalytics().then(() => pageview(pathname));
  }, [pathname]);
  return null;
}
