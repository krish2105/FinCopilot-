"""Natural-language metric -> US-GAAP XBRL concept (Phase 45).

Companies tag the same economic idea with different concepts, and the tag they use
changes over time (Apple moved revenue from ``Revenues`` to
``RevenueFromContractWithCustomerExcludingAssessedTax`` when ASC 606 landed). So every
metric is a *fallback chain*: try each concept in order and take the first that has
data. Without this, "what was revenue" silently returns nothing for half the market.
"""

from __future__ import annotations

# Ordered by preference — first concept with data wins.
METRICS: dict[str, list[str]] = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
    ],
    "cost_of_revenue": ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfServices"],
    "gross_profit": ["GrossProfit"],
    "operating_expenses": ["OperatingExpenses", "CostsAndExpenses"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "eps_diluted": ["EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted"],
    "eps_basic": ["EarningsPerShareBasic"],
    "rnd_expense": ["ResearchAndDevelopmentExpense"],
    "sga_expense": [
        "SellingGeneralAndAdministrativeExpense",
        "GeneralAndAdministrativeExpense",
    ],
    "assets": ["Assets"],
    "liabilities": ["Liabilities"],
    "equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "cash": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ],
    "long_term_debt": ["LongTermDebtNoncurrent", "LongTermDebt"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
    ],
    "dividends_paid": ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends"],
    "buybacks": ["PaymentsForRepurchaseOfCommonStock"],
    "shares_diluted": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
    "income_tax": ["IncomeTaxExpenseBenefit"],
    "inventory": ["InventoryNet"],
}

# What the user is likely to *say* -> our metric key.
ALIASES: dict[str, str] = {
    "revenue": "revenue",
    "revenues": "revenue",
    "net sales": "revenue",
    "sales": "revenue",
    "topline": "revenue",
    "top line": "revenue",
    "net income": "net_income",
    "profit": "net_income",
    "earnings": "net_income",
    "bottom line": "net_income",
    "gross profit": "gross_profit",
    # "margin" means a RATIO. Mapping it to the dollar figure returned Apple's gross
    # margin as "$195,201,000,000", which is gross profit — a confidently wrong answer
    # to the question actually asked.
    "gross margin": "gross_margin_pct",
    "operating income": "operating_income",
    "operating profit": "operating_income",
    "operating margin": "operating_margin_pct",
    "net margin": "net_margin_pct",
    "profit margin": "net_margin_pct",
    "margin": "gross_margin_pct",
    "free cash flow": "free_cash_flow",
    "fcf": "free_cash_flow",
    "eps": "eps_diluted",
    "earnings per share": "eps_diluted",
    "r&d": "rnd_expense",
    "research and development": "rnd_expense",
    "sg&a": "sga_expense",
    "total assets": "assets",
    "assets": "assets",
    "total liabilities": "liabilities",
    "liabilities": "liabilities",
    "equity": "equity",
    "shareholders equity": "equity",
    "cash": "cash",
    "cash and cash equivalents": "cash",
    "debt": "long_term_debt",
    "long-term debt": "long_term_debt",
    "long term debt": "long_term_debt",
    "operating cash flow": "operating_cash_flow",
    "cash flow from operations": "operating_cash_flow",
    "capex": "capex",
    "capital expenditures": "capex",
    "dividends": "dividends_paid",
    "buyback": "buybacks",
    "buybacks": "buybacks",
    "share repurchase": "buybacks",
    "shares outstanding": "shares_diluted",
    "tax": "income_tax",
    "inventory": "inventory",
}

# Metrics we derive rather than read straight off a tag.
DERIVED: dict[str, tuple[str, str]] = {
    "gross_margin_pct": ("gross_profit", "revenue"),
    "operating_margin_pct": ("operating_income", "revenue"),
    "net_margin_pct": ("net_income", "revenue"),
    "free_cash_flow": ("operating_cash_flow", "capex"),  # subtraction, not a ratio
}


def match_metric(query: str) -> str | None:
    """The metric a question is asking for, if any. Longest alias wins."""
    low = query.lower()
    hit: str | None = None
    best = 0
    for alias, metric in ALIASES.items():
        if alias in low and len(alias) > best:
            hit, best = metric, len(alias)
    return hit
