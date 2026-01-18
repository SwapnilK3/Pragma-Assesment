from decimal import Decimal

from discounts import DiscountScope
from discounts.helpers import get_eligible_discount_rules, calculate_category_subtotal, calculate_item_subtotal, \
    calculate_discount_value, check_order_conditions, check_category_conditions, check_item_conditions


def apply_discount_rule(order, rule):
    """
    Apply a discount rule and return the discount amount.
    
    Returns:
        Decimal: The calculated discount amount, or 0 if not applicable
    """
    if rule.scope == DiscountScope.ORDER:
        if not check_order_conditions(order, rule):
            return Decimal('0')

        base_amount = order.subtotal
        return calculate_discount_value(
            base_amount, rule.discount_type, rule.discount_value
        )

    elif rule.scope == DiscountScope.CATEGORY:
        if not check_category_conditions(order, rule):
            return Decimal('0')

        base_amount = calculate_category_subtotal(order, rule.categories)
        return calculate_discount_value(
            base_amount, rule.discount_type, rule.discount_value
        )

    elif rule.scope == DiscountScope.ITEM:
        if not check_item_conditions(order, rule):
            return Decimal('0')

        base_amount = calculate_item_subtotal(order, rule.product_variant)
        return calculate_discount_value(
            base_amount, rule.discount_type, rule.discount_value
        )

    return Decimal('0')


def get_discount_amount(order):
    """
    Calculate the total discount amount for an order and create AppliedDiscount records.
    
    Logic:
    1. Get all eligible discount rules
    2. Apply each rule based on scope (ORDER, CATEGORY, ITEM)
    3. Handle stacking logic:
       - Stackable rules: All discounts are summed
       - Non-stackable rules: Only the best (highest) discount is applied
    4. Create AppliedDiscount records for each applied discount
    
    Args:
        order: The Order instance to calculate discounts for
        
    Returns:
        Decimal: Total discount amount to be applied to the order
    """
    from discounts.models import AppliedDiscount

    eligible_rules = get_eligible_discount_rules(order)

    if not eligible_rules.exists():
        return Decimal('0')

    # Separate stackable and non-stackable rules
    stackable_discounts = []  # List of (rule, amount) tuples
    non_stackable_discounts = []  # List of (rule, amount) tuples

    for rule in eligible_rules:
        discount_amount = apply_discount_rule(order, rule)

        if discount_amount > 0:
            if rule.is_stackable:
                stackable_discounts.append((rule, discount_amount))
            else:
                non_stackable_discounts.append((rule, discount_amount))

    # Calculate total discount
    total_discount = Decimal('0')
    applied_rules = []

    # Add all stackable discounts
    for rule, amount in stackable_discounts:
        total_discount += amount
        applied_rules.append((rule, amount))

    # For non-stackable, pick the best one (highest discount)
    if non_stackable_discounts:
        best_non_stackable = max(non_stackable_discounts, key=lambda x: x[1])
        total_discount += best_non_stackable[1]
        applied_rules.append(best_non_stackable)

    # Create AppliedDiscount records
    for rule, amount in applied_rules:
        AppliedDiscount.objects.update_or_create(
            order=order,
            discount_rule=rule,
            defaults={
                'scope': rule.scope,
                'discount_amount': amount,
                'metadata': {
                    'rule_name': rule.name,
                    'discount_type': rule.discount_type,
                    'discount_value': str(rule.discount_value),
                    'is_stackable': rule.is_stackable
                }
            }
        )

    # Ensure total discount doesn't exceed order subtotal
    order_subtotal = order.subtotal
    total_discount = min(total_discount, order_subtotal)

    return total_discount.quantize(Decimal('0.01'))
