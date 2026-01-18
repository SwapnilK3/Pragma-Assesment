from django.db import models
from django.utils import timezone

from core.models import AbstractUUID, AbstractActive, AbstractBaseModel
from discounts import DiscountScope, DiscountType
from orders.models import Order
from products.models import Category, ProductVariant


class DiscountRule(AbstractUUID, AbstractActive):
    requires_loyalty = models.BooleanField(default=False)
    is_stackable = models.BooleanField(default=False)

    name = models.CharField(
        max_length=100, null=True, blank=True
    )
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    scope = models.CharField(
        max_length=20, choices=DiscountScope.CHOICES, default=DiscountScope.ORDER
    )
    discount_type = models.CharField(
        max_length=20, choices=DiscountType.CHOICES
    )
    discount_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, null=True, blank=True
    )

    min_order_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    min_quantity = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    categories = models.ForeignKey(
        Category, on_delete=models.CASCADE, null=True, blank=True
    )
    product_variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, null=True, blank=True
    )


class AppliedDiscount(AbstractBaseModel):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, null=True, blank=True
    )
    discount_rule = models.ForeignKey(
        DiscountRule, on_delete=models.CASCADE, null=True, blank=True
    )
    scope = models.CharField(
        max_length=20, choices=DiscountScope.CHOICES, default=DiscountScope.ORDER
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2
    )
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        unique_together = (('order', 'discount_rule'),)
        ordering = ('order', 'discount_rule')
        verbose_name = 'Applied Discount'
        verbose_name_plural = 'Applied Discounts'
