from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum

from core.models import AbstractBaseModel, IsActiveModelManager
from inventory import TransactionType
from orders import OrderStatus
from orders.models import OrderItem
from products.models import ProductVariant, Product


class StockInventory(AbstractBaseModel):
    """
    Stock Inventory Model for Product Variants
    """
    product_variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE,
        null=True, unique=True, default=None,
        related_name='stock_inventory'
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        null=True, unique=True, default=None,
        related_name='stock_inventory'
    )
    total_quantity = models.IntegerField(
        default=0, validators=[MinValueValidator(0)],
        help_text='Total quantity of stock items'
    )
    reserved_quantity = models.IntegerField(
        default=0, validators=[MinValueValidator(0)],
        help_text='Reserved quantity of stock items'
    )
    to_produce_quantity = models.IntegerField(
        default=0, validators=[MinValueValidator(0)],
        help_text='Total quantity of stock items'
    )
    remaining_quantity = models.IntegerField(
        default=0, validators=[MinValueValidator(0)],
        help_text='Remaining quantity of stock items'
    )
    is_unlimited_stock = models.BooleanField(
        default=False,
        help_text='Unlimited stock items'
    )

    objects = IsActiveModelManager()

    class Meta:
        verbose_name = 'Stock Inventory'
        verbose_name_plural = 'Stock Inventories'
        ordering = ['product_variant', 'product', 'total_quantity']


    def calculate_inventory_qty(self):
        remaining_quantity = self.total_quantity - self.reserved_quantity

        if remaining_quantity >= 0:
            self.to_produce_quantity = 0
            self.remaining_quantity = remaining_quantity
        else:
            self.remaining_quantity = 0
            self.to_produce_quantity = abs(remaining_quantity)


    def save(self, *args, **kwargs):
        self.calculate_inventory_qty()


    def recalculate_inventory_data(self, *args, **kwargs):
        # TODO To consider the financial year for filtering
        #  Right now it is all time orders and transactions
        transaction_qs = self.stock_transaction.filter(
            is_active=True,
            quantity__gt=0
        )
        inward_quantity = transaction_qs.filter(
            type=TransactionType.INWARD,
        ).aggregate(
            total_quantity=Sum('quantity')
        )['total_quantity'] or 0

        # For now no store present then not including this
        # as we have orders as the data to track
        # outward_quantity = transaction_qs.filter(
        #     type=TransactionType.OUTWARD,
        # )

        order_item_qs = OrderItem.objects.filter(
            is_active=True,
            order__is_active=True,
            product_variant=self.product_variant
        )
        handover_order_item_quantity = order_item_qs.filter(
            order__order_status=OrderStatus.HANDED_OVER
        ).aggregate(
            total_quantity=Sum('quantity')
        )['total_quantity'] or 0

        self.total_quantity = inward_quantity - handover_order_item_quantity

        self.reserved_quantity = order_item_qs.aggregate(
            total_quantity=Sum('quantity')
        )['total_quantity'] or 0

        self.calculate_inventory_qty()


class StockTransaction(AbstractBaseModel):
    inventory = models.ForeignKey(
        StockInventory, on_delete=models.CASCADE,
        related_name='stock_transaction'
    )
    type = models.CharField(
        choices=TransactionType.CHOICES, default=TransactionType.INWARD
    )
    quantity = models.IntegerField(
        default=0, validators=[MinValueValidator(0)]
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Stock transaction metadata"
    )
    objects = IsActiveModelManager()

    class Meta:
        verbose_name = 'Stock Inventory Transaction'
        verbose_name_plural = 'Stock Inventory Transactions'
        ordering = ('-created_at', 'inventory', )