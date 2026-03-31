"""Date and fiscal period helper functions."""

from datetime import datetime, date, timedelta
from typing import List, Tuple, Optional


def parse_date(value):
    """Parse a date from various formats."""
    if isinstance(value, (datetime, date)):
        return value if isinstance(value, date) else value.date()
    if value is None:
        return None
    formats = ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y/%m/%d", "%d-%b-%Y", "%b %d, %Y"]
    for fmt in formats:
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    return None


def fiscal_year_end_dates(fiscal_year_end_month: int, years: List[int]) -> List[date]:
    """Get fiscal year end dates for given years.

    Args:
        fiscal_year_end_month: Month number (1-12) of fiscal year end.
        years: Calendar years to generate FY end dates for.

    Returns:
        List of fiscal year end dates.
    """
    results = []
    for year in years:
        if fiscal_year_end_month == 12:
            results.append(date(year, 12, 31))
        else:
            # FY ends in the given month of the next calendar year
            import calendar
            last_day = calendar.monthrange(year + 1, fiscal_year_end_month)[1]
            results.append(date(year + 1, fiscal_year_end_month, last_day))
    return results


def quarter_end_dates(fiscal_year_end_month: int, year: int) -> List[date]:
    """Get quarter-end dates for a fiscal year.

    Args:
        fiscal_year_end_month: Month number (1-12) of fiscal year end.
        year: The fiscal year.

    Returns:
        List of 4 quarter-end dates.
    """
    import calendar
    quarters = []
    for q in range(1, 5):
        month = (fiscal_year_end_month - 12 + q * 3) % 12
        if month == 0:
            month = 12
        q_year = year if month <= fiscal_year_end_month else year - 1
        if fiscal_year_end_month < 12 and month > fiscal_year_end_month:
            q_year = year
        else:
            q_year = year if month <= fiscal_year_end_month else year + 1
        last_day = calendar.monthrange(q_year, month)[1]
        quarters.append(date(q_year, month, last_day))
    return quarters


def period_label(period_end: date, frequency: str = "annual") -> str:
    """Generate a human-readable period label.

    Args:
        period_end: End date of the period.
        frequency: 'annual', 'quarterly', or 'monthly'.
    """
    if frequency == "annual":
        return f"FY {period_end.year}"
    elif frequency == "quarterly":
        month = period_end.month
        quarter = (month - 1) // 3 + 1
        return f"Q{quarter} {period_end.year}"
    elif frequency == "monthly":
        return period_end.strftime("%b %Y")
    return str(period_end)


def years_between(start: date, end: date) -> int:
    """Calculate full years between two dates."""
    return end.year - start.year - ((end.month, end.day) < (start.month, start.day))


def months_between(start: date, end: date) -> int:
    """Calculate months between two dates."""
    return (end.year - start.year) * 12 + end.month - start.month
