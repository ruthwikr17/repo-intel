from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class UserContribution(Base):
    __tablename__ = "user_contributions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    repo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id"), nullable=False
    )
    opportunity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("opportunities.id"), nullable=True
    )

    # Status
    status: Mapped[str] = mapped_column(String(30), default="interested")
    # interested / started / pr_submitted / merged / abandoned

    # PR details
    branch_name: Mapped[str] = mapped_column(String(255), nullable=True)
    pr_number: Mapped[int] = mapped_column(Integer, nullable=True)
    pr_url: Mapped[str] = mapped_column(String(512), nullable=True)
    pr_title: Mapped[str] = mapped_column(String(255), nullable=True)

    # Timestamps
    started_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    pr_submitted_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    merged_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)

    # Metrics
    hours_spent: Mapped[float] = mapped_column(Float, nullable=True)
    lines_changed: Mapped[int] = mapped_column(Integer, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="contributions")
    opportunity: Mapped["Opportunity"] = relationship(
        "Opportunity", back_populates="contributions"
    )
