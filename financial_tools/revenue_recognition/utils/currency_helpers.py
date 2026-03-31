"""Currency and financial calculation helpers."""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation


def to_decimal(value):
    """Safely convert a value to Decimal."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        cleaned = str(value).replace(",", "").replace("$", "").strip()
        if cleaned == "" or cleaned == "-":
            return Decimal("0")
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return Decimal("0")


def round_currency(value, places=2):
    """Round a Decimal to currency precision."""
    d = to_decimal(value)
    quantize_str = "0." + "0" * places
    return d.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)


def format_currency(value, symbol="$"):
    """Format a number as a currency string."""
    d = round_currency(value)
    if d < 0:
        return f"({symbol}{abs(d):,.2f})"
    return f"{symbol}{d:,.2f}"


def format_millions(value, symbol="$"):
    """Format a number in millions (e.g., $1.2M)."""
    d = to_decimal(value)
    millions = d / Decimal("1000000")
    rounded = millions.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    if d < 0:
        return f"({symbol}{abs(rounded)}M)"
    return f"{symbol}{rounded}M"


def format_thousands(value, symbol="$"):
    """Format a number in thousands (e.g., $1,200K)."""
    d = to_decimal(value)
    thousands = d / Decimal("1000")
    rounded = thousands.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    if d < 0:
        return f"({symbol}{abs(rounded)}K)"
    return f"{symbol}{rounded}K"


def pct_change(current, prior):
    """Calculate percentage change between two values."""
    current_d = to_decimal(current)
    prior_d = to_decimal(prior)
    if prior_d == 0:
        return None
    return float((current_d - prior_d) / abs(prior_d))


def pct_of_total(part, total):
    """Calculate a value as a percentage of total."""
    part_d = to_decimal(part)
    total_d = to_decimal(total)
    if total_d == 0:
        return None
    return float(part_d / total_d)


def variance(actual, expected):
    """Calculate the variance between actual and expected."""
    return to_decimal(actual) - to_decimal(expected)


def effective_tax_rate(tax_expense, pretax_income):
    """Calculate effective tax rate."""
    tax_d = to_decimal(tax_expense)
    income_d = to_decimal(pretax_income)
    if income_d == 0:
        return None
    return float(tax_d / income_d)
