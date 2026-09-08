from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(200))
    url: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str | None] = mapped_column(String(50))
    license_notes: Mapped[str | None] = mapped_column(Text)


class DataImport(Base):
    __tablename__ = "data_imports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int | None] = mapped_column(Integer, index=True)
    data_type: Mapped[str | None] = mapped_column(String(50), index=True)
    season_id: Mapped[int | None] = mapped_column(Integer, index=True)
    row_count: Mapped[int | None] = mapped_column(Integer)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str | None] = mapped_column(String(20))
    confidence: Mapped[float | None] = mapped_column(Float, default=1.0)
    notes: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(500))

    def __repr__(self):
        return (
            f"<DataImport(type='{self.data_type}', season={self.season_id}, "
            f"rows={self.row_count}, status='{self.status}')>"
        )
