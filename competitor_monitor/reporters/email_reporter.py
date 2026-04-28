from __future__ import annotations

import logging
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
from jinja2 import Environment, PackageLoader, select_autoescape

from competitor_monitor.config import settings
from competitor_monitor.detectors.change_detector import DetectedChange
from competitor_monitor.storage.models import Importance

logger = logging.getLogger(__name__)

_IMPORTANCE_ORDER = {Importance.HIGH: 0, Importance.MEDIUM: 1, Importance.LOW: 2}

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  body { font-family: Arial, sans-serif; font-size: 14px; color: #222; }
  h1 { font-size: 18px; }
  h2 { font-size: 15px; margin-top: 24px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 12px; font-weight: bold; }
  .high   { background: #fde8e8; color: #c0392b; }
  .medium { background: #fef3cd; color: #856404; }
  .low    { background: #e8f4fd; color: #1a5276; }
  table { border-collapse: collapse; width: 100%; }
  td, th { border: 1px solid #ddd; padding: 6px 10px; text-align: left; }
  th { background: #f5f5f5; }
  .footer { margin-top: 32px; font-size: 12px; color: #888; }
</style>
</head>
<body>
<h1>Competitor Monitor — Daily Digest</h1>
<p>Report generated: {{ generated_at }}</p>

{% if high %}
<h2>🔴 High Priority</h2>
<table>
  <tr><th>Competitor</th><th>Type</th><th>Summary</th><th>Detail</th></tr>
  {% for c in high %}
  <tr>
    <td>{{ c.competitor }}</td>
    <td>{{ c.change.change_type }}</td>
    <td>{{ c.change.summary }}</td>
    <td>{{ c.change.detail or '' }}</td>
  </tr>
  {% endfor %}
</table>
{% endif %}

{% if medium %}
<h2>🟡 Medium Priority</h2>
<table>
  <tr><th>Competitor</th><th>Type</th><th>Summary</th><th>Detail</th></tr>
  {% for c in medium %}
  <tr>
    <td>{{ c.competitor }}</td>
    <td>{{ c.change.change_type }}</td>
    <td>{{ c.change.summary }}</td>
    <td>{{ c.change.detail or '' }}</td>
  </tr>
  {% endfor %}
</table>
{% endif %}

{% if low %}
<h2>🔵 Low Priority / Baseline</h2>
<table>
  <tr><th>Competitor</th><th>Type</th><th>Summary</th></tr>
  {% for c in low %}
  <tr>
    <td>{{ c.competitor }}</td>
    <td>{{ c.change.change_type }}</td>
    <td>{{ c.change.summary }}</td>
  </tr>
  {% endfor %}
</table>
{% endif %}

{% if not high and not medium and not low %}
<p>No significant changes detected in this period.</p>
{% endif %}

<div class="footer">Competitor Monitor • C+P Systemy Meblowe</div>
</body>
</html>
"""


class _ChangeEntry:
    def __init__(self, competitor: str, change: DetectedChange) -> None:
        self.competitor = competitor
        self.change = change


class EmailReporter:
    """Sends a formatted HTML digest email with all detected changes."""

    async def send(
        self,
        changes_by_competitor: dict[str, list[DetectedChange]],
        *,
        min_importance: Importance = Importance.MEDIUM,
    ) -> bool:
        all_entries = [
            _ChangeEntry(competitor, change)
            for competitor, changes in changes_by_competitor.items()
            for change in changes
            if _IMPORTANCE_ORDER[change.importance] <= _IMPORTANCE_ORDER[min_importance]
        ]

        if not all_entries and min_importance != Importance.LOW:
            logger.info("No changes above threshold — skipping email")
            return False

        high = [e for e in all_entries if e.change.importance == Importance.HIGH]
        medium = [e for e in all_entries if e.change.importance == Importance.MEDIUM]
        low = [e for e in all_entries if e.change.importance == Importance.LOW]

        html_body = self._render(high, medium, low)
        plain_body = self._plain(high, medium, low)

        return await self._send_email(html_body, plain_body, high_count=len(high))

    def _render(
        self,
        high: list[_ChangeEntry],
        medium: list[_ChangeEntry],
        low: list[_ChangeEntry],
    ) -> str:
        from jinja2 import Environment
        env = Environment()
        tmpl = env.from_string(_HTML_TEMPLATE)
        return tmpl.render(
            generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            high=high,
            medium=medium,
            low=low,
        )

    def _plain(
        self,
        high: list[_ChangeEntry],
        medium: list[_ChangeEntry],
        low: list[_ChangeEntry],
    ) -> str:
        lines = ["Competitor Monitor — Daily Digest", "=" * 40, ""]
        for label, entries in [("HIGH PRIORITY", high), ("MEDIUM PRIORITY", medium), ("LOW PRIORITY", low)]:
            if entries:
                lines.append(f"--- {label} ---")
                for e in entries:
                    lines.append(f"[{e.competitor}] {e.change.summary}")
                    if e.change.detail:
                        lines.append(f"  {e.change.detail}")
                lines.append("")
        if not high and not medium and not low:
            lines.append("No significant changes detected.")
        return "\n".join(lines)

    async def _send_email(self, html_body: str, plain_body: str, high_count: int) -> bool:
        if not settings.smtp_user or not settings.email_to:
            logger.warning("Email not configured — printing report to stdout")
            print(plain_body)
            return True

        subject = f"Competitor Monitor: {high_count} high-priority change(s) detected" if high_count else "Competitor Monitor: Daily Digest"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.email_from
        msg["To"] = settings.email_to
        msg.attach(MIMEText(plain_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user,
                password=settings.smtp_password,
                start_tls=True,
            )
            logger.info("Report email sent to %s", settings.email_to)
            return True
        except Exception as exc:
            logger.error("Failed to send email: %s", exc)
            return False
