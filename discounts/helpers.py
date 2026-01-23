from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from discounts import DiscountType


def get_eligible_discount_rules(order, use_cache: bool = True):
    """
    Get all discount rules that are eligible for the given order.

    Filters by:
    - is_active = True
    - start_date <= now
    - end_date is null OR end_date >= now
    - requires_loyalty check (if True, user must be loyalty member)
    
    Uses Redis cache for discount rule IDs (scalable - only 2 cache entries total).
    """
    from discounts.models import DiscountRule
    from discounts.cache import (
        get_cached_active_discount_rule_ids,
        get_cached_loyalty_discount_rule_ids,
        cache_active_discount_rule_ids,
        cache_loyalty_discount_rule_ids
    )
    
    now = timezone.now()
    user = order.user
    is_loyalty_member = getattr(user, 'is_loyalty_member', False)
    
    # Try to get from cache
    if use_cache:
        cached_active_ids = get_cached_active_discount_rule_ids()
        cached_loyalty_ids = get_cached_loyalty_discount_rule_ids()
        
        if cached_active_ids is not None and cached_loyalty_ids is not None:
            # Cache hit - filter by loyalty status
            if is_loyalty_member:
                # Loyalty members get all active discounts
                rule_ids = cached_active_ids
            else:
                # Regular users: exclude loyalty-only discounts
                loyalty_set = set(cached_loyalty_ids)
                rule_ids = [rid for rid in cached_active_ids if rid not in loyalty_set]
            
            return DiscountRule.objects.filter(
                id__in=rule_ids,
                is_active=True,
                start_date__lte=now
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gte=now)
            ).select_related('categories', 'product_variant')

    # Cache miss - query database
    base_queryset = DiscountRule.objects.filter(
        is_active=True,
        start_date__lte=now
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=now)
    )
    
    # Get all active rules for caching
    all_active_rules = base_queryset.select_related('categories', 'product_variant')
    
    # Cache the rule IDs (only 2 cache entries!)
    if use_cache:
        active_ids = [str(rule.id) for rule in all_active_rules]
        loyalty_ids = [str(rule.id) for rule in all_active_rules if rule.requires_loyalty]
        cache_active_discount_rule_ids(active_ids)
        cache_loyalty_discount_rule_ids(loyalty_ids)
    
    # Filter for current user
    if is_loyalty_member:
        return all_active_rules
    else:
        return all_active_rules.filter(requires_loyalty=False)


def calculate_order_subtotal(order):
    """Calculate the subtotal of all items in the order."""
    return order.order_items.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')


def get_all_child_category_ids(category):
    """
    Recursively get all child category IDs for a given parent category.
    Includes the parent category itself.
    """
    from products.models import Category
    
    ids = [category.id]
    children = Category.objects.filter(parent=category, is_active=True)
    for child in children:
        ids.extend(get_all_child_category_ids(child))
    return ids


def calculate_category_subtotal(order, category):
    """Calculate the subtotal of items in a specific category (including child categories)."""
    # Get all category IDs (parent + all children)
    category_ids = get_all_child_category_ids(category)
    
    return order.order_items.filter(
        is_active=True,
        product_variant__product__category_id__in=category_ids
    ).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')


def calculate_category_quantity(order, category):
    """Calculate the total quantity of items in a specific category (including child categories)."""
    # Get all category IDs (parent + all children)
    category_ids = get_all_child_category_ids(category)
    
    return order.order_items.filter(
        product_variant__product__category_id__in=category_ids
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
