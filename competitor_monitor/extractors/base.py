from __future__ import annotations

import json
import logging
import re
from typing import Any

import anthropic
from bs4 import BeautifulSoup

from competitor_monitor.config import settings

logger = logging.getLogger(__name__)

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


def _strip_html(html: str, max_chars: int = 40_000) -> str:
    """Convert HTML to a compact plain-text representation for LLM consumption."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:max_chars]


async def llm_extract(system_prompt: str, user_content: str) -> dict[str, Any]:
    """
    Call Claude to extract structured JSON from web content.
    Returns parsed dict or empty dict on failure.
    """
    client = _get_client()
    try:
        message = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        raw = message.content[0].text.strip()
        # Extract JSON even if wrapped in markdown code fences
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
        json_str = match.group(1) if match else raw
        return json.loads(json_str)
    except Exception as exc:
        logger.error("LLM extraction failed: %s", exc)
        return {}
