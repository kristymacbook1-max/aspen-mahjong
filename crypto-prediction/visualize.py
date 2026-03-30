"""
ASCII-based visualization and report generation for crypto price predictions.
No external dependencies required — pure Python implementation.
"""

from typing import List, Dict
from prediction_models import PricePrediction, get_all_predictions, composite_prediction
from market_data import (
    get_market_summary, BTC_CURRENT, ETH_CURRENT,
    HALVING_EVENTS, HALVING_CYCLE_RETURNS, BTC_HISTORICAL_MONTHLY, ETH_HISTORICAL_MONTHLY
)


def format_price(price: float) -> str:
    """Format price with appropriate precision."""
    if price >= 1_000_000:
        return f"${price / 1_000_000:.2f}M"
    elif price >= 1_000:
        return f"${price:,.0f}"
    else:
        return f"${price:,.2f}"


def ascii_bar_chart(
    predictions: List[PricePrediction],
    width: int = 50,
    title: str = "",
) -> str:
    """Render an ASCII bar chart for predictions across years."""
    if not predictions:
        return "No data."

    max_price = max(p.high for p in predictions)
    scale = width / max_price if max_price > 0 else 1

    lines = []
    if title:
        lines.append(f"\n  {title}")
        lines.append("  " + "─" * (width + 25))

    for p in predictions:
        low_pos = int(p.low * scale)
        mid_pos = int(p.mid * scale)
        high_pos = int(p.high * scale)

        bar = list(" " * (width + 1))

        # Fill low-to-high range
        for i in range(low_pos, min(high_pos + 1, width + 1)):
            bar[i] = "░"

        # Fill low-to-mid range darker
        for i in range(low_pos, min(mid_pos + 1, width + 1)):
            bar[i] = "▓"

        # Mark midpoint
        if mid_pos <= width:
            bar[mid_pos] = "█"

        bar_str = "".join(bar)
        lines.append(
            f"  {p.year} │{bar_str}│ {format_price(p.low)} — {format_price(p.mid)} — {format_price(p.high)}"
        )

    lines.append("")
    lines.append(f"  Legend: ▓ Low→Mid  ░ Mid→High  █ Midpoint    Scale: each char ≈ {format_price(max_price / width)}")
    return "\n".join(lines)


def comparison_table(
    all_models: Dict[str, List[PricePrediction]],
    years: List[int],
    asset: str,
) -> str:
    """Render a comparison table of all models' mid predictions."""
    lines = []
    lines.append(f"\n  {asset} — Model Comparison (Mid-Point Predictions)")
    lines.append("  " + "═" * 95)

    # Header
    header = f"  {'Model':<30}"
    for y in years:
        header += f"│ {y:>10} "
    header += f"│ {'5yr CAGR':>8}"
    lines.append(header)
    lines.append("  " + "─" * 95)

    current = BTC_CURRENT.price_usd if asset == "BTC" else ETH_CURRENT.price_usd

    for model_name, preds in all_models.items():
        row = f"  {model_name:<30}"
        last_mid = current
        for y in years:
            pred = next((p for p in preds if p.year == y), None)
            if pred:
                row += f"│ {format_price(pred.mid):>10} "
                last_mid = pred.mid
            else:
                row += f"│ {'N/A':>10} "

        # CAGR
        if last_mid > 0 and current > 0:
            cagr = (last_mid / current) ** (1 / 5) - 1
            row += f"│ {cagr:>7.1%}"
        else:
            row += f"│ {'N/A':>8}"

        lines.append(row)

    lines.append("  " + "═" * 95)
    return "\n".join(lines)


def risk_analysis(asset: str) -> str:
    """Generate risk factors and scenario analysis."""
    lines = []
    lines.append(f"\n  ╔{'═' * 72}╗")
    lines.append(f"  ║{'RISK ANALYSIS & KEY FACTORS — ' + asset:^72}║")
    lines.append(f"  ╠{'═' * 72}╣")

    if asset == "BTC":
        risks = [
            ("BULLISH CATALYSTS", [
                "Next halving (April 2028) reduces new supply by 50%",
                "Institutional adoption via spot ETFs continues expanding",
                "Potential US strategic Bitcoin reserve policy",
                "Global de-dollarization trends favor neutral assets",
                "Corporate treasury adoption (MicroStrategy model)",
                "Inflation hedging narrative strengthens",
            ]),
            ("BEARISH RISKS", [
                "Regulatory crackdowns (global coordination risk)",
                "Quantum computing threats to cryptographic security",
                "Mining centralization and energy concerns",
                "Macro recession reduces risk appetite",
                "ETF outflow acceleration during downturns",
                "Competition from CBDCs and stablecoins",
                "Diminishing returns pattern — each cycle peaks lower",
            ]),
            ("MACRO FACTORS", [
                "Federal Reserve rate policy and liquidity cycle",
                "US dollar strength (DXY) inversely correlated",
                "Geopolitical tensions (flight to safety vs risk-off)",
                "Global M2 money supply correlation",
                "Correlation with tech/growth equities",
            ]),
        ]
    else:
        risks = [
            ("BULLISH CATALYSTS", [
                "DeFi & smart contract ecosystem dominance",
                "Layer 2 scaling (Arbitrum, Optimism, Base) adoption",
                "Deflationary tokenomics via EIP-1559 burn",
                "3-5% native staking yield attracts capital",
                "Institutional DeFi and tokenized real-world assets",
                "Potential spot ETH ETF expansion globally",
            ]),
            ("BEARISH RISKS", [
                "Layer 1 competition (Solana, Avalanche, etc.)",
                "Vitalik Buterin token sales signal concerns",
                "Regulatory classification as security risk",
                "Gas fee competition from alternative chains",
                "ETH/BTC ratio at historic lows (~0.031)",
                "Complexity of upgrades can introduce vulnerabilities",
            ]),
            ("ETH-SPECIFIC METRICS", [
                "ETH/BTC ratio recovery is critical (currently 0.031)",
                "Total Value Locked (TVL) in DeFi as adoption proxy",
                "Network revenue from L2 blob fees",
                "Staking participation rate (~28% of supply)",
                "Net ETH issuance (deflationary in high-usage periods)",
            ]),
        ]

    for category, items in risks:
        lines.append(f"  ║                                                                        ║")
        lines.append(f"  ║  {category:<70}║")
        lines.append(f"  ║  {'─' * 70}║")
        for item in items:
            lines.append(f"  ║    • {item:<67}║")

    lines.append(f"  ║                                                                        ║")
    lines.append(f"  ╚{'═' * 72}╝")
    return "\n".join(lines)


def scenario_analysis(asset: str) -> str:
    """Generate bull/base/bear scenario narratives."""
    current = BTC_CURRENT.price_usd if asset == "BTC" else ETH_CURRENT.price_usd

    if asset == "BTC":
        scenarios = {
            "BEAR CASE (10th percentile)": {
                "2031_price": 85_000,
                "narrative": (
                    "Regulatory clampdown, ETF outflows, recession. BTC remains range-bound "
                    "between $60K-$100K. Diminishing halving returns continue. Crypto winter "
                    "extends as macro headwinds persist."
                ),
                "cagr": (85_000 / current) ** (1 / 5) - 1,
            },
            "BASE CASE (50th percentile)": {
                "2031_price": 180_000,
                "narrative": (
                    "Moderate institutional growth, halving cycle plays out with diminished "
                    "returns. ETF inflows stabilize. BTC acts as digital gold for ~2-5% of "
                    "portfolios. Reaches $200K+ in 2028-2029 cycle, corrects to ~$180K."
                ),
                "cagr": (180_000 / current) ** (1 / 5) - 1,
            },
            "BULL CASE (90th percentile)": {
                "2031_price": 450_000,
                "narrative": (
                    "Massive institutional adoption, sovereign wealth fund allocation, "
                    "favorable regulation globally. Strategic reserve policies in multiple "
                    "countries. 2028 halving drives supply shock with strong demand."
                ),
                "cagr": (450_000 / current) ** (1 / 5) - 1,
            },
        }
    else:
        scenarios = {
            "BEAR CASE (10th percentile)": {
                "2031_price": 2_500,
                "narrative": (
                    "L1 competition erodes market share. Regulatory uncertainty. ETH/BTC "
                    "ratio remains depressed. DeFi growth stalls. Price range-bound near "
                    "current levels."
                ),
                "cagr": (2_500 / current) ** (1 / 5) - 1,
            },
            "BASE CASE (50th percentile)": {
                "2031_price": 8_500,
                "narrative": (
                    "Ethereum maintains smart contract dominance. L2 ecosystem grows. "
                    "Institutional DeFi adoption drives demand. Staking yield attracts "
                    "capital. ETH/BTC ratio recovers to ~0.045-0.050."
                ),
                "cagr": (8_500 / current) ** (1 / 5) - 1,
            },
            "BULL CASE (90th percentile)": {
                "2031_price": 18_000,
                "narrative": (
                    "ETH becomes settlement layer for tokenized global finance. RWA "
                    "tokenization explodes. ETH/BTC ratio recovers to 0.06+. Deflationary "
                    "supply dynamics + staking demand creates supply squeeze."
                ),
                "cagr": (18_000 / current) ** (1 / 5) - 1,
            },
        }

    lines = []
    lines.append(f"\n  ┌{'─' * 72}┐")
    lines.append(f"  │{'SCENARIO ANALYSIS — ' + asset + ' — 5-Year Outlook':^72}│")
    lines.append(f"  │{'Current Price: ' + format_price(current):^72}│")
    lines.append(f"  ├{'─' * 72}┤")

    for name, data in scenarios.items():
        lines.append(f"  │                                                                        │")
        lines.append(f"  │  {name:<70}│")
        lines.append(f"  │  Target (2031): {format_price(data['2031_price']):<20} CAGR: {data['cagr']:>+.1%}{' ' * 27}│")
        lines.append(f"  │                                                                        │")

        # Word wrap narrative
        narrative = data["narrative"]
        while narrative:
            chunk = narrative[:66]
            if len(narrative) > 66:
                last_space = chunk.rfind(" ")
                if last_space > 0:
                    chunk = narrative[:last_space]
                    narrative = narrative[last_space + 1:]
                else:
                    narrative = narrative[66:]
            else:
                narrative = ""
            lines.append(f"  │    {chunk:<68}│")

        lines.append(f"  │                                                                        │")
        lines.append(f"  ├{'─' * 72}┤")

    # Remove last separator and close
    lines[-1] = f"  └{'─' * 72}┘"
    return "\n".join(lines)


def investment_return_table(asset: str, years: List[int]) -> str:
    """Show potential returns on a $10,000 investment."""
    composite = composite_prediction(asset, years)
    current = BTC_CURRENT.price_usd if asset == "BTC" else ETH_CURRENT.price_usd
    investment = 10_000

    lines = []
    lines.append(f"\n  {asset} — Potential Returns on $10,000 Investment (from {format_price(current)})")
    lines.append("  " + "═" * 75)
    lines.append(f"  {'Year':<8}{'Bear':>12}{'Base':>12}{'Bull':>12}{'Bear ROI':>12}{'Base ROI':>12}{'Bull ROI':>12}")
    lines.append("  " + "─" * 75)

    for pred in composite:
        bear_val = investment * (pred.low / current)
        base_val = investment * (pred.mid / current)
        bull_val = investment * (pred.high / current)

        bear_roi = (pred.low / current - 1) * 100
        base_roi = (pred.mid / current - 1) * 100
        bull_roi = (pred.high / current - 1) * 100

        lines.append(
            f"  {pred.year:<8}"
            f"{format_price(bear_val):>12}"
            f"{format_price(base_val):>12}"
            f"{format_price(bull_val):>12}"
            f"{'%+.0f%%' % bear_roi:>12}"
            f"{'%+.0f%%' % base_roi:>12}"
            f"{'%+.0f%%' % bull_roi:>12}"
        )

    lines.append("  " + "═" * 75)
    return "\n".join(lines)


def full_report() -> str:
    """Generate the complete prediction report."""
    years = [2026, 2027, 2028, 2029, 2030, 2031]
    sections = []

    # Header
    sections.append("=" * 80)
    sections.append("  CRYPTOCURRENCY PRICE PREDICTION MODEL")
    sections.append("  BTC & ETH — 5-Year Forecast (2026–2031)")
    sections.append("  Generated: March 30, 2026")
    sections.append("=" * 80)

    # Market snapshot
    sections.append(get_market_summary())

    # BTC Analysis
    sections.append("\n" + "█" * 80)
    sections.append("  BITCOIN (BTC) PREDICTIONS")
    sections.append("█" * 80)

    btc_all = get_all_predictions("BTC", years)
    btc_composite = btc_all["Composite Ensemble"]

    sections.append(ascii_bar_chart(btc_composite, title="BTC Composite Forecast (2026–2031)"))
    sections.append(comparison_table(btc_all, years, "BTC"))
    sections.append(risk_analysis("BTC"))
    sections.append(scenario_analysis("BTC"))
    sections.append(investment_return_table("BTC", years))

    # ETH Analysis
    sections.append("\n" + "█" * 80)
    sections.append("  ETHEREUM (ETH) PREDICTIONS")
    sections.append("█" * 80)

    eth_all = get_all_predictions("ETH", years)
    eth_composite = eth_all["Composite Ensemble"]

    sections.append(ascii_bar_chart(eth_composite, title="ETH Composite Forecast (2026–2031)"))
    sections.append(comparison_table(eth_all, years, "ETH"))
    sections.append(risk_analysis("ETH"))
    sections.append(scenario_analysis("ETH"))
    sections.append(investment_return_table("ETH", years))

    # Methodology
    sections.append("\n" + "=" * 80)
    sections.append("  METHODOLOGY & DISCLAIMERS")
    sections.append("=" * 80)
    sections.append("""
  This prediction model uses an ensemble of 5-6 independent models:

  1. LOG-LINEAR REGRESSION — Fits ln(price) ~ time to historical monthly data.
     Simple trend extrapolation with volatility bands. R² varies by asset.

  2. HALVING CYCLE MODEL (BTC only) — Based on the observation that BTC follows
     ~4-year cycles tied to block reward halvings. Each cycle shows diminishing
     peak multiples: 96x → 30x → 8x → 2x. Projects cycle 5 accordingly.

  3. MONTE CARLO SIMULATION — 50,000 paths using geometric Brownian motion
     (GBM) with drift and volatility estimated from historical data. Applies
     dampening (0.45x historical drift) to account for market maturation.

  4. STOCK-TO-FLOW (BTC only) — Scarcity model relating price to the ratio
     of existing supply to new issuance. Adjusted with a correction factor
     as the original PlanB model has overestimated by 60-70% in cycle 4.

  5. ANALYST CONSENSUS — Weighted average of forecasts from Standard Chartered,
     Pantera Capital, Ark Invest, Changelly, Coinpedia, Cryptopolitan, and others.

  6. ETH/BTC RATIO MODEL (ETH only) — Projects ETH price by applying expected
     ETH/BTC ratio recovery to BTC composite predictions.

  COMPOSITE: Weighted blend — Monte Carlo (25%), Analyst Consensus (30%),
  Halving Cycle (20% BTC), Log-Linear (15-20%), S2F (10% BTC), Ratio (25% ETH).

  ⚠ DISCLAIMER: This is a mathematical modeling exercise, NOT financial advice.
  Cryptocurrency markets are highly volatile and unpredictable. Past performance
  does not guarantee future results. All models have significant limitations
  and wide uncertainty bands. Never invest more than you can afford to lose.
""")

    return "\n".join(sections)
