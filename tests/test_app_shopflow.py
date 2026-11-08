"""Tests for the SAMPLE APPLICATION (the code SonarQube analyses).

They are deliberately incomplete: inventory is fully covered, orders/pricing/
auth are partially covered, legacy/bugs/tsv_exporter are not covered at all.
That spread is what gives the coverage metrics something interesting to show.
"""
import sqlite3

import pytest

from shopflow.auth import evaluate_formula, find_user, hash_password, new_session_token
from shopflow.exporters.csv_exporter import to_csv
from shopflow.inventory import Inventory, OutOfStockError, Product
from shopflow.orders import calculate_shipping, process_order
from shopflow.pricing import apply_percentage_discount, student_price


# ------------------------------------------------------------- inventory
@pytest.fixture
def inventory():
    inv = Inventory()
    inv.add(Product("A1", "Pen", 10.0, 20))
    inv.add(Product("B2", "Book", 100.0, 3))
    return inv


def test_add_merges_existing_sku(inventory):
    inventory.add(Product("A1", "Pen", 10.0, 5))
    assert inventory.get("A1").quantity == 25


def test_get_unknown_sku_raises(inventory):
    with pytest.raises(KeyError, match="Unknown SKU"):
        inventory.get("ZZ")


def test_remove_stock(inventory):
    inventory.remove_stock("A1", 5)
    assert inventory.get("A1").quantity == 15


def test_remove_too_much_raises(inventory):
    with pytest.raises(OutOfStockError):
        inventory.remove_stock("B2", 4)


def test_total_value(inventory):
    assert inventory.total_value() == 10.0 * 20 + 100.0 * 3


def test_low_stock_sorted(inventory):
    inventory.add(Product("A0", "Cap", 1.0, 1))
    assert [p.sku for p in inventory.low_stock()] == ["A0", "B2"]


# ---------------------------------------------------------------- orders
STOCK = {"A1": {"qty": 10, "price": 100.0}}
CUSTOMERS = {"c1": {"country": "PK", "vip": False}}


def test_shipping_pk_light():
    assert calculate_shipping("PK", 0.5, False, 100) == 150.0


def test_shipping_free_for_big_orders():
    assert calculate_shipping("PK", 30, True, 20000) == 0.0


def test_process_order_accepted():
    order = {"customer_id": "c1", "lines": [{"sku": "A1", "qty": 2}], "weight_kg": 1}
    result = process_order(order, STOCK, CUSTOMERS)
    assert result["status"] == "accepted"
    assert result["total"] == 200.0 + 150.0


def test_process_order_empty_and_unknown_customer():
    assert process_order({}, STOCK, CUSTOMERS)["reasons"] == ["empty order"]
    assert process_order({"customer_id": "x"}, STOCK, CUSTOMERS)["reasons"] == ["unknown customer"]


def test_process_order_unknown_sku():
    order = {"customer_id": "c1", "lines": [{"sku": "NOPE", "qty": 1}]}
    assert process_order(order, STOCK, CUSTOMERS)["status"] == "rejected"


# --------------------------------------------------------------- pricing
def test_percentage_discount():
    assert apply_percentage_discount(200, 25) == 150.0


def test_percentage_discount_validates():
    with pytest.raises(ValueError):
        apply_percentage_discount(200, 150)


def test_student_price_tiers():
    assert student_price(100, 1) == 100.0
    assert student_price(1000, 3) == 3000 * 0.85


# ------------------------------------------------------------------- csv
def test_to_csv_escapes_and_formats():
    text = to_csv([{"a": 'x"y', "b": 1.5}], ["a", "b"])
    assert text == 'a,b\n"x""y","1.50"\n'


def test_to_csv_rejects_non_dict_rows():
    with pytest.raises(TypeError):
        to_csv(["nope"], ["a"])


# ------------------------------------------------------------------ auth
def test_hash_password_is_deterministic():
    assert hash_password("secret") == hash_password("secret")
    assert len(hash_password("secret")) == 32


def test_session_token_changes():
    assert new_session_token() != new_session_token()


def test_find_user_in_memory_db():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE users (name TEXT)")
    conn.execute("INSERT INTO users VALUES ('ali')")
    assert find_user(conn, "ali") == [("ali",)]


def test_evaluate_formula():
    assert evaluate_formula("1 + 2") == 3
