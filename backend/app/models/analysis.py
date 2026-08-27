from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, func, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class RepositoryAnalysis(Base):
    __tablename__ = "repository_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    repo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id"), nullable=False, index=True
    )

    # LLM tier used
    quality_tier: Mapped[str] = mapped_column(String(20), nullable=True)  # HIGH/MEDIUM
    apis_used: Mapped[dict] = mapped_column(JSONB, nullable=True)

    # AI-generated text fields
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    architecture_explanation: Mapped[str] = mapped_column(Text, nullable=True)
    code_walkthrough: Mapped[str] = mapped_column(Text, nullable=True)
    common_patterns: Mapped[str] = mapped_column(Text, nullable=True)
    gotchas_and_tips: Mapped[str] = mapped_column(Text, nullable=True)
    setup_guide: Mapped[str] = mapped_column(Text, nullable=True)

    # Data from GitHub API (stored as JSON)
    tech_stack: Mapped[dict] = mapped_column(JSONB, nullable=True)
    directory_structure: Mapped[dict] = mapped_column(JSONB, nullable=True)
    open_issues: Mapped[dict] = mapped_column(JSONB, nullable=True)
    contributors: Mapped[dict] = mapped_column(JSONB, nullable=True)
    commits: Mapped[dict] = mapped_column(JSONB, nullable=True)

    # Code quality metrics from AST analysis
    code_quality_metrics: Mapped[dict] = mapped_column(JSONB, nullable=True)
    # Example: {avg_complexity, files_analyzed, total_functions, all_issues}

    # Stored AI suggestions for consistency
    ai_suggestions: Mapped[dict] = mapped_column(JSONB, nullable=True)
    # Stores the LLM-generated contribution suggestions

    # Flags
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="analyses")
    opportunities: Mapped[list] = relationship("Opportunity", back_populates="analysis")
    pdf_reports: Mapped[list] = relationship("PdfReport", back_populates="analysis")
