from django.contrib import admin
from discounts.models import DiscountRule, AppliedDiscount


@admin.register(DiscountRule)
class DiscountRuleAdmin(admin.ModelAdmin):
    """Admin configuration for DiscountRule model."""
    list_display = [
        'name', 'scope', 'discount_type', 'discount_value',
        'is_active', 'requires_loyalty', 'is_stackable',
        'start_date', 'end_date'
    ]
    list_filter = ['scope', 'discount_type', 'is_active', 'requires_loyalty', 'is_stackable']
    search_fields = ['name']
    ordering = ['-start_date']
    readonly_fields = ['id']


@admin.register(AppliedDiscount)
class AppliedDiscountAdmin(admin.ModelAdmin):
    """Admin configuration for AppliedDiscount model."""
    list_display = [
        'order', 'discount_rule', 'scope', 'discount_amount', 'created_at'
    ]
    list_filter = ['scope', 'created_at']
    search_fields = ['order__order_number', 'discount_rule__name']
    ordering = ['-created_at']
    readonly_fields = ['id', 'created_at', 'updated_at']
