"""Order processing.

DEMO PURPOSE: ``process_order`` is deliberately over-complex so SonarQube
reports high cyclomatic / cognitive complexity (rule python:S3776) and the
unit tests only cover part of it (partial line + branch coverage).
"""
from __future__ import annotations

PK = "PK"
GULF = ("AE", "SA", "QA")


def calculate_shipping(country: str, weight_kg: float, express: bool, total: float) -> float:
    """Return the shipping cost for an order (moderate complexity)."""
    if total >= 10000:
        return 0.0
    if country == PK:
        if weight_kg <= 1:
            cost = 150.0
        elif weight_kg <= 5:
            cost = 300.0
        elif weight_kg <= 20:
            cost = 700.0
        else:
            cost = 1500.0
    elif country in GULF:
        cost = 2500.0 if weight_kg <= 5 else 4500.0
    else:
        cost = 6000.0 + 500.0 * weight_kg
    if express:
        cost *= 1.5
    return cost


def process_order(order: dict, stock: dict, customers: dict) -> dict:
    """Validate an order and compute its total. Intentionally convoluted."""
    result = {"status": "rejected", "reasons": [], "total": 0.0}
    if not order:
        result["reasons"].append("empty order")
        return result
    customer = customers.get(order.get("customer_id"))
    if customer is None:
        result["reasons"].append("unknown customer")
    else:
        for line in order.get("lines", []):
            sku = line.get("sku")
            qty = line.get("qty", 0)
            if sku not in stock:
                result["reasons"].append("unknown sku " + str(sku))
            elif qty <= 0:
                result["reasons"].append("bad quantity for " + sku)
            else:
                if stock[sku]["qty"] >= qty:
                    price = stock[sku]["price"]
                    if line.get("promo"):
                        if line["promo"] == "HALF":
                            price *= 0.5
                        elif line["promo"] == "TENOFF":
                            price *= 0.9
                        else:
                            result["reasons"].append("bad promo " + line["promo"])
                    if customer.get("vip") and qty > 10:
                        price *= 0.95
                    result["total"] += price * qty
                else:
                    result["reasons"].append("insufficient stock for " + sku)
        if not result["reasons"]:
            shipping = calculate_shipping(
                customer.get("country", PK),
                order.get("weight_kg", 1),
                bool(order.get("express")),
                result["total"],
            )
            result["total"] += shipping
            result["status"] = "accepted"
    return result
