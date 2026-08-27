from sqlalchemy import String, Integer, Boolean, DateTime, func, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    github_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=True)
    avatar_url: Mapped[str] = mapped_column(String(512), nullable=True)

    # Profile
    skill_level: Mapped[str] = mapped_column(String(20), nullable=True)  # beginner/intermediate/advanced
    primary_language: Mapped[str] = mapped_column(String(50), nullable=True)
    interests: Mapped[dict] = mapped_column(JSONB, nullable=True)
    experience_years: Mapped[int] = mapped_column(Integer, nullable=True)
    available_hours_per_week: Mapped[int] = mapped_column(Integer, nullable=True)

    # Stats
    repos_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    contributions_made: Mapped[int] = mapped_column(Integer, default=0)
    prs_merged: Mapped[int] = mapped_column(Integer, default=0)
    days_streak: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    contributions: Mapped[list] = relationship("UserContribution", back_populates="user")
    pdf_reports: Mapped[list] = relationship("PdfReport", back_populates="user")
