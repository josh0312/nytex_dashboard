from datetime import date
from sqlalchemy import String, Date, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class OperatingSeason(Base):
    """Model for tracking operating seasons"""
    __tablename__ = "operating_seasons"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    is_dynamic: Mapped[bool] = mapped_column(Boolean, default=False)
    rule_description: Mapped[str] = mapped_column(String(500), nullable=True)

    def __repr__(self):
        return f"<OperatingSeason {self.name} ({self.start_date} - {self.end_date})>" 