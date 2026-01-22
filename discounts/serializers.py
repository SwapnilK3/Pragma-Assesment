from rest_framework import serializers

from discounts.models import DiscountRule, AppliedDiscount


class DiscountRuleSerializer(serializers.ModelSerializer):
    """
    Serializer for DiscountRule model.
    
    Optional fields (if not provided, the condition doesn't apply):
    - min_order_amount: Minimum order amount required for discount
    - min_quantity: Minimum quantity required for discount
    - categories: Category to which discount applies (for category scope)
    - product_variant: Product variant to which discount applies (for item scope)
    - end_date: If null, discount has no expiration
    """
    category_name = serializers.CharField(source='categories.name', read_only=True)
    variant_name = serializers.CharField(source='product_variant.name', read_only=True)

    class Meta:
        model = DiscountRule
        fields = [
            'id', 'name', 'is_active',
            'requires_loyalty', 'is_stackable',
            'start_date', 'end_date',
            'scope', 'discount_type', 'discount_value',
            'min_order_amount', 'min_quantity',
            'categories', 'category_name',
            'product_variant', 'variant_name'
        ]
        read_only_fields = ['id']

    def validate(self, data):
        """Validate discount rule based on scope."""
        scope = data.get('scope', self.instance.scope if self.instance else None)

        # Validate scope-specific requirements
        if scope == 'category' and not data.get('categories'):
            if not (self.instance and self.instance.categories):
                raise serializers.ValidationError({
                    'categories': 'Category is required for category-scoped discounts'
                })

        if scope == 'item' and not data.get('product_variant'):
            if not (self.instance and self.instance.product_variant):
                raise serializers.ValidationError({
                    'product_variant': 'Product variant is required for item-scoped discounts'
                })

        # Validate discount value
        discount_type = data.get('discount_type', self.instance.discount_type if self.instance else None)
        discount_value = data.get('discount_value')

        if discount_type == 'percentage' and discount_value is not None:
            if discount_value < 0 or discount_value > 100:
                raise serializers.ValidationError({
                    'discount_value': 'Percentage discount must be between 0 and 100'
                })

        if discount_value is not None and discount_value < 0:
            raise serializers.ValidationError({
                'discount_value': 'Discount value cannot be negative'
            })

        # Validate date range
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                'end_date': 'End date must be after start date'
            })

        return data


class DiscountRuleListSerializer(serializers.ModelSerializer):
    """Serializer for listing discount rules with all necessary fields."""
    category_name = serializers.CharField(source='categories.name', read_only=True)
    variant_name = serializers.CharField(source='product_variant.name', read_only=True)

    class Meta:
        model = DiscountRule
        fields = [
            'id', 'name', 'is_active',
            'requires_loyalty', 'is_stackable',
            'scope', 'discount_type', 'discount_value',
            'min_order_amount', 'min_quantity',
            'start_date', 'end_date',
            'categories', 'category_name',
            'product_variant', 'variant_name'
        ]


class AppliedDiscountSerializer(serializers.ModelSerializer):
    """Serializer for viewing applied discounts."""
    rule_name = serializers.CharField(source='discount_rule.name', read_only=True)
    order_number = serializers.IntegerField(source='order.order_number', read_only=True)

    class Meta:
        model = AppliedDiscount
        fields = [
            'id', 'order', 'order_number', 'discount_rule', 'rule_name',
            'scope', 'discount_amount', 'metadata',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
