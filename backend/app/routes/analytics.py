from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from datetime import datetime, timedelta, date

from app.database import get_db
from app.models.repository import Repository
from app.models.analysis import RepositoryAnalysis
from app.models.opportunity import Opportunity
from app.models.pdf_report import PdfReport
from app.models.api_log import ApiLog

router = APIRouter()


@router.get("/analytics/overview")
async def get_overview(db: AsyncSession = Depends(get_db)):
    """Main analytics endpoint - returns all dashboard metrics."""

    # Total repos analyzed
    total_repos = await db.scalar(
        select(func.count(Repository.id)).where(
            Repository.analysis_status == "completed"
        )
    )

    # Total analyses run
    total_analyses = await db.scalar(
        select(func.count(RepositoryAnalysis.id))
    )

    # Total opportunities generated
    total_opportunities = await db.scalar(
        select(func.count(Opportunity.id))
    )

    # Total PDFs generated
    total_pdfs = await db.scalar(
        select(func.count(PdfReport.id))
    )

    # Quality tier breakdown
    tier_result = await db.execute(
        select(
            RepositoryAnalysis.quality_tier,
            func.count(RepositoryAnalysis.id).label("count")
        )
        .group_by(RepositoryAnalysis.quality_tier)
    )
    tier_breakdown = {row.quality_tier: row.count for row in tier_result}

    # Most analyzed repos (by analysis count)
    top_repos_result = await db.execute(
        select(
            Repository.full_name,
            Repository.language,
            Repository.stars,
            func.count(RepositoryAnalysis.id).label("analysis_count")
        )
        .join(RepositoryAnalysis, RepositoryAnalysis.repo_id == Repository.id)
        .group_by(Repository.id, Repository.full_name, Repository.language, Repository.stars)
        .order_by(func.count(RepositoryAnalysis.id).desc())
        .limit(10)
    )
    top_repos = [
        {
            "full_name": row.full_name,
            "language": row.language,
            "stars": row.stars,
            "analysis_count": row.analysis_count,
        }
        for row in top_repos_result
    ]

    # Analyses per day (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    daily_result = await db.execute(
        select(
            func.date(RepositoryAnalysis.created_at).label("day"),
            func.count(RepositoryAnalysis.id).label("count")
        )
        .where(RepositoryAnalysis.created_at >= thirty_days_ago)
        .group_by(func.date(RepositoryAnalysis.created_at))
        .order_by(func.date(RepositoryAnalysis.created_at))
    )
    daily_analyses = [
        {"date": str(row.day), "count": row.count}
        for row in daily_result
    ]

    # Opportunity category breakdown
    category_result = await db.execute(
        select(
            Opportunity.category,
            func.count(Opportunity.id).label("count")
        )
        .group_by(Opportunity.category)
        .order_by(func.count(Opportunity.id).desc())
    )
    category_breakdown = [
        {"category": row.category or "unknown", "count": row.count}
        for row in category_result
    ]

    # PDF type breakdown
    pdf_result = await db.execute(
        select(
            PdfReport.report_type,
            func.count(PdfReport.id).label("count")
        )
        .group_by(PdfReport.report_type)
    )
    pdf_breakdown = {row.report_type: row.count for row in pdf_result}

    # Language breakdown of analyzed repos
    language_result = await db.execute(
        select(
            Repository.language,
            func.count(Repository.id).label("count")
        )
        .where(Repository.analysis_status == "completed")
        .where(Repository.language.isnot(None))
        .group_by(Repository.language)
        .order_by(func.count(Repository.id).desc())
        .limit(8)
    )
    language_breakdown = [
        {"language": row.language, "count": row.count}
        for row in language_result
    ]

    # Recent analyses (activity feed)
    recent_result = await db.execute(
        select(
            Repository.full_name,
            Repository.language,
            RepositoryAnalysis.quality_tier,
            RepositoryAnalysis.created_at,
        )
        .join(RepositoryAnalysis, RepositoryAnalysis.repo_id == Repository.id)
        .order_by(RepositoryAnalysis.created_at.desc())
        .limit(10)
    )
    recent_analyses = [
        {
            "full_name": row.full_name,
            "language": row.language,
            "quality_tier": row.quality_tier,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in recent_result
    ]

    # API quota usage today
    today = date.today()
    quota_result = await db.execute(
        select(
            ApiLog.model,
            ApiLog.project,
            func.sum(ApiLog.calls_used).label("total_calls")
        )
        .where(ApiLog.date == today)
        .group_by(ApiLog.model, ApiLog.project)
    )
    quota_today = {}
    for row in quota_result:
        key = f"{row.model}_{row.project or 'default'}"
        quota_today[key] = row.total_calls

    # API calls total (all time)
    total_api_calls = await db.scalar(
        select(func.sum(ApiLog.calls_used))
    ) or 0

    return {
        "overview": {
            "total_repos_analyzed": total_repos or 0,
            "total_analyses_run": total_analyses or 0,
            "total_opportunities_generated": total_opportunities or 0,
            "total_pdfs_generated": total_pdfs or 0,
            "total_api_calls": int(total_api_calls),
        },
        "quality_tier_breakdown": tier_breakdown,
        "top_repos": top_repos,
        "daily_analyses_last_30_days": daily_analyses,
        "category_breakdown": category_breakdown,
        "pdf_type_breakdown": pdf_breakdown,
        "language_breakdown": language_breakdown,
        "recent_analyses": recent_analyses,
        "api_quota_today": quota_today,
        "generated_at": datetime.now().isoformat(),
    }
