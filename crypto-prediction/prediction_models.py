"""
Crypto Price Prediction Models for BTC and ETH (2026–2031)

Models implemented:
1. Log-Linear Regression — trend extrapolation from historical data
2. Halving Cycle Model — BTC-specific, based on post-halving patterns
3. Monte Carlo Simulation — probabilistic price paths using geometric Brownian motion
4. Stock-to-Flow (S2F) — scarcity-based valuation for BTC
5. Analyst Consensus — weighted average of professional forecasts
6. Composite Model — blended ensemble of all models
"""

import math
import random
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from datetime import date

from market_data import (
    BTC_CURRENT, ETH_CURRENT, BTC_HISTORICAL_MONTHLY, ETH_HISTORICAL_MONTHLY,
    HALVING_EVENTS, HALVING_CYCLE_RETURNS, ANALYST_FORECASTS
)


@dataclass
class PricePrediction:
    """A single price prediction for a given year."""
    year: int
    low: float
    mid: float
    high: float
    model: str
    asset: str


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL 1: Log-Linear Regression
# ═══════════════════════════════════════════════════════════════════════════════

def _months_since_origin(date_str: str, origin: str = "2013-01") -> float:
    """Convert YYYY-MM string to months since origin."""
    oy, om = map(int, origin.split("-"))
    dy, dm = map(int, date_str.split("-"))
    return (dy - oy) * 12 + (dm - om)


def _log_linear_regression(
    data: List[Tuple[str, float]], origin: str = "2013-01"
) -> Tuple[float, float, float]:
    """Fit ln(price) = a + b*t via least squares. Returns (a, b, r_squared)."""
    n = len(data)
    xs = [_months_since_origin(d, origin) for d, _ in data]
    ys = [math.log(p) for _, p in data]

    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)

    b = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
    a = (sum_y - b * sum_x) / n

    # R-squared
    y_mean = sum_y / n
    ss_tot = sum((y - y_mean) ** 2 for y in ys)
    ss_res = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    return a, b, r2


def predict_log_linear(
    asset: str,
    years: List[int],
    volatility_band: float = 0.6,
) -> List[PricePrediction]:
    """Log-linear trend extrapolation with volatility bands."""
    data = BTC_HISTORICAL_MONTHLY if asset == "BTC" else ETH_HISTORICAL_MONTHLY
    origin = "2013-01" if asset == "BTC" else "2016-01"

    a, b, r2 = _log_linear_regression(data, origin)

    predictions = []
    for year in years:
        t = _months_since_origin(f"{year}-06", origin)  # Mid-year
        ln_price = a + b * t
        mid = math.exp(ln_price)

        # Widen bands for further-out predictions
        years_out = year - 2026
        band = volatility_band * (1 + 0.15 * years_out)

        predictions.append(PricePrediction(
            year=year,
            low=mid * math.exp(-band),
            mid=mid,
            high=mid * math.exp(band),
            model="Log-Linear Regression",
            asset=asset,
        ))

    return predictions


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL 2: Halving Cycle Model (BTC only)
# ═══════════════════════════════════════════════════════════════════════════════

def predict_halving_cycle(years: List[int]) -> List[PricePrediction]:
    """
    BTC prediction based on diminishing-returns halving cycle pattern.

    Key insight: Each cycle's peak multiple over halving price has been declining:
    Cycle 1: 96x → Cycle 2: 30x → Cycle 3: 8x → Cycle 4: 2x

    The diminishing ratio is roughly 3.2x per cycle.
    """
    # Cycle 4 data (current cycle)
    cycle4_halving_price = 63_800
    cycle4_peak = 126_080
    cycle4_peak_multiple = cycle4_peak / cycle4_halving_price  # ~1.98x

    # Diminishing returns: each cycle peak multiple decays by ~3.2x
    # But we also model the base price (halving price) rising
    cycle5_halving_date = 2028.3  # April 2028
    cycle5_est_halving_price = 150_000  # Estimated based on trend

    # Cycle 5 peak multiple estimate (continuing diminishing pattern but slower decay)
    cycle5_peak_multiple = max(cycle4_peak_multiple * 0.65, 1.3)  # ~1.3x minimum
    cycle5_est_peak = cycle5_est_halving_price * (1 + cycle5_peak_multiple)

    predictions = []
    for year in years:
        if year <= 2028:
            # Pre-halving 5: we're in cycle 4 territory
            # Recovery from current drawdown, then pre-halving accumulation
            if year == 2026:
                mid = 95_000    # Recovery from current ~67k
                low = 60_000
                high = 130_000
            elif year == 2027:
                mid = 120_000   # Pre-halving accumulation
                low = 85_000
                high = 165_000
            else:  # 2028
                mid = 160_000   # Halving year rally
                low = 100_000
                high = 250_000
        elif year == 2029:
            # Post-halving peak year (historically 12-18 months after)
            mid = 225_000
            low = 140_000
            high = 350_000
        elif year == 2030:
            # Post-peak correction year
            mid = 175_000
            low = 110_000
            high = 280_000
        else:  # 2031
            # Bear/accumulation phase
            mid = 150_000
            low = 90_000
            high = 230_000

        predictions.append(PricePrediction(
            year=year,
            low=low,
            mid=mid,
            high=high,
            model="Halving Cycle",
            asset="BTC",
        ))

    return predictions


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL 3: Monte Carlo Simulation (Geometric Brownian Motion)
# ═══════════════════════════════════════════════════════════════════════════════

def _compute_historical_params(
    data: List[Tuple[str, float]]
) -> Tuple[float, float]:
    """Compute annualized drift and volatility from monthly price data."""
    # Monthly log returns
    log_returns = []
    for i in range(1, len(data)):
        r = math.log(data[i][1] / data[i - 1][1])
        # Approximate months between data points
        m1 = _months_since_origin(data[i - 1][0])
        m2 = _months_since_origin(data[i][0])
        dt = max(m2 - m1, 1)
        monthly_r = r / dt
        log_returns.append(monthly_r)

    n = len(log_returns)
    mu_monthly = sum(log_returns) / n
    var_monthly = sum((r - mu_monthly) ** 2 for r in log_returns) / (n - 1)

    # Annualize
    mu_annual = mu_monthly * 12
    sigma_annual = math.sqrt(var_monthly * 12)

    return mu_annual, sigma_annual


def predict_monte_carlo(
    asset: str,
    years: List[int],
    n_simulations: int = 50_000,
    seed: int = 42,
) -> List[PricePrediction]:
    """
    Monte Carlo simulation using geometric Brownian motion.

    dS/S = μdt + σdW

    Uses historical drift and volatility, with mean-reversion adjustment
    to prevent unrealistic exponential growth.
    """
    random.seed(seed)

    data = BTC_HISTORICAL_MONTHLY if asset == "BTC" else ETH_HISTORICAL_MONTHLY
    current_price = BTC_CURRENT.price_usd if asset == "BTC" else ETH_CURRENT.price_usd

    mu_raw, sigma = _compute_historical_params(data)

    # Apply dampening to drift for forward projections (maturing market)
    mu = mu_raw * 0.45  # Historical crypto returns are unlikely to persist fully

    # Reduce volatility slightly for maturing market
    sigma_adj = sigma * 0.85

    dt = 1 / 12  # Monthly steps

    predictions = []
    for year in years:
        months_ahead = (year - 2026) * 12 + 3  # From March 2026 to mid-year target
        steps = max(months_ahead, 1)

        final_prices = []
        for _ in range(n_simulations):
            price = current_price
            for _ in range(steps):
                z = random.gauss(0, 1)
                price *= math.exp(
                    (mu - 0.5 * sigma_adj ** 2) * dt + sigma_adj * math.sqrt(dt) * z
                )
            final_prices.append(price)

        final_prices.sort()
        p10 = final_prices[int(n_simulations * 0.10)]
        p50 = final_prices[int(n_simulations * 0.50)]
        p90 = final_prices[int(n_simulations * 0.90)]

        predictions.append(PricePrediction(
            year=year,
            low=p10,
            mid=p50,
            high=p90,
            model="Monte Carlo (GBM)",
            asset=asset,
        ))

    return predictions


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL 4: Stock-to-Flow (BTC only)
# ═══════════════════════════════════════════════════════════════════════════════

def predict_stock_to_flow(years: List[int]) -> List[PricePrediction]:
    """
    Stock-to-Flow model for Bitcoin.

    Model: ln(price) = a + b * ln(S2F)
    Historically: a ≈ -1.84, b ≈ 3.36 (PlanB's original model)

    Updated coefficients for post-2024 halving reality.
    The S2F model has shown significant deviation since 2022,
    so we apply a correction factor.
    """
    # Bitcoin supply schedule
    total_supply = 21_000_000
    current_supply = 19_850_000  # Approximate

    predictions = []
    for year in years:
        # Determine block reward for the year
        if year < 2028:
            block_reward = 3.125
        else:
            block_reward = 1.5625

        # Annual flow
        blocks_per_year = 52_560  # ~6 per hour * 24 * 365
        annual_flow = block_reward * blocks_per_year

        # Stock (approximate)
        years_from_now = year - 2026
        est_supply = min(current_supply + annual_flow * years_from_now, total_supply)

        # S2F ratio
        s2f = est_supply / annual_flow if annual_flow > 0 else float('inf')

        # Original PlanB model
        ln_price_raw = -1.84 + 3.36 * math.log(s2f)

        # Apply reality correction (S2F has overestimated by ~60-70% in cycle 4)
        correction = 0.38
        ln_price = ln_price_raw * correction + math.log(67_000) * (1 - correction)

        mid = math.exp(ln_price)

        # S2F has very wide confidence intervals
        band = 0.8 + 0.05 * years_from_now
        low = mid * math.exp(-band)
        high = mid * math.exp(band)

        predictions.append(PricePrediction(
            year=year,
            low=low,
            mid=mid,
            high=high,
            model="Stock-to-Flow (adjusted)",
            asset="BTC",
        ))

    return predictions


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL 5: Analyst Consensus
# ═══════════════════════════════════════════════════════════════════════════════

def predict_analyst_consensus(
    asset: str,
    years: List[int],
) -> List[PricePrediction]:
    """Weighted average of analyst forecasts for each year."""
    predictions = []
    for year in years:
        matching = [f for f in ANALYST_FORECASTS if f.asset == asset and f.year == year]

        if not matching:
            # Interpolate from nearest years
            before = [f for f in ANALYST_FORECASTS if f.asset == asset and f.year < year]
            after = [f for f in ANALYST_FORECASTS if f.asset == asset and f.year > year]
            if before and after:
                b = max(before, key=lambda f: f.year)
                a = min(after, key=lambda f: f.year)
                weight = (year - b.year) / (a.year - b.year)
                low = b.low + weight * (a.low - b.low)
                mid = b.mid + weight * (a.mid - b.mid)
                high = b.high + weight * (a.high - b.high)
            elif before:
                b = max(before, key=lambda f: f.year)
                growth = 1.15  # Default 15% annual growth assumption
                yrs = year - b.year
                low = b.low * growth ** yrs
                mid = b.mid * growth ** yrs
                high = b.high * growth ** yrs
            else:
                continue
        else:
            low = sum(f.low for f in matching) / len(matching)
            mid = sum(f.mid for f in matching) / len(matching)
            high = sum(f.high for f in matching) / len(matching)

        predictions.append(PricePrediction(
            year=year,
            low=low,
            mid=mid,
            high=high,
            model="Analyst Consensus",
            asset=asset,
        ))

    return predictions


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL 6: ETH/BTC Ratio Model (ETH only)
# ═══════════════════════════════════════════════════════════════════════════════

def predict_eth_ratio(
    btc_predictions: List[PricePrediction],
    years: List[int],
) -> List[PricePrediction]:
    """
    Predict ETH price based on projected ETH/BTC ratio.

    Current ratio: ~0.031 (near historic lows)
    Historical range: 0.015 – 0.088
    Assumption: Mean-reversion toward 0.04–0.06 over time as ETH ecosystem matures.
    """
    current_ratio = ETH_CURRENT.price_usd / BTC_CURRENT.price_usd  # ~0.031

    # Projected ratio recovery schedule
    ratio_targets = {
        2026: (0.025, 0.035, 0.050),
        2027: (0.030, 0.042, 0.060),
        2028: (0.035, 0.050, 0.070),
        2029: (0.035, 0.055, 0.075),
        2030: (0.035, 0.050, 0.070),
        2031: (0.030, 0.048, 0.068),
    }

    predictions = []
    for year in years:
        btc_pred = next((p for p in btc_predictions if p.year == year), None)
        if not btc_pred or year not in ratio_targets:
            continue

        r_low, r_mid, r_high = ratio_targets[year]

        predictions.append(PricePrediction(
            year=year,
            low=btc_pred.low * r_low,
            mid=btc_pred.mid * r_mid,
            high=btc_pred.high * r_high,
            model="ETH/BTC Ratio",
            asset="ETH",
        ))

    return predictions


# ═══════════════════════════════════════════════════════════════════════════════
# COMPOSITE MODEL — Ensemble
# ═══════════════════════════════════════════════════════════════════════════════

def composite_prediction(
    asset: str,
    years: List[int],
    weights: Optional[Dict[str, float]] = None,
) -> List[PricePrediction]:
    """
    Blended ensemble of all applicable models.

    Default weights reflect model reliability:
    - Monte Carlo: 25% (probabilistic, well-founded)
    - Halving Cycle: 20% (strong historical basis for BTC)
    - Log-Linear: 15% (simple trend, assumes continuation)
    - S2F: 10% (theoretical but has shown deviation)
    - Analyst Consensus: 20% (incorporates market intelligence)
    - ETH/BTC Ratio: 10% (ETH only)
    """
    if asset == "BTC":
        default_weights = {
            "Monte Carlo (GBM)": 0.25,
            "Halving Cycle": 0.20,
            "Log-Linear Regression": 0.15,
            "Stock-to-Flow (adjusted)": 0.10,
            "Analyst Consensus": 0.30,
        }
    else:
        default_weights = {
            "Monte Carlo (GBM)": 0.25,
            "Log-Linear Regression": 0.20,
            "Analyst Consensus": 0.30,
            "ETH/BTC Ratio": 0.25,
        }

    w = weights or default_weights

    # Generate all individual model predictions
    all_preds: Dict[str, List[PricePrediction]] = {}

    all_preds["Log-Linear Regression"] = predict_log_linear(asset, years)
    all_preds["Monte Carlo (GBM)"] = predict_monte_carlo(asset, years)
    all_preds["Analyst Consensus"] = predict_analyst_consensus(asset, years)

    if asset == "BTC":
        all_preds["Halving Cycle"] = predict_halving_cycle(years)
        all_preds["Stock-to-Flow (adjusted)"] = predict_stock_to_flow(years)
    else:
        # For ETH ratio model, use BTC composite first
        btc_composite = composite_prediction("BTC", years)
        all_preds["ETH/BTC Ratio"] = predict_eth_ratio(btc_composite, years)

    # Blend
    composite = []
    for year in years:
        total_weight = 0
        weighted_low = 0
        weighted_mid = 0
        weighted_high = 0

        for model_name, model_weight in w.items():
            preds = all_preds.get(model_name, [])
            pred = next((p for p in preds if p.year == year), None)
            if pred:
                weighted_low += pred.low * model_weight
                weighted_mid += pred.mid * model_weight
                weighted_high += pred.high * model_weight
                total_weight += model_weight

        if total_weight > 0:
            composite.append(PricePrediction(
                year=year,
                low=weighted_low / total_weight,
                mid=weighted_mid / total_weight,
                high=weighted_high / total_weight,
                model="Composite Ensemble",
                asset=asset,
            ))

    return composite


def get_all_predictions(asset: str, years: List[int]) -> Dict[str, List[PricePrediction]]:
    """Return predictions from all models for an asset."""
    results = {}

    results["Log-Linear Regression"] = predict_log_linear(asset, years)
    results["Monte Carlo (GBM)"] = predict_monte_carlo(asset, years)
    results["Analyst Consensus"] = predict_analyst_consensus(asset, years)

    if asset == "BTC":
        results["Halving Cycle"] = predict_halving_cycle(years)
        results["Stock-to-Flow (adjusted)"] = predict_stock_to_flow(years)
    else:
        btc_composite = composite_prediction("BTC", years)
        results["ETH/BTC Ratio"] = predict_eth_ratio(btc_composite, years)

    results["Composite Ensemble"] = composite_prediction(asset, years)

    return results
