from rest_framework import serializers

from core import Currency
from core.models import Address
from discounts.models import AppliedDiscount
from inventory.models import StockInventory
from orders.models import Order, OrderItem
from orders.utils import create_shipping_address
from products.models import ProductVariant


class OrderItemInputSerializer(serializers.Serializer):
    """Input serializer for order items during checkout."""
    product_variant_id = serializers.UUIDField(required=True)
    quantity = serializers.IntegerField(required=True, min_value=1)


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for displaying order items."""
    product_name = serializers.CharField(source='product_variant.product.name', read_only=True)
    variant_name = serializers.CharField(source='product_variant.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product_variant', 'product_name', 'variant_name',
            'quantity', 'unit_rate', 'amount', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class OrderSerializer(serializers.Serializer):
    """Serializer for creating an order (checkout)."""
    items = OrderItemInputSerializer(many=True, required=True)
    shipping_address_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    shipping_address = serializers.DictField(required=False, allow_null=True)
    payment_mode = serializers.CharField(required=False, default='online')
    currency = serializers.CharField(required=False, default=Currency.INR)

    def validate_shipping_address(self, shipping_address):
        # If address ID is used, shipping_address can be null
        if not shipping_address:
            return shipping_address

        required_fields = [
            'address_line_1',
            'city',
            'country_code',
            'country_area',
            'postal_code',
            'phone'
        ]

        missing_fields = [
            field for field in required_fields
            if not shipping_address.get(field)
        ]

        if missing_fields:
            raise serializers.ValidationError(
                f"Missing required fields: {missing_fields}"
            )

        return shipping_address

    def validate_items(self, items):
        """Validate that items exist and variants are active."""
        if not items:
            raise serializers.ValidationError("Order must contain at least one item")

        # Check all variants exist and are active
        variant_ids = [item['product_variant_id'] for item in items]
        variants = ProductVariant.objects.filter(
            id__in=variant_ids,
            is_active=True,
            product__is_active=True
        )

        if variants.count() != len(variant_ids):
            raise serializers.ValidationError("One or more product variants are invalid or inactive")

        return items

    def validate(self, attrs):
        shipping_address_id = attrs.get('shipping_address_id')
        shipping_address = attrs.get('shipping_address')

        # If neither is provided
        if not shipping_address_id and not shipping_address:
            raise serializers.ValidationError({
                "shipping_address": "Shipping address must not be empty"
            })
        return attrs

    def save(self):
        """Create order with items and calculate totals."""
        user = self.context['user']
        validated_data = self.validated_data
        items = validated_data.pop('items')
        shipping_address_id = validated_data.pop('shipping_address_id', None)
        shipping_address_details = validated_data.pop('shipping_address', {})
        payment_mode = validated_data.get('payment_mode')
        currency = validated_data.get('currency')

        if shipping_address_id:
            try:
                shipping_address = Address.objects.get(id=shipping_address_id)
            except Address.DoesNotExist:
                raise serializers.ValidationError("Shipping address does not exist")
        else:
            shipping_address = create_shipping_address(shipping_address_details)

        # Create order
        order = Order.objects.create(
            user=user,
            shipping_address=shipping_address,
            payment_mode=payment_mode,
            currency=currency
        )

        for item in items:
            variant = ProductVariant.objects.select_related('product').get(
                id=item['product_variant_id']
            )
            quantity = item['quantity']

            # Get price from variant
            unit_rate = variant.price

            # Create order item (save() will calculate amount automatically)
            order_item = OrderItem.objects.create(
                order=order,
                product_variant=variant,
                quantity=quantity,
                unit_rate=unit_rate,
            )
            inventory_obj = variant.stock_inventory.first()
            if not inventory_obj:
                inventory_obj = StockInventory.objects.create(
                    product_variant=variant
                )
            inventory_obj.reserved_quantity = inventory_obj.reserved_quantity + quantity
            inventory_obj.save()
        order.save()

        return order


class OrderDetailSerializer(serializers.ModelSerializer):
    """Serializer for displaying order details with discount breakdown."""
    order_items = OrderItemSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    shipping_address_details = serializers.SerializerMethodField()

    # Calculated fields
    subtotal = serializers.SerializerMethodField()
    discount_breakdown = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user', 'user_email',
            'order_status', 'payment_status', 'payment_mode',
            'shipping_address', 'shipping_address_details',
            'subtotal', 'discount_amount', 'discount_breakdown',
            'total_payable_tax', 'total_payable_amount', 'currency',
            'order_items', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'order_number', 'user', 'created_at', 'updated_at']

    def get_subtotal(self, obj):
        """Calculate subtotal before discounts."""
        return str(sum(
            item.quantity * item.unit_rate
            for item in obj.order_items.all()
        ))

    def get_discount_breakdown(self, obj):
        """Provide detailed discount breakdown with distribution by scope."""
        queryset = AppliedDiscount.objects.filter(
            is_active=True,
            order=obj
        ).select_related('discount_rule').order_by('-discount_amount')


        # Calculate distribution by scope
        scope_totals = {}
        for discount in queryset:
            scope = discount.scope
            if scope not in scope_totals:
                scope_totals[scope] = {
                    'total_amount': 0,
                    'count': 0,
                    'discounts': []
                }
            scope_totals[scope]['total_amount'] += float(discount.discount_amount)
            scope_totals[scope]['count'] += 1
            scope_totals[scope]['discounts'].append({
                'rule_name': discount.discount_rule.name if discount.discount_rule else 'Unknown',
                'amount': str(discount.discount_amount)
            })
        
        # Format scope totals
        distribution = []
        for scope, data in scope_totals.items():
            distribution.append({
                'scope': scope,
                'scope_display': scope.title(),
                'total_amount': f"{data['total_amount']:.2f}",
                'discount_count': data['count'],
                'discounts': data['discounts']
            })
        
        return {
            'total_discount': str(obj.discount_amount),
            'applied_count': queryset.count(),
            'distribution': distribution
        }

    def get_shipping_address_details(self, obj):
        """Get shipping address details if available."""
        if obj.shipping_address:
            return {
                'id': str(obj.shipping_address.id),
                'address_line_1': obj.shipping_address.address_line_1,
                'address_line_2': obj.shipping_address.address_line_2,
                'city': obj.shipping_address.city,
                'country': str(obj.shipping_address.country),
                'postal_code': obj.shipping_address.postal_code
            }
        return None


class OrderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing orders."""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user_email',
            'order_status', 'payment_status',
            'total_payable_amount', 'currency',
            'items_count', 'created_at'
        ]
        read_only_fields = ['id', 'order_number', 'created_at']

    def get_items_count(self, obj):
        """Get total number of items in order."""
        return obj.order_items.count()
