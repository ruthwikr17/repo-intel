from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class PdfReport(Base):
    __tablename__ = "pdf_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    repo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id"), nullable=False
    )
    analysis_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repository_analyses.id"), nullable=True
    )

    report_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # contributor_guide / code_quality / executive_summary / comparison

    file_path: Mapped[str] = mapped_column(String(512), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    share_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=True)

    generated_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="pdf_reports")
    repository: Mapped["Repository"] = relationship(
        "Repository", back_populates="pdf_reports"
    )
    analysis: Mapped["RepositoryAnalysis"] = relationship(
        "RepositoryAnalysis", back_populates="pdf_reports"
    )
