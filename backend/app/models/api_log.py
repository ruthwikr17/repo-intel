from sqlalchemy import String, Integer, DateTime, Date, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ApiLog(Base):
    __tablename__ = "api_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    model: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    project: Mapped[str] = mapped_column(String(50), nullable=True)
    calls_used: Mapped[int] = mapped_column(Integer, default=1)
    tokens_input: Mapped[int] = mapped_column(Integer, nullable=True)
    tokens_output: Mapped[int] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=True)
    analysis_id: Mapped[int] = mapped_column(Integer, nullable=True)
    date: Mapped[Date] = mapped_column(Date, server_default=func.current_date(), index=True)
    timestamp: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
