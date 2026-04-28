from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .base import _strip_html, llm_extract

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a marketing intelligence assistant. Given the visible text of a competitor's
homepage or category page, identify all active promotions, sales, and campaigns.

Return a JSON array of objects. Each object must have:
{
  "promo_type": "<banner | coupon | sale | free_shipping | loyalty | other>",
  "title": "<short title of the promotion, max 120 chars>",
  "description": "<longer description if available, else null>",
  "discount_pct": <numeric discount percentage if stated, else null>,
  "valid_until": "<date string if mentioned, else null>"
}

Return an empty array [] if no promotions are found.
Return only valid JSON. No explanation.
"""


@dataclass
class PromoData:
    promo_type: str
    title: str
    description: str | None = None
    discount_pct: float | None = None
    valid_until: str | None = None


async def extract_promos(html: str) -> list[PromoData]:
    """Use an LLM to detect active promotions on a competitor homepage."""
    page_text = _strip_html(html)
    data = await llm_extract(_SYSTEM_PROMPT, f"Page content:\n{page_text}")

    if not isinstance(data, list):
        return []

    promos: list[PromoData] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        promos.append(
            PromoData(
                promo_type=item.get("promo_type", "other"),
                title=item.get("title", ""),
                description=item.get("description"),
                discount_pct=_to_float(item.get("discount_pct")),
                valid_until=item.get("valid_until"),
            )
        )
    return promos


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class PromoExtractor:
    async def extract(self, html: str) -> list[PromoData]:
        return await extract_promos(html)
