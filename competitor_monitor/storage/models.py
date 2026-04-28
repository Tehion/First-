from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Importance(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PageSnapshot(Base):
    """Raw HTML snapshot of a crawled page at a point in time."""

    __tablename__ = "page_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    competitor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    market: Mapped[str] = mapped_column(String(8), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    page_type: Mapped[str] = mapped_column(String(32), nullable=False)  # homepage | sku | blog
    html_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    screenshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    crawled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    price_records: Mapped[list[PriceRecord]] = relationship(back_populates="snapshot")
    promo_records: Mapped[list[PromoRecord]] = relationship(back_populates="snapshot")
    change_events: Mapped[list[ChangeEvent]] = relationship(back_populates="snapshot")


class PriceRecord(Base):
    """Extracted price for a specific SKU at a specific point in time."""

    __tablename__ = "price_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("page_snapshots.id"), nullable=False)
    competitor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sku_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sku_name: Mapped[str] = mapped_column(String(256), nullable=False)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_price: Mapped[float | None] = mapped_column(Float, nullable=True)  # before discount
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    in_stock: Mapped[bool | None] = mapped_column(nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    snapshot: Mapped[PageSnapshot] = relationship(back_populates="price_records")


class PromoRecord(Base):
    """Detected promotion / campaign on a competitor's homepage or product page."""

    __tablename__ = "promo_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("page_snapshots.id"), nullable=False)
    competitor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    market: Mapped[str] = mapped_column(String(8), nullable=False)
    promo_type: Mapped[str] = mapped_column(String(64), nullable=False)  # banner | coupon | sale | free_shipping
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    discount_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    valid_until: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    snapshot: Mapped[PageSnapshot] = relationship(back_populates="promo_records")


class ChangeEvent(Base):
    """A detected, scored change between two consecutive snapshots."""

    __tablename__ = "change_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("page_snapshots.id"), nullable=False)
    competitor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    market: Mapped[str] = mapped_column(String(8), nullable=False)
    change_type: Mapped[str] = mapped_column(String(64), nullable=False)  # price_change | new_promo | removed_promo | new_product | ...
    importance: Mapped[Importance] = mapped_column(Enum(Importance), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reported: Mapped[bool] = mapped_column(default=False, nullable=False)

    snapshot: Mapped[PageSnapshot] = relationship(back_populates="change_events")
