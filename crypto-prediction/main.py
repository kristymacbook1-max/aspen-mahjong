#!/usr/bin/env python3
"""
Crypto Price Prediction Model — BTC & ETH 5-Year Forecast (2026–2031)

Run: python3 main.py [--json] [--asset BTC|ETH] [--year 2028]

Generates comprehensive price predictions using an ensemble of models:
- Log-Linear Regression
- Halving Cycle (BTC)
- Monte Carlo Simulation (50K paths)
- Stock-to-Flow (BTC)
- Analyst Consensus
- ETH/BTC Ratio (ETH)
"""

import sys
import json
import os

# Add the script's directory to path so imports work from anywhere
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prediction_models import get_all_predictions, composite_prediction, PricePrediction
from visualize import full_report, format_price
from market_data import BTC_CURRENT, ETH_CURRENT


def to_json(asset: str, years: list) -> str:
    """Export predictions as JSON."""
    all_preds = get_all_predictions(asset, years)

    output = {
        "asset": asset,
        "current_price": BTC_CURRENT.price_usd if asset == "BTC" else ETH_CURRENT.price_usd,
        "snapshot_date": "2026-03-30",
        "models": {},
    }

    for model_name, preds in all_preds.items():
        output["models"][model_name] = [
            {
                "year": p.year,
                "low": round(p.low, 2),
                "mid": round(p.mid, 2),
                "high": round(p.high, 2),
            }
            for p in preds
        ]

    return json.dumps(output, indent=2)


def quick_summary():
    """Print a concise summary of composite predictions."""
    years = [2026, 2027, 2028, 2029, 2030, 2031]

    print("\n  Quick Summary — Composite Ensemble Predictions")
    print("  " + "=" * 65)

    for asset in ["BTC", "ETH"]:
        current = BTC_CURRENT.price_usd if asset == "BTC" else ETH_CURRENT.price_usd
        preds = composite_prediction(asset, years)
        print(f"\n  {asset} (current: {format_price(current)})")
        print(f"  {'Year':<8}{'Bear (10%)':>14}{'Base (50%)':>14}{'Bull (90%)':>14}")
        print("  " + "─" * 50)
        for p in preds:
            print(f"  {p.year:<8}{format_price(p.low):>14}{format_price(p.mid):>14}{format_price(p.high):>14}")

        final = preds[-1]
        cagr = (final.mid / current) ** (1 / 5) - 1
        print(f"\n  5-Year Base CAGR: {cagr:+.1%}")

    print()


def main():
    args = sys.argv[1:]
    years = [2026, 2027, 2028, 2029, 2030, 2031]

    if "--json" in args:
        asset = "BTC"
        if "--asset" in args:
            idx = args.index("--asset")
            asset = args[idx + 1].upper()
        print(to_json(asset, years))
    elif "--quick" in args:
        quick_summary()
    else:
        print(full_report())


if __name__ == "__main__":
    main()
