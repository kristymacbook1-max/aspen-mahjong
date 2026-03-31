"""SEC EDGAR 10-K data fetcher for Phase 1 revenue recognition analysis.

Pulls structured financial data from SEC EDGAR XBRL APIs and maps it
to the TenKInput dataclass hierarchy used by the Phase 1 analyzer.
"""

import time
import warnings
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import requests

from ..utils.currency_helpers import to_decimal
from ..utils.date_helpers import parse_date
from .ten_k_analyzer import (
    BalanceSheetData,
    CompanyProfile,
    ContractAssetData,
    DeferredRevenueData,
    IncomeStatementData,
    RevenueStream,
    TenKInput,
)

# ---------------------------------------------------------------------------
# XBRL tag groups -- ordered by preference (first match wins)
# ---------------------------------------------------------------------------

_REVENUE_TAGS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
]

_COGS_TAGS = [
    "CostOfRevenue",
    "CostOfGoodsAndServicesSold",
    "CostOfGoodsSold",
]

_OPERATING_INCOME_TAGS = [
    "OperatingIncomeLoss",
]

_NET_INCOME_TAGS = [
    "NetIncomeLoss",
    "ProfitLoss",
]

_TAX_TAGS = [
    "IncomeTaxExpenseBenefit",
]

_PRETAX_TAGS = [
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
]

_AR_TAGS = [
    "AccountsReceivableNetCurrent",
    "AccountsReceivableNet",
]

_ALLOWANCE_TAGS = [
    "AllowanceForDoubtfulAccountsReceivableCurrent",
]

_TOTAL_ASSETS_TAGS = [
    "Assets",
]

_DEFERRED_REVENUE_TAGS = [
    "ContractWithCustomerLiability",
    "ContractWithCustomerLiabilityCurrent",
    "DeferredRevenue",
    "DeferredRevenueCurrent",
]

_DEFERRED_REVENUE_NONCURRENT_TAGS = [
    "ContractWithCustomerLiabilityNoncurrent",
    "DeferredRevenueNoncurrent",
]

_CONTRACT_ASSET_TAGS = [
    "ContractWithCustomerAssetNet",
    "ContractWithCustomerAssetNetCurrent",
]

# Revenue disaggregation tags -- each maps to a human-readable stream name
_REVENUE_DISAGG_TAGS = {
    "RevenueFromContractWithCustomerExcludingAssessedTax": "Contract Revenue (excl. assessed tax)",
    "RevenueFromContractWithCustomerIncludingAssessedTax": "Contract Revenue (incl. assessed tax)",
    "RevenueFromSubscriptionArrangement": "Subscription Revenue",
    "LicenseRevenue": "License Revenue",
    "MaintenanceRevenue": "Maintenance Revenue",
    "TechnologyServicesRevenue": "Technology Services Revenue",
    "ProductRevenue": "Product Revenue",
    "ServiceRevenue": "Service Revenue",
    "AdvertisingRevenue": "Advertising Revenue",
    "FinancialServicesRevenue": "Financial Services Revenue",
    "RealEstateRevenueNet": "Real Estate Revenue",
}


class EdgarFetcherError(Exception):
    """Raised when an EDGAR API call fails in an unrecoverable way."""


class EdgarFetcher:
    """Fetches 10-K filing data from SEC EDGAR and builds a TenKInput object.

    Uses the publicly-available EDGAR XBRL company-facts API (no API key
    required).  A well-formed ``User-Agent`` header is mandatory per SEC
    policy.

    Parameters
    ----------
    company_identifier:
        A stock ticker (e.g. ``"AAPL"``) or a CIK number (e.g. ``"320193"``).
    user_agent:
        The ``User-Agent`` string sent with every request.  The SEC requires
        a company name and admin email in the format
        ``"CompanyName admin@company.com"``.
    """

    _BASE_SUBMISSIONS = "https://data.sec.gov/submissions"
    _BASE_COMPANYFACTS = "https://data.sec.gov/api/xbrl/companyfacts"
    _SEARCH_INDEX = "https://efts.sec.gov/LATEST/search-index"
    _RATE_LIMIT_SECONDS = 0.1

    def __init__(
        self,
        company_identifier: str,
        user_agent: str = "FinancialTools admin@example.com",
    ) -> None:
        self._identifier = company_identifier.strip()
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": user_agent,
            "Accept": "application/json",
        })

        # Resolved lazily
        self._cik: Optional[str] = None
        self._cik_padded: Optional[str] = None
        self._company_data: Optional[Dict[str, Any]] = None
        self._facts: Optional[Dict[str, Any]] = None
        self._last_request_time: float = 0.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _throttle(self) -> None:
        """Respect SEC rate-limiting by ensuring >= 0.1 s between requests."""
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self._RATE_LIMIT_SECONDS:
            time.sleep(self._RATE_LIMIT_SECONDS - elapsed)

    def _get(self, url: str) -> Dict[str, Any]:
        """Issue a throttled GET and return the JSON payload."""
        self._throttle()
        resp = self._session.get(url, timeout=30)
        self._last_request_time = time.monotonic()
        if resp.status_code != 200:
            raise EdgarFetcherError(
                f"EDGAR returned HTTP {resp.status_code} for {url}"
            )
        return resp.json()

    def _resolve_cik(self) -> str:
        """Resolve the company identifier to a zero-padded CIK string."""
        if self._cik_padded is not None:
            return self._cik_padded

        identifier = self._identifier

        # If the identifier is purely numeric, treat it as a CIK directly.
        if identifier.isdigit():
            self._cik = identifier
            self._cik_padded = identifier.zfill(10)
            return self._cik_padded

        # Otherwise treat it as a ticker and look it up via the company
        # tickers JSON file that EDGAR publishes.
        url = "https://www.sec.gov/files/company_tickers.json"
        data = self._get(url)

        ticker_upper = identifier.upper()
        for entry in data.values():
            if entry.get("ticker", "").upper() == ticker_upper:
                self._cik = str(entry["cik_str"])
                self._cik_padded = self._cik.zfill(10)
                return self._cik_padded

        raise EdgarFetcherError(
            f"Could not resolve ticker '{identifier}' to a CIK via EDGAR."
        )

    def _ensure_company_data(self) -> Dict[str, Any]:
        """Fetch and cache the full company submission metadata."""
        if self._company_data is not None:
            return self._company_data
        cik_padded = self._resolve_cik()
        url = f"{self._BASE_SUBMISSIONS}/CIK{cik_padded}.json"
        self._company_data = self._get(url)
        return self._company_data

    def _ensure_facts(self) -> Dict[str, Any]:
        """Fetch and cache the full XBRL company-facts payload."""
        if self._facts is not None:
            return self._facts
        cik_padded = self._resolve_cik()
        url = f"{self._BASE_COMPANYFACTS}/CIK{cik_padded}.json"
        self._facts = self._get(url)
        return self._facts

    def _get_us_gaap_facts(self) -> Dict[str, Any]:
        """Return the us-gaap namespace from the company-facts payload."""
        facts = self._ensure_facts()
        return facts.get("facts", {}).get("us-gaap", {})

    # ------------------------------------------------------------------
    # XBRL value extraction
    # ------------------------------------------------------------------

    def _fiscal_year_end_month(self) -> int:
        """Return the company's fiscal-year-end month (1-12)."""
        data = self._ensure_company_data()
        fye = data.get("fiscalYearEnd", "1231")
        # EDGAR stores this as a 4-char MMDD string.
        try:
            return int(fye[:2])
        except (ValueError, TypeError):
            return 12

    def _fy_end_date(self, fiscal_year: int) -> date:
        """Build the expected fiscal-year-end date for *fiscal_year*."""
        import calendar

        month = self._fiscal_year_end_month()
        last_day = calendar.monthrange(fiscal_year, month)[1]
        return date(fiscal_year, month, last_day)

    def _extract_annual_value(
        self,
        tag: str,
        target_fy_end: date,
        us_gaap: Dict[str, Any],
    ) -> Optional[Decimal]:
        """Extract the annual (10-K / FY) value for *tag* whose period ends
        on or near *target_fy_end*.

        Returns ``None`` if no suitable fact is found.
        """
        tag_data = us_gaap.get(tag)
        if tag_data is None:
            return None

        units_map = tag_data.get("units", {})
        # Financial values are typically in USD; fall back to first unit key.
        facts_list: List[Dict[str, Any]] = []
        for unit_key in ("USD", "USD/shares"):
            if unit_key in units_map:
                facts_list = units_map[unit_key]
                break
        if not facts_list:
            # Grab the first available unit.
            for v in units_map.values():
                facts_list = v
                break

        if not facts_list:
            return None

        # Filter to annual 10-K facts, then find the one whose period end
        # is closest to target_fy_end.
        annual_facts = [
            f for f in facts_list
            if f.get("form") == "10-K" or f.get("fp") == "FY"
        ]

        # If nothing explicitly tagged 10-K/FY, fall back to all facts that
        # look like annual periods (duration >= 350 days or instant).
        if not annual_facts:
            annual_facts = facts_list

        best: Optional[Dict[str, Any]] = None
        best_distance: int = 9999

        for fact in annual_facts:
            end_str = fact.get("end")
            if end_str is None:
                continue
            end_date = parse_date(end_str)
            if end_date is None:
                continue
            distance = abs((end_date - target_fy_end).days)
            # Allow up to ~5 days tolerance for slight date variations.
            if distance < best_distance and distance <= 5:
                best_distance = distance
                best = fact

        if best is None:
            return None

        return to_decimal(best.get("val"))

    def _first_match(
        self,
        tags: List[str],
        target_fy_end: date,
        us_gaap: Dict[str, Any],
    ) -> Decimal:
        """Try each tag in order and return the first non-None value."""
        for tag in tags:
            val = self._extract_annual_value(tag, target_fy_end, us_gaap)
            if val is not None:
                return val
        tag_names = ", ".join(tags)
        warnings.warn(
            f"No XBRL data found for tags [{tag_names}] near {target_fy_end}. "
            "Defaulting to 0.",
            stacklevel=2,
        )
        return Decimal("0")

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def fetch_company_info(self) -> CompanyProfile:
        """Fetch basic company information from EDGAR submissions API.

        Returns a populated :class:`CompanyProfile`.
        """
        data = self._ensure_company_data()
        fye_month = self._fiscal_year_end_month()

        # Extract ticker -- may be a list or a single value.
        tickers = data.get("tickers", [])
        ticker: Optional[str] = None
        if isinstance(tickers, list) and tickers:
            ticker = tickers[0]
        elif isinstance(tickers, str) and tickers:
            ticker = tickers

        # If we were initialised with a ticker, prefer that.
        if not ticker and not self._identifier.isdigit():
            ticker = self._identifier.upper()

        return CompanyProfile(
            name=data.get("name", data.get("entityName", "")),
            ticker=ticker,
            cik=self._cik,
            sic_code=data.get("sic", None),
            industry=data.get("sicDescription", ""),
            fiscal_year_end_month=fye_month,
            filing_date=None,  # Could be extracted from recent filings list
            reporting_currency="USD",
        )

    def fetch_financials(
        self, fiscal_year: Optional[int] = None
    ) -> Tuple[IncomeStatementData, BalanceSheetData]:
        """Pull income-statement and balance-sheet line items from XBRL.

        Parameters
        ----------
        fiscal_year:
            The target fiscal year.  If ``None``, uses the most recent
            calendar year minus one (a reasonable proxy for the latest
            annual filing).

        Returns
        -------
        tuple of (IncomeStatementData, BalanceSheetData)
        """
        us_gaap = self._get_us_gaap_facts()

        if fiscal_year is None:
            fiscal_year = date.today().year - 1

        fy_end = self._fy_end_date(fiscal_year)
        fy_end_prior = self._fy_end_date(fiscal_year - 1)
        fy_end_two_prior = self._fy_end_date(fiscal_year - 2)

        def _get(tags: List[str], fy: date) -> Decimal:
            return self._first_match(tags, fy, us_gaap)

        income = IncomeStatementData(
            total_revenue_current=_get(_REVENUE_TAGS, fy_end),
            total_revenue_prior=_get(_REVENUE_TAGS, fy_end_prior),
            total_revenue_two_years_prior=_get(_REVENUE_TAGS, fy_end_two_prior),
            cost_of_revenue_current=_get(_COGS_TAGS, fy_end),
            cost_of_revenue_prior=_get(_COGS_TAGS, fy_end_prior),
            operating_income_current=_get(_OPERATING_INCOME_TAGS, fy_end),
            operating_income_prior=_get(_OPERATING_INCOME_TAGS, fy_end_prior),
            net_income_current=_get(_NET_INCOME_TAGS, fy_end),
            net_income_prior=_get(_NET_INCOME_TAGS, fy_end_prior),
            income_tax_expense_current=_get(_TAX_TAGS, fy_end),
            income_tax_expense_prior=_get(_TAX_TAGS, fy_end_prior),
            pretax_income_current=_get(_PRETAX_TAGS, fy_end),
            pretax_income_prior=_get(_PRETAX_TAGS, fy_end_prior),
        )

        balance = BalanceSheetData(
            accounts_receivable_current=_get(_AR_TAGS, fy_end),
            accounts_receivable_prior=_get(_AR_TAGS, fy_end_prior),
            allowance_for_doubtful_current=_get(_ALLOWANCE_TAGS, fy_end),
            allowance_for_doubtful_prior=_get(_ALLOWANCE_TAGS, fy_end_prior),
            total_assets_current=_get(_TOTAL_ASSETS_TAGS, fy_end),
            total_assets_prior=_get(_TOTAL_ASSETS_TAGS, fy_end_prior),
        )

        return income, balance

    def fetch_revenue_disaggregation(
        self, fiscal_year: Optional[int] = None
    ) -> List[RevenueStream]:
        """Attempt to extract revenue stream breakdowns from XBRL tags.

        XBRL disaggregation detail varies widely across filers.  This
        method looks for common revenue-category tags and returns whatever
        it finds.  Returns an empty list when no disaggregation data is
        available.

        Parameters
        ----------
        fiscal_year:
            Target fiscal year; defaults to last calendar year.
        """
        us_gaap = self._get_us_gaap_facts()

        if fiscal_year is None:
            fiscal_year = date.today().year - 1

        fy_end = self._fy_end_date(fiscal_year)
        fy_end_prior = self._fy_end_date(fiscal_year - 1)

        streams: List[RevenueStream] = []
        for tag, label in _REVENUE_DISAGG_TAGS.items():
            current_val = self._extract_annual_value(tag, fy_end, us_gaap)
            if current_val is None or current_val == Decimal("0"):
                continue
            prior_val = self._extract_annual_value(tag, fy_end_prior, us_gaap)
            if prior_val is None:
                prior_val = Decimal("0")

            streams.append(
                RevenueStream(
                    name=label,
                    description=f"Extracted from XBRL tag: {tag}",
                    amount_current=current_val,
                    amount_prior=prior_val,
                    notes="Auto-populated from EDGAR XBRL data.",
                )
            )

        if not streams:
            warnings.warn(
                "No revenue disaggregation data found in XBRL. "
                "Manual entry may be required.",
                stacklevel=2,
            )

        return streams

    def fetch_deferred_revenue(
        self, fiscal_year: Optional[int] = None
    ) -> DeferredRevenueData:
        """Extract deferred revenue / contract liability data from XBRL.

        Parameters
        ----------
        fiscal_year:
            Target fiscal year; defaults to last calendar year.
        """
        us_gaap = self._get_us_gaap_facts()

        if fiscal_year is None:
            fiscal_year = date.today().year - 1

        fy_end = self._fy_end_date(fiscal_year)
        fy_end_prior = self._fy_end_date(fiscal_year - 1)

        current_balance = self._first_match(
            _DEFERRED_REVENUE_TAGS, fy_end, us_gaap
        )
        prior_balance = self._first_match(
            _DEFERRED_REVENUE_TAGS, fy_end_prior, us_gaap
        )

        # Try to split current vs. noncurrent portions
        current_portion = Decimal("0")
        noncurrent_portion = Decimal("0")

        # Check if the total came from a "current" specific tag
        for tag in ("ContractWithCustomerLiabilityCurrent", "DeferredRevenueCurrent"):
            val = self._extract_annual_value(tag, fy_end, us_gaap)
            if val is not None and val != Decimal("0"):
                current_portion = val
                break

        for tag in _DEFERRED_REVENUE_NONCURRENT_TAGS:
            val = self._extract_annual_value(tag, fy_end, us_gaap)
            if val is not None and val != Decimal("0"):
                noncurrent_portion = val
                break

        # If we found separate current + noncurrent but no combined total,
        # derive the total.  Otherwise trust what we already have.
        if current_balance == Decimal("0") and (
            current_portion != Decimal("0") or noncurrent_portion != Decimal("0")
        ):
            current_balance = current_portion + noncurrent_portion

        return DeferredRevenueData(
            current_balance=current_balance,
            prior_balance=prior_balance,
            current_portion=current_portion,
            noncurrent_portion=noncurrent_portion,
            notes="Auto-populated from EDGAR XBRL data.",
        )

    def fetch_contract_assets(
        self, fiscal_year: Optional[int] = None
    ) -> ContractAssetData:
        """Extract contract asset / unbilled receivable data from XBRL.

        Parameters
        ----------
        fiscal_year:
            Target fiscal year; defaults to last calendar year.
        """
        us_gaap = self._get_us_gaap_facts()

        if fiscal_year is None:
            fiscal_year = date.today().year - 1

        fy_end = self._fy_end_date(fiscal_year)
        fy_end_prior = self._fy_end_date(fiscal_year - 1)

        current_balance = self._first_match(
            _CONTRACT_ASSET_TAGS, fy_end, us_gaap
        )
        prior_balance = self._first_match(
            _CONTRACT_ASSET_TAGS, fy_end_prior, us_gaap
        )

        return ContractAssetData(
            current_balance=current_balance,
            prior_balance=prior_balance,
            notes="Auto-populated from EDGAR XBRL data.",
        )

    def build_phase1_input(
        self, fiscal_year: Optional[int] = None
    ) -> TenKInput:
        """Orchestrate all fetches and return a fully-populated TenKInput.

        This is the primary entry point: call this method and pass the
        result to :class:`TenKAnalyzer` for analysis.

        Parameters
        ----------
        fiscal_year:
            The fiscal year to pull data for.  Defaults to the most recent
            completed calendar year.

        Returns
        -------
        TenKInput
            Populated with whatever data EDGAR XBRL provides.  Fields that
            cannot be derived from structured XBRL data (e.g. narrative
            disclosures, auditor opinions) are left at their defaults and
            should be filled in manually.
        """
        if fiscal_year is None:
            fiscal_year = date.today().year - 1

        company = self.fetch_company_info()
        income_statement, balance_sheet = self.fetch_financials(fiscal_year)
        revenue_streams = self.fetch_revenue_disaggregation(fiscal_year)
        deferred_revenue = self.fetch_deferred_revenue(fiscal_year)
        contract_assets = self.fetch_contract_assets(fiscal_year)

        return TenKInput(
            company=company,
            revenue_streams=revenue_streams,
            deferred_revenue=deferred_revenue,
            contract_assets=contract_assets,
            income_statement=income_statement,
            balance_sheet=balance_sheet,
        )
