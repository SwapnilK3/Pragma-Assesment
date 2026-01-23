from decimal import Decimal

from discounts import DiscountScope
from discounts.helpers import get_eligible_discount_rules, calculate_category_subtotal, calculate_item_subtotal, \
    calculate_discount_value, check_order_conditions, check_category_conditions, check_item_conditions, \
    get_all_child_category_ids


class MockOrder:
    """Lightweight mock order for discount eligibility checks (preview only)."""
    def __init__(self, user, subtotal):
        self.user = user
        self.subtotal = subtotal


def calculate_preview_discounts(user, cart_items, subtotal):
    """
    Calculate discounts for cart preview without creating a real order.
    
    Args:
        user: The authenticated user
        cart_items: List of dicts with keys: variant_id, quantity, total, category_id, 
                    product_name, variant_name, category_name
        subtotal: Decimal total of all cart items
        
    Returns:
        dict with keys: discount_details, applied_discounts, not_applied_discounts,
                       total_discount, stackable_count, non_stackable_count, best_non_stackable
    """
    # Create mock order for eligibility check (only needs user and subtotal)
    mock_order = MockOrder(user, subtotal)
    eligible_rules = get_eligible_discount_rules(mock_order, use_cache=True)
    
    discount_details = []
    
    for rule in eligible_rules:
        result = _calculate_rule_discount(rule, cart_items, subtotal)
        if result:
            discount_details.append(result)
    
    # Separate stackable and non-stackable
    stackable = [d for d in discount_details if d['is_stackable']]
    non_stackable = [d for d in discount_details if not d['is_stackable']]
    
    # Mark applied status
    for d in stackable:
        d['is_applied'] = True
        d['applied_reason'] = 'Stackable - automatically applied'
    
    stackable_total = sum(Decimal(d['discount_amount']) for d in stackable)
    best_non_stackable = None
    
    if non_stackable:
        best_non_stackable = max(non_stackable, key=lambda x: Decimal(x['discount_amount']))
        for d in non_stackable:
            if d['rule_id'] == best_non_stackable['rule_id']:
                d['is_applied'] = True
                d['applied_reason'] = 'Best non-stackable discount - applied'
            else:
                d['is_applied'] = False
                d['applied_reason'] = f"Not applied - {best_non_stackable['rule_name']} gives better value"
        total_discount = stackable_total + Decimal(best_non_stackable['discount_amount'])
    else:
        total_discount = stackable_total
    
    # Cap at subtotal
    total_discount = min(total_discount, subtotal)
    
    return {
        'discount_details': discount_details,
        'applied_discounts': [d for d in discount_details if d.get('is_applied', False)],
        'not_applied_discounts': [d for d in discount_details if not d.get('is_applied', False)],
        'total_discount': total_discount,
        'stackable_count': len(stackable),
        'non_stackable_count': len(non_stackable),
        'best_non_stackable': best_non_stackable
    }


def _calculate_rule_discount(rule, cart_items, subtotal):
    """Calculate discount for a single rule against cart items. Returns dict or None."""
    discount_amount = Decimal('0')
    applies_to = None
    reason = None
    
    if rule.scope == DiscountScope.ORDER:
        if rule.min_order_amount and subtotal < rule.min_order_amount:
            return None
        discount_amount = calculate_discount_value(subtotal, rule.discount_type, rule.discount_value)
        applies_to = 'Entire Order'
        reason = f'Discount on orders' + (f' over ₹{rule.min_order_amount}' if rule.min_order_amount else '')
    
    elif rule.scope == DiscountScope.CATEGORY:
        if not rule.categories:
            return None
        all_category_ids = [str(cid) for cid in get_all_child_category_ids(rule.categories)]
        category_items = [i for i in cart_items if i['category_id'] in all_category_ids]
        category_subtotal = sum(Decimal(i['total']) for i in category_items)
        category_quantity = sum(i['quantity'] for i in category_items)
        
        if category_subtotal == 0:
            return None
        if rule.min_order_amount and category_subtotal < rule.min_order_amount:
            return None
        if rule.min_quantity and category_quantity < int(rule.min_quantity):
            return None
        
        discount_amount = calculate_discount_value(category_subtotal, rule.discount_type, rule.discount_value)
        applies_to = f'{rule.categories.name} Category'
        min_qty = f' (min {int(rule.min_quantity)} items)' if rule.min_quantity else ''
        reason = f'Discount on {rule.categories.name} products{min_qty}'
    
    elif rule.scope == DiscountScope.ITEM:
        if not rule.product_variant:
            return None
        item_entries = [i for i in cart_items if i['variant_id'] == str(rule.product_variant.id)]
        item_subtotal = sum(Decimal(i['total']) for i in item_entries)
        item_quantity = sum(i['quantity'] for i in item_entries)
        
        if item_subtotal == 0:
            return None
        if rule.min_order_amount and item_subtotal < rule.min_order_amount:
            return None
        if rule.min_quantity and item_quantity < int(rule.min_quantity):
            return None
        
        discount_amount = calculate_discount_value(item_subtotal, rule.discount_type, rule.discount_value)
        applies_to = f'{rule.product_variant.product.name} - {rule.product_variant.name}'
        min_qty = f' (min {int(rule.min_quantity)} items)' if rule.min_quantity else ''
        reason = f'Special discount on {rule.product_variant.name}{min_qty}'
    
    if discount_amount <= 0:
        return None
    
    return {
        'rule_id': str(rule.id),
        'rule_name': rule.name,
        'scope': rule.scope,
        'scope_display': rule.scope.title(),
        'applies_to': applies_to,
        'reason': reason,
        'discount_type': rule.discount_type,
        'discount_type_display': 'Fixed Amount' if rule.discount_type == 'fix' else 'Percentage',
        'discount_value': str(rule.discount_value),
        'discount_amount': str(discount_amount.quantize(Decimal('0.01'))),
        'is_stackable': rule.is_stackable,
        'stacking_info': 'Can be combined with other discounts' if rule.is_stackable else 'Best non-stackable discount applied'
    }


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


def get_discount_amount(order, use_cache: bool = True):
    """
    Calculate the total discount amount for an order and create AppliedDiscount records.
    
    Uses Redis cache to get eligible discount rules for the user quickly.
    
    Logic:
    1. Get all eligible discount rules (cached by user + loyalty status)
    2. Apply each rule based on scope (ORDER, CATEGORY, ITEM)
    3. Handle stacking logic:
       - Stackable rules: All discounts are summed
       - Non-stackable rules: Only the best (highest) discount is applied
    4. Create AppliedDiscount records for each applied discount
    
    Args:
        order: The Order instance to calculate discounts for
        use_cache: Whether to use Redis cache for getting eligible rules (default: True)
        
    Returns:
        Decimal: Total discount amount to be applied to the order
    """
    from discounts.models import AppliedDiscount

    # Get eligible rules (uses cache if enabled)
    eligible_rules = get_eligible_discount_rules(order, use_cache=use_cache)

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
