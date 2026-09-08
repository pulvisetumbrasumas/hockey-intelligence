from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, String, Column, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.connection import Base


class Franchise(Base):
    __tablename__ = "franchises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    common_name: Mapped[Optional[str]] = mapped_column(String(100))
    place_name: Mapped[Optional[str]] = mapped_column(String(100))
    raw_tricode: Mapped[Optional[str]] = mapped_column(String(10))
    tricode: Mapped[Optional[str]] = mapped_column(String(10))

    established_year: Mapped[Optional[int]] = mapped_column(Integer)
    active: Mapped[int] = mapped_column(Integer, default=1)
    successor_franchise_id: Mapped[Optional[int]] = mapped_column(Integer)

    notes: Mapped[Optional[str]] = mapped_column(Text)

    def __repr__(self):
        return f"<Franchise(id={self.id}, name='{self.full_name}')>"