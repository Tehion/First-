"""Unit tests for the change detector (no network, no LLM calls)."""
import pytest

from competitor_monitor.config import SKUConfig
from competitor_monitor.detectors.change_detector import ChangeDetector
from competitor_monitor.extractors.price_extractor import PriceData
from competitor_monitor.extractors.promo_extractor import PromoData
from competitor_monitor.storage.models import Importance


@pytest.fixture
def sku() -> SKUConfig:
    return SKUConfig(id="sku_1", name="Test Product", url="https://example.de/p/1", price_alert_threshold_pct=5.0)


@pytest.fixture
def detector() -> ChangeDetector:
    return ChangeDetector()


class TestPriceDetection:
    def test_baseline_on_first_run(self, detector, sku):
        current = PriceData(price=99.99, original_price=None, currency="EUR", in_stock=True, product_name="Test Product")
        changes = detector.detect_price_changes(sku, current, previous=None)
        assert len(changes) == 1
        assert changes[0].change_type == "price_baseline"
        assert changes[0].importance == Importance.LOW

    def test_high_importance_price_drop(self, detector, sku):
        previous = PriceData(price=100.0, original_price=None, currency="EUR", in_stock=True, product_name="Test")
        current = PriceData(price=90.0, original_price=None, currency="EUR", in_stock=True, product_name="Test")
        changes = detector.detect_price_changes(sku, current, previous)
        price_change = next(c for c in changes if c.change_type == "price_change")
        assert price_change.importance == Importance.HIGH  # 10% > 5% threshold

    def test_medium_importance_small_price_change(self, detector, sku):
        previous = PriceData(price=100.0, original_price=None, currency="EUR", in_stock=True, product_name="Test")
        current = PriceData(price=97.0, original_price=None, currency="EUR", in_stock=True, product_name="Test")
        changes = detector.detect_price_changes(sku, current, previous)
        price_change = next(c for c in changes if c.change_type == "price_change")
        assert price_change.importance == Importance.MEDIUM  # 3% < 5% threshold

    def test_no_change_when_same_price(self, detector, sku):
        price = PriceData(price=99.99, original_price=None, currency="EUR", in_stock=True, product_name="Test")
        changes = detector.detect_price_changes(sku, price, price)
        assert not any(c.change_type == "price_change" for c in changes)

    def test_stock_change_is_high(self, detector, sku):
        previous = PriceData(price=99.0, original_price=None, currency="EUR", in_stock=True, product_name="Test")
        current = PriceData(price=99.0, original_price=None, currency="EUR", in_stock=False, product_name="Test")
        changes = detector.detect_price_changes(sku, current, previous)
        stock_change = next(c for c in changes if c.change_type == "stock_change")
        assert stock_change.importance == Importance.HIGH


class TestPromoDetection:
    def test_new_promo_is_high(self, detector):
        current = [PromoData(promo_type="sale", title="Summer Sale 20% off")]
        changes = detector.detect_promo_changes("Competitor X", current, [])
        assert changes[0].importance == Importance.LOW  # first detection → LOW baseline

    def test_new_promo_after_baseline_is_high(self, detector):
        previous = [PromoData(promo_type="sale", title="Winter Sale")]
        current = [PromoData(promo_type="sale", title="Summer Sale 20% off"), PromoData(promo_type="sale", title="Winter Sale")]
        changes = detector.detect_promo_changes("Competitor X", current, previous)
        new_promo = next(c for c in changes if c.change_type == "new_promo")
        assert new_promo.importance == Importance.HIGH

    def test_removed_promo_is_medium(self, detector):
        previous = [PromoData(promo_type="sale", title="Old Sale")]
        current: list[PromoData] = []
        changes = detector.detect_promo_changes("Competitor X", current, previous)
        removed = next(c for c in changes if c.change_type == "removed_promo")
        assert removed.importance == Importance.MEDIUM
