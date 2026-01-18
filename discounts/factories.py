from datetime import timedelta

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from discounts.models import DiscountRule, AppliedDiscount


class DiscountRuleFactory(DjangoModelFactory):
    """Factory for DiscountRule model."""

    class Meta:
        model = DiscountRule

    name = factory.Sequence(lambda n: f'Discount Rule {n}')
    is_active = True
    requires_loyalty = False
    is_stackable = False
    start_date = factory.LazyFunction(timezone.now)
    end_date = factory.LazyFunction(lambda: timezone.now() + timedelta(days=30))
    scope = 'order'
    discount_type = 'percentage'
    discount_value = factory.Faker('pydecimal', left_digits=2, right_digits=2, positive=True, min_value=5, max_value=50)
    min_order_amount = None
    min_quantity = None
    categories = None
    product_variant = None


class AppliedDiscountFactory(DjangoModelFactory):
    """Factory for AppliedDiscount model."""

    class Meta:
        model = AppliedDiscount

    order = None
    discount_rule = factory.SubFactory(DiscountRuleFactory)
    scope = 'order'
    discount_amount = factory.Faker('pydecimal', left_digits=3, right_digits=2, positive=True)
    metadata = None
