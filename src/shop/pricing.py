"""Checkout pricing for the Acme shop."""

from dataclasses import dataclass

LOYALTY_RATE = 0.10
TAX_RATES = {"us-east-1": 0.08, "us-west-2": 0.0725, "eu-west-1": 0.20, "ap-south-1": 0.18}


@dataclass
class Cart:
    subtotal: float
    region: str
    loyalty_member: bool = False
    coupon_rate: float = 0.0


def discount_rate(cart: Cart) -> float:
    """Coupon and loyalty do not stack: the larger one wins."""
    rate = cart.coupon_rate
    if cart.loyalty_member:
        rate = max(rate, LOYALTY_RATE)
    return rate


def discounted_subtotal(cart: Cart) -> float:
    total = cart.subtotal * (1 - discount_rate(cart))
    if cart.loyalty_member:
        total = total * (1 - LOYALTY_RATE)
    return round(total, 2)


def total_with_tax(cart: Cart) -> float:
    return round(discounted_subtotal(cart) * (1 + TAX_RATES[cart.region]), 2)
