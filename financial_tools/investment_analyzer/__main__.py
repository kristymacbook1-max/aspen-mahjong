"""CLI entry point for the AI Investment Analyzer.

Usage:
    # Analyze a single stock
    python -m financial_tools.investment_analyzer analyze AAPL

    # Analyze with peer comparison
    python -m financial_tools.investment_analyzer analyze AAPL --peers MSFT GOOGL

    # Quick snapshot (no AI, just data)
    python -m financial_tools.investment_analyzer snapshot AAPL

    # Analyze and save to file
    python -m financial_tools.investment_analyzer analyze AAPL --save

    # Start the web API server
    python -m financial_tools.investment_analyzer serve

    # Use static template (no extra API credits for writing)
    python -m financial_tools.investment_analyzer analyze AAPL --static
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv


def load_env():
    """Load .env from the investment_analyzer directory."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        # Also check project root
        root_env = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        if os.path.exists(root_env):
            load_dotenv(root_env)


def cmd_analyze(args):
    """Run full analysis pipeline."""
    from .run_analysis import InvestmentAnalyzerPipeline

    print(f"\nAnalyzing {args.ticker.upper()}...")
    if args.peers:
        print(f"Comparing against peers: {', '.join(p.upper() for p in args.peers)}")
    print("This takes 30-60 seconds (fetching data + AI analysis).\n")

    pipeline = InvestmentAnalyzerPipeline(
        use_static_writer=args.static,
    )

    if args.save:
        filepath = pipeline.analyze_and_save(
            args.ticker,
            peers=args.peers,
            output_dir=args.output_dir,
        )
        print(f"Proposal saved to: {filepath}")
        print(f"Open it with: cat {filepath}")
    else:
        proposal = pipeline.analyze_stock(args.ticker, peers=args.peers)
        print(proposal)


def cmd_snapshot(args):
    """Quick data snapshot — no AI calls."""
    from .run_analysis import InvestmentAnalyzerPipeline

    print(f"\nFetching snapshot for {args.ticker.upper()}...\n")

    pipeline = InvestmentAnalyzerPipeline()
    summary = pipeline.get_research_summary(args.ticker)

    if "error" in summary:
        print(f"Error: {summary['error']}")
        sys.exit(1)

    print(f"  Company:        {summary.get('company_name', 'N/A')}")
    print(f"  Ticker:         {summary.get('ticker', 'N/A')}")
    print(f"  Price:          ${summary.get('current_price', 0):,.2f}")
    print(f"  Market Cap:     ${summary.get('market_cap', 0):,.0f}")
    print(f"  P/E Ratio:      {summary.get('pe_ratio', 'N/A')}")
    print(f"  Sector:         {summary.get('sector', 'N/A')}")
    print(f"  Beta:           {summary.get('beta', 'N/A')}")
    print(f"  Dividend Yield: {summary.get('dividend_yield', 'N/A')}")
    print(f"  Analyst Rating: {summary.get('recommendation', 'N/A')}")

    returns = summary.get("returns", {})
    if returns:
        print(f"\n  Returns:")
        for period, val in returns.items():
            if val is not None:
                print(f"    {period}: {val*100:+.2f}%")
            else:
                print(f"    {period}: N/A")

    sentiment = summary.get("news_sentiment")
    if sentiment is not None:
        label = "Bullish" if sentiment > 0.15 else "Bearish" if sentiment < -0.15 else "Neutral"
        print(f"\n  News Sentiment: {label} ({sentiment:.3f})")

    print()


def cmd_serve(args):
    """Start the FastAPI server."""
    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn is required. Run: pip install uvicorn")
        sys.exit(1)

    print(f"\nStarting AI Investment Analyzer API on port {args.port}...")
    print(f"Open http://localhost:{args.port}/docs for the interactive API docs.\n")
    print("Endpoints:")
    print(f"  GET  http://localhost:{args.port}/api/v1/snapshot/AAPL")
    print(f"  POST http://localhost:{args.port}/api/v1/analyze")
    print(f"  GET  http://localhost:{args.port}/api/v1/proposals\n")

    uvicorn.run(
        "financial_tools.investment_analyzer.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


def main():
    parser = argparse.ArgumentParser(
        prog="investment_analyzer",
        description="AI Investment Analyzer — Analyze stocks and generate investment proposals.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # analyze command
    analyze_parser = subparsers.add_parser(
        "analyze", help="Run full AI analysis and generate an investment proposal"
    )
    analyze_parser.add_argument("ticker", help="Stock ticker symbol (e.g., AAPL)")
    analyze_parser.add_argument(
        "--peers", nargs="+", help="Peer tickers for comparison (e.g., --peers MSFT GOOGL)"
    )
    analyze_parser.add_argument(
        "--save", action="store_true", help="Save proposal to a file instead of printing"
    )
    analyze_parser.add_argument(
        "--output-dir", default="output", help="Directory to save proposals (default: output)"
    )
    analyze_parser.add_argument(
        "--static", action="store_true",
        help="Use static template for proposal (skips one AI call, saves credits)",
    )

    # snapshot command
    snapshot_parser = subparsers.add_parser(
        "snapshot", help="Quick data snapshot (no AI calls, free)"
    )
    snapshot_parser.add_argument("ticker", help="Stock ticker symbol (e.g., AAPL)")

    # serve command
    serve_parser = subparsers.add_parser(
        "serve", help="Start the web API server"
    )
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    serve_parser.add_argument("--reload", action="store_true", help="Auto-reload on code changes")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        print("\nExamples:")
        print("  python -m financial_tools.investment_analyzer snapshot AAPL")
        print("  python -m financial_tools.investment_analyzer analyze AAPL")
        print("  python -m financial_tools.investment_analyzer analyze AAPL --peers MSFT GOOGL --save")
        print("  python -m financial_tools.investment_analyzer serve")
        sys.exit(0)

    # Load environment variables
    load_env()

    # Check for API key on commands that need it
    if args.command == "analyze" and not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY is not set.")
        print("Either:")
        print("  1. Create a .env file (see .env.example)")
        print("  2. Or export it: export ANTHROPIC_API_KEY=sk-ant-your-key-here")
        sys.exit(1)

    if args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "snapshot":
        cmd_snapshot(args)
    elif args.command == "serve":
        cmd_serve(args)


if __name__ == "__main__":
    main()
