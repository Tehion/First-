from __future__ import annotations

import logging
from dataclasses import dataclass

from competitor_monitor.config import SKUConfig
from competitor_monitor.extractors import PriceData, PromoData
from competitor_monitor.storage.models import Importance

logger = logging.getLogger(__name__)


@dataclass
class DetectedChange:
    change_type: str
    importance: Importance
    summary: str
    detail: str | None = None
    previous_value: str | None = None
    current_value: str | None = None


class ChangeDetector:
    """
    Compares current extractions against the previous recorded values and
    produces a list of scored DetectedChange events.

    Scoring rules:
      - Price change ≥ threshold%  → HIGH
      - Price change < threshold%  → MEDIUM
      - Stock status change        → HIGH
      - New promotion detected     → HIGH
      - Promotion disappeared      → MEDIUM
      - No previous data           → LOW (first-run baseline)
    """

    def detect_price_changes(
        self,
        sku: SKUConfig,
        current: PriceData,
        previous: PriceData | None,
    ) -> list[DetectedChange]:
        changes: list[DetectedChange] = []

        if previous is None:
            changes.append(
                DetectedChange(
                    change_type="price_baseline",
                    importance=Importance.LOW,
                    summary=f"Initial price recorded for {sku.name}",
                    current_value=_fmt_price(current),
                )
            )
            return changes

        # Price change
        if current.price is not None and previous.price is not None:
            delta_pct = abs(current.price - previous.price) / previous.price * 100
            if delta_pct >= 0.1:  # ignore rounding noise < 0.1%
                direction = "increased" if current.price > previous.price else "decreased"
                importance = Importance.HIGH if delta_pct >= sku.price_alert_threshold_pct else Importance.MEDIUM
                changes.append(
                    DetectedChange(
                        change_type="price_change",
                        importance=importance,
                        summary=f"{sku.name}: price {direction} by {delta_pct:.1f}%",
                        detail=f"{previous.price} → {current.price} {current.currency}",
                        previous_value=_fmt_price(previous),
                        current_value=_fmt_price(current),
                    )
                )

        # Stock status change
        if current.in_stock is not None and previous.in_stock is not None:
            if current.in_stock != previous.in_stock:
                status = "back in stock" if current.in_stock else "out of stock"
                changes.append(
                    DetectedChange(
                        change_type="stock_change",
                        importance=Importance.HIGH,
                        summary=f"{sku.name}: {status}",
                        previous_value=str(previous.in_stock),
                        current_value=str(current.in_stock),
                    )
                )

        return changes

    def detect_promo_changes(
        self,
        competitor_name: str,
        current_promos: list[PromoData],
        previous_promos: list[PromoData],
    ) -> list[DetectedChange]:
        changes: list[DetectedChange] = []

        current_titles = {p.title for p in current_promos}
        previous_titles = {p.title for p in previous_promos}

        new_titles = current_titles - previous_titles
        removed_titles = previous_titles - current_titles

        for title in new_titles:
            promo = next(p for p in current_promos if p.title == title)
            desc = f"Type: {promo.promo_type}"
            if promo.discount_pct:
                desc += f", {promo.discount_pct:.0f}% off"
            if promo.valid_until:
                desc += f", valid until {promo.valid_until}"
            changes.append(
                DetectedChange(
                    change_type="new_promo",
                    importance=Importance.HIGH,
                    summary=f"{competitor_name}: new promotion — {title}",
                    detail=desc,
                    current_value=title,
                )
            )

        for title in removed_titles:
            changes.append(
                DetectedChange(
                    change_type="removed_promo",
                    importance=Importance.MEDIUM,
                    summary=f"{competitor_name}: promotion ended — {title}",
                    previous_value=title,
                )
            )

        if not previous_promos and current_promos:
            # First detection of any promos
            for change in changes:
                change.importance = Importance.LOW

        return changes


def _fmt_price(p: PriceData) -> str:
    if p.price is None:
        return "N/A"
    parts = [f"{p.price} {p.currency}"]
    if p.original_price and p.original_price != p.price:
        parts.append(f"(was {p.original_price})")
    return " ".join(parts)
