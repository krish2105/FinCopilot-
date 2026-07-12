"""Test config: force the deterministic offline embedder so the suite needs no
torch, no network, and no API keys — and is fully reproducible in CI."""

import os

# Must be set before src.config.settings is first imported/cached.
os.environ.setdefault("FINCOPILOT_EMBED_BACKEND", "hash")
os.environ.setdefault("FINCOPILOT_OFFLINE_MODE", "true")

import pytest

from src.config.settings import Settings


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        fincopilot_embed_backend="hash",
        fincopilot_offline_mode=True,
        data_dir=str(tmp_path),
    )


SAMPLE_10K_HTML = """
<html><body>
<p>Item 1. Business</p>
<p>Acme Corp designs and sells widgets across global markets.</p>
<div><table>
<tr><th>Metric</th><th>2024</th><th>2023</th></tr>
<tr><td>Revenue</td><td>1,000</td><td>900</td></tr>
<tr><td>Net income</td><td>120</td><td>100</td></tr>
</table></div>
<p>Item 1A. Risk Factors</p>
<p>Our business faces competition, supply chain risk, and going concern uncertainty.</p>
<p>Foreign currency fluctuations may adversely affect results.</p>
</body></html>
"""


@pytest.fixture
def sample_html() -> str:
    return SAMPLE_10K_HTML
