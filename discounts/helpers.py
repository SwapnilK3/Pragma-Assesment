from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from discounts import DiscountType


def get_eligible_discount_rules(order):
    """
    Get all discount rules that are eligible for the given order.

    Filters by:
    - is_active = True
    - start_date <= now
    - end_date is null OR end_date >= now
    - requires_loyalty check (if True, user must be loyalty member)
    """
    # local import because of circular import
    from discounts.models import DiscountRule
    now = timezone.now()
    user = order.user

    # Base queryset: active rules within valid date range
    queryset = DiscountRule.objects.filter(
        is_active=True,
        start_date__lte=now
    ).filter(
        Q(end_date__isnull=True) |
        Q(end_date__gte=now
          )
    )

    # Filter by loyalty requirement
    is_loyalty_member = getattr(user, 'is_loyalty_member', False)
    if not is_loyalty_member:
        # Exclude rules that require loyalty if user is not a member
        queryset = queryset.filter(requires_loyalty=False)

    return queryset.select_related('categories', 'product_variant')


def calculate_order_subtotal(order):
    """Calculate the subtotal of all items in the order."""
    return order.order_items.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')


def calculate_category_subtotal(order, category):
    """Calculate the subtotal of items in a specific category."""
    return order.order_items.filter(
        is_active=True,
        product_variant__product__category=category
    ).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')


def calculate_category_quantity(order, category):
    """Calculate the total quantity of items in a specific category."""
    return order.order_items.filter(
        product_variant__product__category=category
    ).aggregate(
        total=Sum('quantity')
    )['total'] or 0


def calculate_item_subtotal(order, product_variant):
    """Calculate the subtotal of a specific product variant in the order."""
    return order.order_items.filter(
        product_variant=product_variant
    ).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')


def calculate_item_quantity(order, product_variant):
    """Calculate the quantity of a specific product variant in the order."""
    return order.order_items.filter(
        product_variant=product_variant
    ).aggregate(
        total=Sum('quantity')
    )['total'] or 0


def calculate_discount_value(base_amount, discount_type, discount_value):
    """
    Calculate the discount amount based on type.

    - FIX: Returns the fixed discount value (capped at base_amount)
    - PERCENTAGE: Returns percentage of base_amount
    """
    if discount_type == DiscountType.FIX:
        # Fixed discount cannot exceed the base amount
        return min(discount_value, base_amount)

    elif discount_type == DiscountType.PERCENTAGE:
        # Percentage discount
        percentage = discount_value / Decimal('100')
        return base_amount * percentage
    return Decimal('0')


def check_order_conditions(order, rule):
    """
    Check if order-level conditions are met for the discount rule.

    Conditions:
    - min_order_amount: Order subtotal must be >= this value
    """
    order_subtotal = order.subtotal

    if rule.min_order_amount and order_subtotal < rule.min_order_amount:
        return False

    return True


def check_category_conditions(order, rule):
    """
    Check if category-level conditions are met for the discount rule.

    Conditions:
    - min_order_amount: Category subtotal must be >= this value
    - min_quantity: Total quantity in category must be >= this value
    """
    if not rule.categories:
        return False

    category_subtotal = calculate_category_subtotal(order, rule.categories)
    category_quantity = calculate_category_quantity(order, rule.categories)

    # Check if category has any items in the order
    if category_subtotal == 0:
        return False

    if rule.min_order_amount and category_subtotal < rule.min_order_amount:
        return False

    if rule.min_quantity and category_quantity < rule.min_quantity:
        return False

    return True


def check_item_conditions(order, rule):
    """
    Check if item-level conditions are met for the discount rule.

    Conditions:
    - min_order_amount: Item subtotal must be >= this value
    - min_quantity: Item quantity must be >= this value
    """
    if not rule.product_variant:
        return False

    item_subtotal = calculate_item_subtotal(order, rule.product_variant)
    item_quantity = calculate_item_quantity(order, rule.product_variant)

    # Check if item exists in the order
    if item_subtotal == 0:
        return False

    if rule.min_order_amount and item_subtotal < rule.min_order_amount:
        return False

    if rule.min_quantity and item_quantity < rule.min_quantity:
        return False

    return True
