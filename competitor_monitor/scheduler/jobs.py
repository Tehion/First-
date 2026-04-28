from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select

from competitor_monitor.config import COMPETITORS, MARKETS, CompetitorConfig, SKUConfig
from competitor_monitor.crawler import PlaywrightCrawler
from competitor_monitor.detectors import ChangeDetector, DetectedChange
from competitor_monitor.extractors import PriceData, PriceExtractor, PromoData, PromoExtractor
from competitor_monitor.reporters import EmailReporter
from competitor_monitor.storage import AsyncSessionLocal
from competitor_monitor.storage.models import (
    ChangeEvent,
    PageSnapshot,
    PriceRecord,
    PromoRecord,
)

logger = logging.getLogger(__name__)

_SCREENSHOT_DIR = "screenshots"


async def run_monitoring_cycle() -> None:
    """Full monitoring cycle: crawl → extract → detect → report."""
    logger.info("Starting monitoring cycle for %d competitors", len(COMPETITORS))

    price_extractor = PriceExtractor()
    promo_extractor = PromoExtractor()
    detector = ChangeDetector()
    changes_by_competitor: dict[str, list[DetectedChange]] = defaultdict(list)

    async with PlaywrightCrawler(screenshot_dir=_SCREENSHOT_DIR) as crawler:
        for competitor in COMPETITORS:
            try:
                await _process_competitor(
                    competitor=competitor,
                    crawler=crawler,
                    price_extractor=price_extractor,
                    promo_extractor=promo_extractor,
                    detector=detector,
                    changes_by_competitor=changes_by_competitor,
                )
            except Exception:
                logger.exception("Failed to process competitor %s", competitor.id)

    reporter = EmailReporter()
    await reporter.send(dict(changes_by_competitor))
    logger.info("Monitoring cycle complete")


async def _process_competitor(
    *,
    competitor: CompetitorConfig,
    crawler: PlaywrightCrawler,
    price_extractor: PriceExtractor,
    promo_extractor: PromoExtractor,
    detector: ChangeDetector,
    changes_by_competitor: dict[str, list[DetectedChange]],
) -> None:
    market = MARKETS.get(competitor.market)
    currency = market.currency if market else "EUR"

    # --- Homepage: promo detection ---
    logger.info("[%s] Crawling homepage: %s", competitor.id, competitor.homepage_url)
    homepage_result = await crawler.crawl(
        competitor.homepage_url,
        take_screenshot=True,
    )

    if homepage_result.success:
        async with AsyncSessionLocal() as session:
            snapshot = PageSnapshot(
                competitor_id=competitor.id,
                market=competitor.market,
                url=competitor.homepage_url,
                page_type="homepage",
                html_hash=homepage_result.html_hash,
                html_content=homepage_result.html,
                screenshot_path=homepage_result.screenshot_path,
            )
            session.add(snapshot)
            await session.flush()

            current_promos = await promo_extractor.extract(homepage_result.html)
            previous_promos = await _load_previous_promos(session, competitor.id)

            for promo in current_promos:
                session.add(PromoRecord(
                    snapshot_id=snapshot.id,
                    competitor_id=competitor.id,
                    market=competitor.market,
                    promo_type=promo.promo_type,
                    title=promo.title,
                    description=promo.description,
                    discount_pct=promo.discount_pct,
                    valid_until=promo.valid_until,
                ))

            promo_changes = detector.detect_promo_changes(
                competitor.name, current_promos, previous_promos
            )
            for change in promo_changes:
                session.add(ChangeEvent(
                    snapshot_id=snapshot.id,
                    competitor_id=competitor.id,
                    market=competitor.market,
                    change_type=change.change_type,
                    importance=change.importance,
                    summary=change.summary,
                    detail=change.detail,
                    previous_value=change.previous_value,
                    current_value=change.current_value,
                ))
            changes_by_competitor[competitor.name].extend(promo_changes)
            await session.commit()
    else:
        logger.warning("[%s] Homepage crawl failed: %s", competitor.id, homepage_result.error)

    # --- SKU pages: price monitoring ---
    for sku in competitor.skus:
        logger.info("[%s] Crawling SKU %s: %s", competitor.id, sku.id, sku.url)
        sku_result = await crawler.crawl(sku.url)
        if not sku_result.success:
            logger.warning("[%s] SKU crawl failed for %s: %s", competitor.id, sku.id, sku_result.error)
            continue

        async with AsyncSessionLocal() as session:
            snapshot = PageSnapshot(
                competitor_id=competitor.id,
                market=competitor.market,
                url=sku.url,
                page_type="sku",
                html_hash=sku_result.html_hash,
                html_content=sku_result.html,
            )
            session.add(snapshot)
            await session.flush()

            current_price = await price_extractor.extract(sku_result.html, sku.name, currency)
            previous_price = await _load_previous_price(session, competitor.id, sku.id)

            session.add(PriceRecord(
                snapshot_id=snapshot.id,
                competitor_id=competitor.id,
                sku_id=sku.id,
                sku_name=current_price.product_name or sku.name,
                price=current_price.price,
                original_price=current_price.original_price,
                currency=current_price.currency,
                in_stock=current_price.in_stock,
            ))

            price_changes = detector.detect_price_changes(sku, current_price, previous_price)
            for change in price_changes:
                session.add(ChangeEvent(
                    snapshot_id=snapshot.id,
                    competitor_id=competitor.id,
                    market=competitor.market,
                    change_type=change.change_type,
                    importance=change.importance,
                    summary=change.summary,
                    detail=change.detail,
                    previous_value=change.previous_value,
                    current_value=change.current_value,
                ))
            changes_by_competitor[competitor.name].extend(price_changes)
            await session.commit()


async def _load_previous_price(session, competitor_id: str, sku_id: str) -> PriceData | None:
    result = await session.execute(
        select(PriceRecord)
        .where(PriceRecord.competitor_id == competitor_id, PriceRecord.sku_id == sku_id)
        .order_by(PriceRecord.recorded_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return PriceData(
        price=row.price,
        original_price=row.original_price,
        currency=row.currency,
        in_stock=row.in_stock,
        product_name=row.sku_name,
    )


async def _load_previous_promos(session, competitor_id: str) -> list[PromoData]:
    # Find the most recent homepage snapshot for this competitor
    snap_result = await session.execute(
        select(PageSnapshot)
        .where(
            PageSnapshot.competitor_id == competitor_id,
            PageSnapshot.page_type == "homepage",
        )
        .order_by(PageSnapshot.crawled_at.desc())
        .limit(1)
    )
    snap = snap_result.scalar_one_or_none()
    if snap is None:
        return []

    promos_result = await session.execute(
        select(PromoRecord).where(PromoRecord.snapshot_id == snap.id)
    )
    rows = promos_result.scalars().all()
    return [
        PromoData(
            promo_type=r.promo_type,
            title=r.title,
            description=r.description,
            discount_pct=r.discount_pct,
            valid_until=r.valid_until,
        )
        for r in rows
    ]
