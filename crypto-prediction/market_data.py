"""
Current Market Data & Historical Context for BTC and ETH
Data sourced from CoinGecko, CoinMarketCap, Fortune, and other aggregators.
Last updated: March 30, 2026
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Tuple
import math


@dataclass
class CryptoSnapshot:
    """Point-in-time snapshot of a cryptocurrency."""
    symbol: str
    name: str
    price_usd: float
    market_cap: float
    volume_24h: float
    change_24h_pct: float
    circulating_supply: float
    all_time_high: float
    ath_date: str
    ath_drawdown_pct: float
    rank: int
    snapshot_date: str


# ── Current Market Data (March 30, 2026) ─────────────────────────────────────

BTC_CURRENT = CryptoSnapshot(
    symbol="BTC",
    name="Bitcoin",
    price_usd=67_000.0,
    market_cap=1_332_000_000_000,
    volume_24h=15_080_000_000,
    change_24h_pct=-0.50,
    circulating_supply=20_000_000,
    all_time_high=126_080.0,
    ath_date="2025-10-15",
    ath_drawdown_pct=-47.2,
    rank=1,
    snapshot_date="2026-03-30",
)

ETH_CURRENT = CryptoSnapshot(
    symbol="ETH",
    name="Ethereum",
    price_usd=2_073.0,
    market_cap=250_000_000_000,
    volume_24h=8_500_000_000,
    change_24h_pct=2.80,
    circulating_supply=120_000_000,
    all_time_high=4_951.0,
    ath_date="2025-08-25",
    ath_drawdown_pct=-58.1,
    rank=2,
    snapshot_date="2026-03-30",
)


# ── Historical BTC Price Milestones (approximate monthly closes) ──────────────

BTC_HISTORICAL_MONTHLY: List[Tuple[str, float]] = [
    # Pre-halving and halving cycles
    ("2013-01", 13),
    ("2013-12", 1_150),       # First major bubble peak
    ("2015-01", 200),          # Bear market bottom
    ("2016-07", 660),          # 2nd halving (July 2016)
    ("2017-01", 1_000),
    ("2017-06", 2_500),
    ("2017-12", 19_700),       # 2nd bubble peak
    ("2018-12", 3_200),        # Bear market bottom
    ("2019-06", 12_000),
    ("2020-01", 7_200),
    ("2020-03", 5_000),        # COVID crash
    ("2020-05", 9_500),        # 3rd halving (May 2020)
    ("2020-12", 29_000),
    ("2021-04", 58_000),       # 3rd cycle peak 1
    ("2021-07", 35_000),       # Mid-cycle correction
    ("2021-11", 69_000),       # 3rd cycle ATH
    ("2022-06", 20_000),
    ("2022-11", 16_500),       # Bear market bottom (FTX)
    ("2023-01", 23_000),
    ("2023-06", 30_500),
    ("2023-10", 34_000),
    ("2024-01", 42_000),
    ("2024-03", 70_000),       # Pre-halving rally
    ("2024-04", 63_000),       # 4th halving (April 2024)
    ("2024-06", 62_000),
    ("2024-09", 58_000),
    ("2024-12", 95_000),
    ("2025-01", 102_000),
    ("2025-03", 88_000),
    ("2025-06", 105_000),
    ("2025-10", 126_080),      # 4th cycle ATH
    ("2025-12", 88_000),       # Post-ATH correction
    ("2026-01", 75_000),
    ("2026-02", 70_000),
    ("2026-03", 67_000),       # Current
]

ETH_HISTORICAL_MONTHLY: List[Tuple[str, float]] = [
    ("2016-01", 1),
    ("2017-01", 8),
    ("2017-06", 350),
    ("2018-01", 1_400),        # 1st major peak
    ("2018-12", 85),           # Bear market bottom
    ("2019-06", 270),
    ("2020-01", 130),
    ("2020-03", 110),          # COVID crash
    ("2020-12", 740),
    ("2021-05", 4_000),        # 1st cycle peak
    ("2021-07", 2_200),
    ("2021-11", 4_800),        # 2nd cycle ATH
    ("2022-06", 1_000),
    ("2022-11", 1_200),
    ("2023-01", 1_600),
    ("2023-06", 1_900),
    ("2023-10", 1_800),
    ("2024-01", 2_300),
    ("2024-03", 3_500),
    ("2024-06", 3_400),
    ("2024-09", 2_500),
    ("2024-12", 3_800),
    ("2025-01", 3_500),
    ("2025-03", 3_200),
    ("2025-06", 4_200),
    ("2025-08", 4_951),        # ATH
    ("2025-12", 2_600),
    ("2026-01", 2_200),
    ("2026-02", 2_100),
    ("2026-03", 2_073),        # Current
]


# ── Bitcoin Halving Schedule ──────────────────────────────────────────────────

HALVING_EVENTS = [
    {"number": 1, "date": "2012-11-28", "block_reward": 25.0,  "price_at_halving": 12},
    {"number": 2, "date": "2016-07-09", "block_reward": 12.5,  "price_at_halving": 660},
    {"number": 3, "date": "2020-05-11", "block_reward": 6.25,  "price_at_halving": 8_700},
    {"number": 4, "date": "2024-04-20", "block_reward": 3.125, "price_at_halving": 63_800},
    {"number": 5, "date": "2028-04-15", "block_reward": 1.5625, "price_at_halving": None},  # Future
]

# Post-halving cycle metrics
HALVING_CYCLE_RETURNS = [
    {"halving": 1, "peak_multiple": 96.0,  "months_to_peak": 13, "peak_price": 1_150},
    {"halving": 2, "peak_multiple": 29.8,  "months_to_peak": 17, "peak_price": 19_700},
    {"halving": 3, "peak_multiple": 7.93,  "months_to_peak": 18, "peak_price": 69_000},
    {"halving": 4, "peak_multiple": 1.98,  "months_to_peak": 18, "peak_price": 126_080},
]


# ── Analyst Forecasts ─────────────────────────────────────────────────────────

@dataclass
class PriceForecast:
    source: str
    year: int
    asset: str
    low: float
    mid: float
    high: float


ANALYST_FORECASTS: List[PriceForecast] = [
    # BTC Forecasts
    PriceForecast("Long Forecast", 2026, "BTC", 74_693, 117_012, 125_369),
    PriceForecast("Long Forecast", 2027, "BTC", 113_324, 120_682, 130_384),
    PriceForecast("Standard Chartered", 2027, "BTC", 200_000, 300_000, 400_000),
    PriceForecast("Coinpedia", 2028, "BTC", 200_000, 325_000, 450_000),
    PriceForecast("Standard Chartered", 2028, "BTC", 300_000, 400_000, 500_000),
    PriceForecast("Changelly", 2029, "BTC", 127_157, 198_301, 305_028),
    PriceForecast("Pantera Capital", 2029, "BTC", 400_000, 570_000, 740_000),
    PriceForecast("Changelly", 2030, "BTC", 153_552, 173_586, 210_238),
    PriceForecast("Coinpedia", 2030, "BTC", 380_000, 640_000, 900_000),
    PriceForecast("Cathie Wood / Ark", 2030, "BTC", 500_000, 750_000, 1_000_000),
    PriceForecast("Changelly", 2031, "BTC", 131_054, 160_512, 203_912),

    # ETH Forecasts
    PriceForecast("Consensus Analysts", 2026, "ETH", 4_572, 4_765, 5_150),
    PriceForecast("InvestingHaven", 2027, "ETH", 5_615, 6_500, 7_500),
    PriceForecast("Cryptopolitan", 2028, "ETH", 4_401, 6_242, 8_083),
    PriceForecast("Cryptopolitan", 2029, "ETH", 8_425, 12_000, 16_794),
    PriceForecast("CoinDCX", 2030, "ETH", 9_000, 12_500, 15_000),
    PriceForecast("Standard Chartered", 2030, "ETH", 15_000, 27_500, 40_000),
    PriceForecast("Cryptopolitan", 2031, "ETH", 10_462, 10_898, 13_000),
]


def get_market_summary() -> str:
    """Return a formatted market summary string."""
    btc = BTC_CURRENT
    eth = ETH_CURRENT

    return f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                    CRYPTO MARKET SNAPSHOT — {btc.snapshot_date}                ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║  BITCOIN (BTC)                          ETHEREUM (ETH)                 ║
║  ─────────────                          ──────────────                 ║
║  Price:    ${btc.price_usd:>10,.0f}               Price:    ${eth.price_usd:>10,.0f}      ║
║  Mkt Cap:  ${btc.market_cap/1e12:.2f}T                 Mkt Cap:  ${eth.market_cap/1e9:.0f}B          ║
║  24h Vol:  ${btc.volume_24h/1e9:.1f}B                  24h Vol:  ${eth.volume_24h/1e9:.1f}B           ║
║  24h Chg:  {btc.change_24h_pct:>+.2f}%                  24h Chg:  {eth.change_24h_pct:>+.2f}%          ║
║  ATH:      ${btc.all_time_high:>10,.0f}               ATH:      ${eth.all_time_high:>10,.0f}      ║
║  From ATH: {btc.ath_drawdown_pct:>+.1f}%                  From ATH: {eth.ath_drawdown_pct:>+.1f}%         ║
║  Supply:   {btc.circulating_supply/1e6:.0f}M BTC                  Supply:   {eth.circulating_supply/1e6:.0f}M ETH          ║
║                                                                        ║
║  Market Context:                                                       ║
║  • BTC dominance: ~60% of total crypto market cap                      ║
║  • Both assets in significant drawdown from 2025 ATHs                  ║
║  • ETF outflows resumed; macro headwinds (strong USD, geopolitics)     ║
║  • Next BTC halving: ~April 2028 (reward → 1.5625 BTC)                ║
║                                                                        ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
