from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, func, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    analysis_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repository_analyses.id"), nullable=False
    )
    repo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id"), nullable=False, index=True
    )

    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=True)
    # bug / feature / documentation / refactor / testing / dependency

    # GitHub link
    github_issue_number: Mapped[int] = mapped_column(Integer, nullable=True)
    github_issue_url: Mapped[str] = mapped_column(String(512), nullable=True)

    # Scores (1-10 each)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=True)
    learning_value: Mapped[int] = mapped_column(Integer, nullable=True)
    impact: Mapped[int] = mapped_column(Integer, nullable=True)
    feasibility: Mapped[int] = mapped_column(Integer, nullable=True)
    overall_score: Mapped[float] = mapped_column(Float, nullable=True)

    # Estimates
    estimated_hours: Mapped[int] = mapped_column(Integer, nullable=True)
    difficulty_tier: Mapped[str] = mapped_column(String(20), nullable=True)
    # beginner / intermediate / advanced

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    analysis: Mapped["RepositoryAnalysis"] = relationship(
        "RepositoryAnalysis", back_populates="opportunities"
    )
    repository: Mapped["Repository"] = relationship(
        "Repository", back_populates="opportunities"
    )
    contributions: Mapped[list] = relationship(
        "UserContribution", back_populates="opportunity"
    )
