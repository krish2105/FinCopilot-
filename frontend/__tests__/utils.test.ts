import { describe, expect, it } from "vitest";
import { formatCompact, timeAgo } from "@/lib/utils";

describe("formatCompact", () => {
  it("formats magnitudes", () => {
    expect(formatCompact(391_035_000_000)).toBe("391.04B");
    expect(formatCompact(1_290)).toBe("1.3K");
    expect(formatCompact(42)).toBe("42");
    expect(formatCompact(2_500_000)).toBe("2.50M");
  });
});

describe("timeAgo", () => {
  it("handles recent + invalid", () => {
    expect(timeAgo(new Date().toISOString())).toBe("just now");
    expect(timeAgo("not-a-date")).toBe("");
    const anHourAgo = new Date(Date.now() - 3600_000).toISOString();
    expect(timeAgo(anHourAgo)).toContain("h ago");
  });
});
