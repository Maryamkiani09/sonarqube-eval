"""Pricing and discounts.

DEMO PURPOSE: ``student_price`` and ``senior_price`` contain an identical
block of code -> SonarQube "Duplicated Blocks" / duplicated_lines_density.
"""
from __future__ import annotations


def apply_percentage_discount(price: float, percent: float) -> float:
    """Clean helper: validates its input and rounds the result."""
    if not 0 <= percent <= 100:
        raise ValueError("percent must be between 0 and 100")
    return round(price * (1 - percent / 100), 2)


def student_price(price: float, quantity: int) -> float:
    subtotal = price * quantity
    if subtotal > 20000:
        rate = 0.30
    elif subtotal > 10000:
        rate = 0.25
    elif subtotal > 5000:
        rate = 0.20
    elif subtotal > 2000:
        rate = 0.15
    elif subtotal > 1000:
        rate = 0.10
    elif subtotal > 500:
        rate = 0.05
    else:
        rate = 0.0
    discount = subtotal * rate
    final_price = subtotal - discount
    rounded = round(final_price, 2)
    return rounded


def senior_price(price: float, quantity: int) -> float:
    subtotal = price * quantity
    if subtotal > 20000:
        rate = 0.30
    elif subtotal > 10000:
        rate = 0.25
    elif subtotal > 5000:
        rate = 0.20
    elif subtotal > 2000:
        rate = 0.15
    elif subtotal > 1000:
        rate = 0.10
    elif subtotal > 500:
        rate = 0.05
    else:
        rate = 0.0
    discount = subtotal * rate
    final_price = subtotal - discount
    rounded = round(final_price, 2)
    return rounded
