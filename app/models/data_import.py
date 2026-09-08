from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, Column, DateTime, Float, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.connection import Base


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(200))
    url: Mapped[Optional[str]] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    source_type: Mapped[Optional[str]] = mapped_column(String(50))
    license_notes: Mapped[Optional[str]] = mapped_column(Text)


class DataImport(Base):
    __tablename__ = "data_imports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    data_type: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    season_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    row_count: Mapped[Optional[int]] = mapped_column(Integer)
    imported_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[Optional[str]] = mapped_column(String(20))
    confidence: Mapped[Optional[float]] = mapped_column(Float, default=1.0)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(String(500))

    def __repr__(self):
        return (
            f"<DataImport(type='{self.data_type}', season={self.season_id}, "
            f"rows={self.row_count}, status='{self.status}')>"
        )