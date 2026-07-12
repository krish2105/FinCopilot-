import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { RouteBadge } from "@/components/route-badge";
import { CitationText } from "@/components/workspace/citation-text";
import type { Citation } from "@/lib/api";

describe("RouteBadge", () => {
  it("renders the human label per route", () => {
    render(<RouteBadge route="graphrag" />);
    expect(screen.getByText("GraphRAG")).toBeTruthy();
    render(<RouteBadge route="hybrid" />);
    expect(screen.getByText("Hybrid Search")).toBeTruthy();
  });
});

describe("CitationText", () => {
  const cites: Citation[] = [
    {
      marker: "[1]",
      ticker: "AAPL",
      doc_type: "10-K",
      title: "",
      page: 26,
      section: "Item 1A",
      source_url: "",
      excerpt: "",
    },
  ];

  it("turns [n] markers into clickable chips", () => {
    const onCite = vi.fn();
    render(
      <CitationText text="Apple discloses risk factors [1] in its filing." citations={cites} onCite={onCite} />,
    );
    const chip = screen.getByText("1");
    fireEvent.click(chip);
    expect(onCite).toHaveBeenCalledWith("[1]");
  });

  it("leaves unknown markers as plain text", () => {
    const { container } = render(
      <CitationText text="No source here [9]." citations={cites} onCite={() => {}} />,
    );
    expect(container.textContent).toContain("[9]");
  });
});
