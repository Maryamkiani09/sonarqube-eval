"""Inventory management.

Intentionally CLEAN: small functions, type hints, docstrings and 100% test
coverage. Use it as the "good code" baseline when comparing ratings.
"""
from __future__ import annotations

from dataclasses import dataclass


class OutOfStockError(Exception):
    """Raised when more units are requested than are in stock."""


@dataclass
class Product:
    sku: str
    name: str
    price: float
    quantity: int = 0


class Inventory:
    """In-memory product store."""

    def __init__(self) -> None:
        self._items: dict[str, Product] = {}

    def add(self, product: Product) -> None:
        """Add a product, or increase the quantity if the SKU already exists."""
        if product.sku in self._items:
            self._items[product.sku].quantity += product.quantity
        else:
            self._items[product.sku] = product

    def get(self, sku: str) -> Product:
        try:
            return self._items[sku]
        except KeyError:
            raise KeyError(f"Unknown SKU: {sku}") from None

    def remove_stock(self, sku: str, quantity: int) -> None:
        product = self.get(sku)
        if quantity > product.quantity:
            raise OutOfStockError(
                f"{sku}: requested {quantity}, only {product.quantity} in stock"
            )
        product.quantity -= quantity

    def total_value(self) -> float:
        return sum(p.price * p.quantity for p in self._items.values())

    def low_stock(self, threshold: int = 5) -> list[Product]:
        low = (p for p in self._items.values() if p.quantity <= threshold)
        return sorted(low, key=lambda p: p.sku)
