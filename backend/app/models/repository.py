from sqlalchemy import String, Integer, Boolean, DateTime, func, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=True)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(512), unique=True, nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=True)

    # GitHub metadata
    language: Mapped[str] = mapped_column(String(50), nullable=True)
    stars: Mapped[int] = mapped_column(Integer, default=0)
    forks: Mapped[int] = mapped_column(Integer, default=0)
    open_issues_count: Mapped[int] = mapped_column(Integer, default=0)
    topics: Mapped[dict] = mapped_column(JSONB, nullable=True)
    license: Mapped[str] = mapped_column(String(100), nullable=True)

    # Analysis status
    analysis_status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending/analyzing/completed/failed
    last_analyzed_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)

    # Cached raw data from GitHub API (stored to avoid re-fetching)
    cached_github_data: Mapped[dict] = mapped_column(JSONB, nullable=True)
    cached_until: Mapped[DateTime] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    analyses: Mapped[list] = relationship("RepositoryAnalysis", back_populates="repository")
    opportunities: Mapped[list] = relationship("Opportunity", back_populates="repository")
    pdf_reports: Mapped[list] = relationship("PdfReport", back_populates="repository")
