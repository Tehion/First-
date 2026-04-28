from __future__ import annotations

import logging
from dataclasses import dataclass

from .base import _strip_html, llm_extract

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a web data extraction assistant. Given the visible text of a product page,
extract the current price information as JSON with these exact keys:
{
  "price": <float or null>,
  "original_price": <float or null>,  // pre-discount price if shown, else null
  "currency": "<ISO 4217 currency code, e.g. EUR>",
  "in_stock": <true | false | null>,
  "product_name": "<name of the product as shown on the page>"
}
Return only valid JSON. No explanation, no markdown outside the JSON block.
If a value cannot be determined, use null.
"""


@dataclass
class PriceData:
    price: float | None
    original_price: float | None
    currency: str
    in_stock: bool | None
    product_name: str

    @classmethod
    def empty(cls, currency: str = "EUR") -> PriceData:
        return cls(price=None, original_price=None, currency=currency, in_stock=None, product_name="")


async def extract_price(html: str, sku_name: str, market_currency: str) -> PriceData:
    """Use an LLM to extract pricing data from a product page."""
    page_text = _strip_html(html)
    user_content = f"Product we are looking for: {sku_name}\n\nPage content:\n{page_text}"

    data = await llm_extract(_SYSTEM_PROMPT, user_content)
    if not data:
        return PriceData.empty(market_currency)

    return PriceData(
        price=_to_float(data.get("price")),
        original_price=_to_float(data.get("original_price")),
        currency=data.get("currency") or market_currency,
        in_stock=data.get("in_stock"),
        product_name=data.get("product_name") or sku_name,
    )


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class PriceExtractor:
    async def extract(self, html: str, sku_name: str, market_currency: str) -> PriceData:
        return await extract_price(html, sku_name, market_currency)
