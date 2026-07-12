from src.agents import analyst, compliance, visualization
from src.agents.schemas import AnalystOutput, Finding
from src.ingestion.models import DocType, SourceMetadata
from src.retrieval.types import Citation, RetrievalResult, RetrievedChunk


def _result(chunks_data):
    """chunks_data: list of (marker, text, section)."""
    chunks, cites = [], []
    for marker, text, section in chunks_data:
        md = SourceMetadata(
            ticker="AAPL",
            doc_type=DocType.TEN_K,
            page=1,
            section=section,
            title="AAPL 10-K",
            source_url="https://sec.gov/x",
        )
        chunks.append(RetrievedChunk(chunk_id=marker, text=text, metadata=md, marker=marker))
        cites.append(
            Citation(marker=marker, ticker="AAPL", doc_type="10-K", page=1, section=section)
        )
    return RetrievalResult(query="q", chunks=chunks, citations=cites)


# --- Analyst ---
def test_analyst_stub_extracts_cited_figures():
    res = _result([("[1]", "Total net sales were $391,035 million in fiscal 2024.", "Item 7")])
    out = analyst._stub_findings(res)
    assert out.findings
    assert any("391" in f.value for f in out.findings)
    assert all(f.citation_marker == "[1]" for f in out.findings)


def test_analyst_empty_evidence():
    from src.config.settings import Settings
    from src.providers.router import ProviderRouter

    r = ProviderRouter(Settings(fincopilot_offline_mode=True))
    out = analyst.analyze(r, "q", None)
    assert out.findings == []


# --- Compliance ---
def test_compliance_flags_going_concern():
    res = _result([("[1]", "There is substantial doubt about our going concern.", "Item 1A")])
    out = compliance.check(res, AnalystOutput())
    assert out.verdict == "ok"
    assert any(f.category == "going_concern" for f in out.flags)


def test_compliance_insufficient_when_no_evidence():
    out = compliance.check(None, AnalystOutput())
    assert out.verdict == "insufficient_evidence"


def test_compliance_detects_uncited_finding():
    res = _result([("[1]", "Revenue grew.", "Item 7")])
    analyst_out = AnalystOutput(findings=[Finding(label="x", value="1", citation_marker="[9]")])
    out = compliance.check(res, analyst_out)
    assert out.uncited_findings == ["x"]


# --- Visualization ---
def test_visualization_builds_chart_from_figures():
    a = AnalystOutput(
        findings=[Finding(label="Net sales", value="$391,035 million", citation_marker="[1]")]
    )
    viz = visualization.build(a)
    assert viz.charts
    pt = viz.charts[0].series[0].points[0]
    assert pt.y == 391035 * 1e6


def test_visualization_empty():
    assert visualization.build(AnalystOutput()).charts == []
