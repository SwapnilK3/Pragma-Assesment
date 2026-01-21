"""
Serializers for Inventory app models.
"""
from rest_framework import serializers
from django.db import transaction

from inventory.models import StockInventory, StockTransaction
from inventory import TransactionType


class StockTransactionSerializer(serializers.ModelSerializer):
    """Serializer for StockTransaction model."""
    type_display = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        model = StockTransaction
        fields = [
            'id', 'inventory', 'type', 'type_display', 'quantity', 'metadata',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class StockTransactionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating StockTransaction."""

    class Meta:
        model = StockTransaction
        fields = ['id', 'inventory', 'type', 'quantity', 'metadata']
        read_only_fields = ['id']

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value

    @transaction.atomic
    def create(self, validated_data):
        stock_transaction = StockTransaction.objects.create(**validated_data)

        # Recalculate inventory after transaction
        inventory = validated_data['inventory']
        inventory.recalculate_inventory_data()
        inventory.save()

        return stock_transaction


class StockInventoryListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for StockInventory listing."""
    product_name = serializers.CharField(source='product.name', read_only=True)
    variant_name = serializers.CharField(source='product_variant.name', read_only=True)

    class Meta:
        model = StockInventory
        fields = [
            'id', 'product', 'product_name', 'product_variant', 'variant_name',
            'total_quantity', 'reserved_quantity', 'remaining_quantity',
            'to_produce_quantity', 'is_unlimited_stock', 'is_active'
        ]


class StockInventoryDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for StockInventory with transactions."""
    product_name = serializers.CharField(source='product.name', read_only=True)
    variant_name = serializers.CharField(source='product_variant.name', read_only=True)
    recent_transactions = serializers.SerializerMethodField()

    class Meta:
        model = StockInventory
        fields = [
            'id', 'product', 'product_name', 'product_variant', 'variant_name',
            'total_quantity', 'reserved_quantity', 'remaining_quantity',
            'to_produce_quantity', 'is_unlimited_stock', 'recent_transactions',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'remaining_quantity', 'to_produce_quantity']

    def get_recent_transactions(self, obj):
        transactions = obj.stock_transaction.filter(is_active=True).order_by('-created_at')[:10]
        return StockTransactionSerializer(transactions, many=True).data


class StockInventoryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating StockInventory."""
    initial_quantity = serializers.IntegerField(
        write_only=True,
        required=False,
        min_value=0,
        help_text="Initial stock quantity (creates an INWARD transaction)"
    )

    class Meta:
        model = StockInventory
        fields = [
            'id', 'product', 'product_variant', 'total_quantity',
            'reserved_quantity', 'is_unlimited_stock', 'initial_quantity', 'is_active'
        ]
        read_only_fields = ['id']

    def validate(self, data):
        # Only require product or product_variant on create (when instance doesn't exist)
        if not self.instance:
            product = data.get('product')
            product_variant = data.get('product_variant')

            if not product and not product_variant:
                raise serializers.ValidationError(
                    "Either 'product' or 'product_variant' must be provided"
                )

        return data

    @transaction.atomic
    def create(self, validated_data):
        initial_quantity = validated_data.pop('initial_quantity', None)

        inventory = StockInventory.objects.create(**validated_data)

        # Create initial INWARD transaction if quantity provided
        if initial_quantity and initial_quantity > 0:
            StockTransaction.objects.create(
                inventory=inventory,
                type=TransactionType.INWARD,
                quantity=initial_quantity,
                metadata={'note': 'Initial stock entry'}
            )
            inventory.recalculate_inventory_data()
            inventory.save()

        return inventory

    @transaction.atomic
    def update(self, instance, validated_data):
        validated_data.pop('initial_quantity', None)  # Ignore on update

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance
