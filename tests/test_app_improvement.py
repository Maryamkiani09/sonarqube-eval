"""OPTIONAL "second sprint" tests, switched on with IMPROVE=1.

Workflow for the trend / history demo (Persons 1 and 3):
  1. analyse as-is                      -> baseline (coverage ~68 %)
  2. IMPROVE=1 scripts/run_analysis...  -> more coverage, projectVersion 1.1
  3. compare the two analyses in Activity / Measures history, or run
     `python -m sonar_tools.cli trend shopflow-eval --metric coverage`.
"""
import os

import pytest

from shopflow.exporters.tsv_exporter import to_tsv
from shopflow.orders import calculate_shipping, process_order
from shopflow.pricing import senior_price, student_price

pytestmark = pytest.mark.skipif(not os.environ.get("IMPROVE"), reason="set IMPROVE=1 for the second-sprint tests")

STOCK = {"A1": {"qty": 10, "price": 100.0}}
CUSTOMERS = {"c1": {"country": "AE", "vip": True}}


@pytest.mark.parametrize("country,weight,expected", [("PK", 3, 300.0), ("PK", 10, 700.0), ("PK", 50, 1500.0), ("AE", 3, 2500.0), ("AE", 9, 4500.0), ("US", 2, 7000.0)])
def test_shipping_tiers(country, weight, expected):
    assert calculate_shipping(country, weight, False, 100) == expected


def test_promos_bad_quantity_and_stock():
    lines = [{"sku": "A1", "qty": 1, "promo": "HALF"}, {"sku": "A1", "qty": 1, "promo": "TENOFF"}, {"sku": "A1", "qty": 1, "promo": "??"},
             {"sku": "A1", "qty": 0}, {"sku": "A1", "qty": 99}]
    result = process_order({"customer_id": "c1", "lines": lines}, STOCK, CUSTOMERS)
    assert result["status"] == "rejected" and len(result["reasons"]) == 3


def test_vip_discount_and_express():
    order = {"customer_id": "c1", "lines": [{"sku": "A1", "qty": 11}], "express": True}
    result = process_order(order, {"A1": {"qty": 11, "price": 10.0}}, CUSTOMERS)
    # 11 units * 10.0 * 0.95 (VIP, qty > 10) + AE shipping 2500 * 1.5 (express)
    assert result["status"] == "accepted" and result["total"] == pytest.approx(104.5 + 3750.0)


@pytest.mark.parametrize("quantity,expected", [(1, 100.0), (6, 570.0), (11, 990.0), (30, 2550.0), (60, 4800.0), (120, 9000.0), (250, 17500.0)])
def test_discount_tiers_match_for_both_customer_types(quantity, expected):
    assert student_price(100, quantity) == senior_price(100, quantity) == pytest.approx(expected)


def test_tsv_export():
    assert to_tsv([{"a": "x\ty", "b": None}], ["a", "b"]) == "a\tb\nx y\t\n"
