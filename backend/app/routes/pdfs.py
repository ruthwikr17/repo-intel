import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.models.repository import Repository
from app.models.analysis import RepositoryAnalysis
from app.models.opportunity import Opportunity
from app.models.pdf_report import PdfReport
from app.services.pdf_service import (
    generate_contributor_guide,
    generate_executive_summary,
    generate_code_quality_report,
    generate_full_analysis,
)

router = APIRouter()


class PdfRequest(BaseModel):
    repo_id: int
    report_type: str  # contributor_guide / executive_summary / code_quality / full_analysis


@router.post("/pdfs/generate")
async def generate_pdf(request: PdfRequest, db: AsyncSession = Depends(get_db)):
    """Generate a PDF report for a repository."""

    # Get repo
    repo_result = await db.execute(
        select(Repository).where(Repository.id == request.repo_id)
    )
    repo = repo_result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Get analysis
    analysis_result = await db.execute(
        select(RepositoryAnalysis).where(
            RepositoryAnalysis.repo_id == request.repo_id,
            RepositoryAnalysis.is_current == True,
        )
    )
    analysis = analysis_result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found")

    # Get opportunities
    opps_result = await db.execute(
        select(Opportunity)
        .where(Opportunity.repo_id == request.repo_id)
        .order_by(Opportunity.overall_score.desc())
    )
    opportunities = opps_result.scalars().all()

    # Build dicts for templates
    repo_dict = {
        "full_name": repo.full_name,
        "description": repo.description,
        "language": repo.language,
        "stars": repo.stars,
        "forks": repo.forks,
        "open_issues_count": repo.open_issues_count,
        "license": repo.license,
    }

    analysis_dict = {
        "summary": analysis.summary,
        "architecture_explanation": analysis.architecture_explanation,
        "code_walkthrough": analysis.code_walkthrough,
        "common_patterns": analysis.common_patterns,
        "gotchas_and_tips": analysis.gotchas_and_tips,
        "setup_guide": analysis.setup_guide,
        "quality_tier": analysis.quality_tier,
        "executive_summary": None,
        "code_quality_metrics": analysis.code_quality_metrics,
    }

    opp_list = [
        {
            "title": o.title,
            "description": o.description,
            "category": o.category,
            "difficulty": o.difficulty,
            "impact": o.impact,
            "learning_value": o.learning_value,
            "overall_score": o.overall_score,
            "estimated_hours": o.estimated_hours,
            "difficulty_tier": o.difficulty_tier,
            "github_issue_number": o.github_issue_number,
            "github_issue_url": o.github_issue_url,
        }
        for o in opportunities
    ]

    # Generate PDF
    try:
        if request.report_type == "contributor_guide":
            file_path = generate_contributor_guide(analysis_dict, repo_dict, opp_list)
        elif request.report_type == "executive_summary":
            file_path = generate_executive_summary(analysis_dict, repo_dict)
        elif request.report_type == "code_quality":
            file_path = generate_code_quality_report(analysis_dict, repo_dict, opp_list)
        elif request.report_type == "full_analysis":
            file_path = generate_full_analysis(analysis_dict, repo_dict, opp_list)
        else:
            raise HTTPException(status_code=400, detail="Invalid report_type")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    # Save record
    pdf_record = PdfReport(
        repo_id=repo.id,
        analysis_id=analysis.id,
        report_type=request.report_type,
        file_path=file_path,
        file_size_bytes=os.path.getsize(file_path),
    )
    db.add(pdf_record)
    await db.commit()
    await db.refresh(pdf_record)

    return {
        "pdf_id": pdf_record.id,
        "report_type": request.report_type,
        "file_size_bytes": pdf_record.file_size_bytes,
        "download_url": f"/api/pdfs/download/{pdf_record.id}",
    }


@router.get("/pdfs/download/{pdf_id}")
async def download_pdf(pdf_id: int, db: AsyncSession = Depends(get_db)):
    """Download a generated PDF by ID."""
    result = await db.execute(
        select(PdfReport).where(PdfReport.id == pdf_id)
    )
    pdf_record = result.scalar_one_or_none()
    if not pdf_record:
        raise HTTPException(status_code=404, detail="PDF not found")

    if not os.path.exists(pdf_record.file_path):
        raise HTTPException(status_code=404, detail="PDF file missing from disk")

    filename = f"repo_intel_{pdf_record.report_type}_{pdf_record.repo_id}.pdf"
    return FileResponse(
        pdf_record.file_path,
        media_type="application/pdf",
        filename=filename,
    )
