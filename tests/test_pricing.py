import pytest

from shop.pricing import Cart, discounted_subtotal, total_with_tax


@pytest.mark.parametrize("subtotal", [round(5 + i * 1.37, 2) for i in range(400)])
def test_no_discount_keeps_subtotal(subtotal):
    assert discounted_subtotal(Cart(subtotal=subtotal, region="us-east-1")) == subtotal


def test_coupon_only():
    assert discounted_subtotal(Cart(subtotal=100, region="us-east-1", coupon_rate=0.25)) == 75.0


def test_loyalty_discount_applies_once():
    assert discounted_subtotal(Cart(subtotal=100, region="us-east-1", loyalty_member=True)) == 90.0


def test_bigger_discount_wins():
    cart = Cart(subtotal=100, region="us-east-1", loyalty_member=True, coupon_rate=0.25)
    assert discounted_subtotal(cart) == 75.0


def test_eu_tax():
    assert total_with_tax(Cart(subtotal=100, region="eu-west-1")) == 120.0
