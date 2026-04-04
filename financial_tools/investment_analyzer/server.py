"""FastAPI server for the AI Investment Analyzer.

Provides REST endpoints to run analysis from any device.
Deploy as a Docker container to Cloud Run, Railway, or similar.

Usage:
    uvicorn financial_tools.investment_analyzer.server:app --host 0.0.0.0 --port 8000

Endpoints:
    GET  /health              - Health check
    GET  /api/v1/snapshot/{ticker}  - Quick data snapshot (no LLM)
    POST /api/v1/analyze      - Full analysis pipeline
    GET  /api/v1/proposals    - List saved proposals
    GET  /api/v1/proposals/{id} - Get a specific proposal
"""

import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .run_analysis import InvestmentAnalyzerPipeline


app = FastAPI(
    title="AI Investment Analyzer",
    description="Analyzes stock market data and drafts investment proposals using Claude AI.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory proposal store (swap for a database in production)
_proposals: dict[str, dict] = {}
_pipeline: Optional[InvestmentAnalyzerPipeline] = None


def get_pipeline() -> InvestmentAnalyzerPipeline:
    """Lazy-initialize the pipeline singleton."""
    global _pipeline
    if _pipeline is None:
        _pipeline = InvestmentAnalyzerPipeline(
            model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
            use_static_writer=os.getenv("USE_STATIC_WRITER", "false").lower() == "true",
        )
    return _pipeline


# --- Request/Response Models ---

class AnalyzeRequest(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol (e.g., AAPL)")
    peers: Optional[list[str]] = Field(None, description="Peer tickers for comparison")
    async_mode: bool = Field(False, description="If true, returns immediately with a proposal ID")


class AnalyzeResponse(BaseModel):
    proposal_id: str
    ticker: str
    status: str  # "completed" or "processing"
    proposal: Optional[str] = None
    created_at: str


class SnapshotResponse(BaseModel):
    ticker: str
    company_name: Optional[str] = None
    current_price: Optional[float] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    sector: Optional[str] = None
    dividend_yield: Optional[float] = None
    beta: Optional[float] = None
    recommendation: Optional[str] = None
    returns: Optional[dict] = None
    news_sentiment: Optional[float] = None
    error: Optional[str] = None


class ProposalListItem(BaseModel):
    proposal_id: str
    ticker: str
    status: str
    created_at: str


# --- Background task ---

def _run_analysis_background(proposal_id: str, ticker: str, peers: Optional[list[str]]):
    """Run analysis in background and store result."""
    try:
        pipeline = get_pipeline()
        proposal_text = pipeline.analyze_stock(ticker, peers=peers)
        _proposals[proposal_id]["status"] = "completed"
        _proposals[proposal_id]["proposal"] = proposal_text
    except Exception as e:
        _proposals[proposal_id]["status"] = "failed"
        _proposals[proposal_id]["error"] = str(e)


# --- Endpoints ---

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ai-investment-analyzer",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/v1/snapshot/{ticker}", response_model=SnapshotResponse)
def get_snapshot(ticker: str):
    """Get a quick data snapshot for a ticker (no LLM calls)."""
    pipeline = get_pipeline()
    try:
        summary = pipeline.get_research_summary(ticker.upper())
        return SnapshotResponse(**summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data: {e}")


@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
def analyze_stock(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """Run the full investment analysis pipeline.

    In sync mode (default), blocks until the proposal is ready.
    In async mode, returns immediately with a proposal_id to poll.
    """
    proposal_id = str(uuid.uuid4())[:8]
    ticker = request.ticker.upper()
    now = datetime.now().isoformat()

    _proposals[proposal_id] = {
        "proposal_id": proposal_id,
        "ticker": ticker,
        "status": "processing",
        "proposal": None,
        "created_at": now,
    }

    if request.async_mode:
        background_tasks.add_task(
            _run_analysis_background, proposal_id, ticker, request.peers
        )
        return AnalyzeResponse(
            proposal_id=proposal_id,
            ticker=ticker,
            status="processing",
            created_at=now,
        )

    # Synchronous mode
    try:
        pipeline = get_pipeline()
        proposal_text = pipeline.analyze_stock(ticker, peers=request.peers)
        _proposals[proposal_id]["status"] = "completed"
        _proposals[proposal_id]["proposal"] = proposal_text
        return AnalyzeResponse(
            proposal_id=proposal_id,
            ticker=ticker,
            status="completed",
            proposal=proposal_text,
            created_at=now,
        )
    except Exception as e:
        _proposals[proposal_id]["status"] = "failed"
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@app.get("/api/v1/proposals", response_model=list[ProposalListItem])
def list_proposals():
    """List all generated proposals."""
    return [
        ProposalListItem(
            proposal_id=p["proposal_id"],
            ticker=p["ticker"],
            status=p["status"],
            created_at=p["created_at"],
        )
        for p in sorted(_proposals.values(), key=lambda x: x["created_at"], reverse=True)
    ]


@app.get("/api/v1/proposals/{proposal_id}", response_model=AnalyzeResponse)
def get_proposal(proposal_id: str):
    """Get a specific proposal by ID."""
    if proposal_id not in _proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    p = _proposals[proposal_id]
    return AnalyzeResponse(
        proposal_id=p["proposal_id"],
        ticker=p["ticker"],
        status=p["status"],
        proposal=p.get("proposal"),
        created_at=p["created_at"],
    )
