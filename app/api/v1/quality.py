"""
API endpoints for domain quality scoring.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.drop import DroppedDomain
from app.models.tld import Tld
from app.services.quality_scorer import (
    calculate_quality_score,
    get_quality_tier,
    batch_calculate_scores
)

router = APIRouter()


class DomainScoreRequest(BaseModel):
    """Request schema for scoring a single domain."""
    domain: str
    tld: str


class DomainScoreResponse(BaseModel):
    """Response schema for domain score."""
    domain: str
    tld: str
    full_domain: str
    score: int
    tier: str
    breakdown: dict


class BatchScoreRequest(BaseModel):
    """Request schema for batch scoring."""
    domains: List[DomainScoreRequest]


class BatchScoreResponse(BaseModel):
    """Response schema for batch scoring."""
    results: List[DomainScoreResponse]
    count: int


@router.post("/score", response_model=DomainScoreResponse)
def score_domain(request: DomainScoreRequest):
    """
    Calculate quality score for a single domain.
    
    Returns score (0-100), tier, and score breakdown.
    """
    result = calculate_quality_score(
        request.domain,
        request.tld,
        include_breakdown=True
    )
    
    return DomainScoreResponse(
        domain=result["domain"],
        tld=result["tld"],
        full_domain=result["full_domain"],
        score=result["total"],
        tier=get_quality_tier(result["total"]),
        breakdown=result["breakdown"]
    )


@router.post("/score/batch", response_model=BatchScoreResponse)
def score_domains_batch(request: BatchScoreRequest):
    """
    Calculate quality scores for multiple domains.
    
    Returns sorted list (highest score first).
    """
    if len(request.domains) > 100:
        raise HTTPException(
            status_code=400,
            detail="Maximum 100 domains per batch"
        )
    
    domains = [(d.domain, d.tld) for d in request.domains]
    results = batch_calculate_scores(domains)
    
    response_results = [
        DomainScoreResponse(
            domain=r["domain"],
            tld=r["tld"],
            full_domain=r["full_domain"],
            score=r["total"],
            tier=r["tier"],
            breakdown=r["breakdown"]
        )
        for r in results
    ]
    
    return BatchScoreResponse(
        results=response_results,
        count=len(response_results)
    )


@router.get("/score/{domain_id}", response_model=DomainScoreResponse)
def score_domain_by_id(
    domain_id: int,
    db: Session = Depends(get_db)
):
    """
    Calculate quality score for a domain by its database ID.
    """
    domain = db.query(DroppedDomain).filter(DroppedDomain.id == domain_id).first()
    
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    # Extract SLD from full domain
    sld = domain.domain.rsplit('.', 1)[0] if '.' in domain.domain else domain.domain
    tld = domain.tld.name if domain.tld else ""
    
    result = calculate_quality_score(sld, tld, include_breakdown=True)
    
    return DomainScoreResponse(
        domain=result["domain"],
        tld=result["tld"],
        full_domain=result["full_domain"],
        score=result["total"],
        tier=get_quality_tier(result["total"]),
        breakdown=result["breakdown"]
    )


@router.get("/top-domains")
def get_top_quality_domains(
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    tld: Optional[str] = Query(None, description="Filter by TLD"),
    min_score: int = Query(50, ge=0, le=100, description="Minimum quality score"),
    limit: int = Query(50, ge=1, le=200, description="Number of results"),
    db: Session = Depends(get_db)
):
    """
    Get top quality dropped domains.
    
    Returns domains sorted by quality score (calculated on-the-fly).
    """
    from datetime import date as date_type
    from sqlalchemy import func, desc
    
    query = db.query(DroppedDomain).join(Tld)
    
    # Date filter
    if date:
        try:
            filter_date = date_type.fromisoformat(date)
            query = query.filter(DroppedDomain.drop_date == filter_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        # Default to latest date
        latest_date = db.query(func.max(DroppedDomain.drop_date)).scalar()
        if latest_date:
            query = query.filter(DroppedDomain.drop_date == latest_date)
    
    # TLD filter
    if tld:
        query = query.filter(Tld.name == tld.lower())
    
    # Get domains and calculate scores
    domains = query.limit(500).all()  # Get more to filter by score
    
    scored_domains = []
    for d in domains:
        sld = d.domain.rsplit('.', 1)[0] if '.' in d.domain else d.domain
        tld_name = d.tld.name if d.tld else ""
        
        result = calculate_quality_score(sld, tld_name, include_breakdown=True)
        
        if result["total"] >= min_score:
            scored_domains.append({
                "id": d.id,
                "domain": d.domain,
                "tld": tld_name,
                "full_domain": f"{d.domain}",
                "drop_date": d.drop_date.isoformat(),
                "length": d.length,
                "charset_type": d.charset_type,
                "score": result["total"],
                "tier": get_quality_tier(result["total"]),
                "breakdown": result["breakdown"]
            })
    
    # Sort by score and limit
    scored_domains.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "total": len(scored_domains),
        "results": scored_domains[:limit]
    }


@router.get("/tiers")
def get_quality_tiers():
    """
    Get quality tier definitions.
    """
    return {
        "tiers": [
            {"name": "Premium", "min_score": 85, "max_score": 100, "color": "#FFD700"},
            {"name": "Excellent", "min_score": 70, "max_score": 84, "color": "#00D4AA"},
            {"name": "Good", "min_score": 55, "max_score": 69, "color": "#00B4D8"},
            {"name": "Average", "min_score": 40, "max_score": 54, "color": "#90E0EF"},
            {"name": "Below Average", "min_score": 25, "max_score": 39, "color": "#ADB5BD"},
            {"name": "Low", "min_score": 0, "max_score": 24, "color": "#6C757D"}
        ],
        "factors": [
            {"name": "Length", "max_points": 30, "description": "Shorter domains score higher"},
            {"name": "Charset", "max_points": 20, "description": "Letter-only domains score higher"},
            {"name": "Pattern", "max_points": 15, "description": "Pronounceable patterns score higher"},
            {"name": "TLD", "max_points": 15, "description": "Premium TLDs (.dev, .app, .ai) score higher"},
            {"name": "Word", "max_points": 20, "description": "Dictionary words score higher"}
        ]
    }








