from django.db import models, connection

from accounts.backends import User
from core import Currency
from core.models import AbstractBaseModel, Address
from orders import OrderStatus, PaymentStatus, TransactionMode
from products.models import Product, ProductVariant


def get_order_number():
    """Generate unique order number. Works with both PostgreSQL and SQLite."""

    # For PostgreSQL, use sequence
    if connection.vendor == 'postgresql':
        with connection.cursor() as cursor:
            cursor.execute("SELECT nextval('order_order_number_seq')")
            result = cursor.fetchone()
            return result[0]
    
    # For SQLite and others, use max + 1
    max_order = Order.objects.aggregate(models.Max('order_number'))['order_number__max']
    return (max_order or 0) + 1


class Order(AbstractBaseModel):
    """
    Order model for storing order details.
    It Calculates total order amount by applying/removing coupon code
    after Discounts, Tax price calculations.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_number = models.IntegerField(
        unique=True, default=get_order_number, editable=False)

    total_payable_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    total_payable_tax = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(
        max_length=64, choices=Currency.CHOICES,
        default=Currency.INR)
    order_status = models.CharField(
        max_length=64, choices=OrderStatus.CHOICES,
        default=OrderStatus.CREATED)

    payment_status = models.CharField(
        max_length=64, choices=PaymentStatus.CHOICES,
        default=PaymentStatus.PAYMENT_PENDING)

    payment_mode = models.CharField(
        max_length=20, choices=TransactionMode.CHOICES,
        default=TransactionMode.ONLINE)

    shipping_address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='shipping_address')

    # estimated_date = models.DateField(
    #     null=True, blank=True,
    #     help_text='system estimated delivered date'
    # )
    delivered_on = models.DateTimeField(
        null=True, blank=True,
        help_text='actual delivered date'
    )

    def __str__(self):
        return f"{self.id} - {self.user.id}"


class OrderItem(AbstractBaseModel):
    """
    OrderItem Model for storing the details of each item in an order.
    """
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='order_items')
    product_variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name='order_items'
    )
    quantity = models.IntegerField(
        default=1,
        help_text="ordered quantity")
    unit_rate = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=0,
        help_text='unit prise'
    )
    discounted_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    is_coupon_code_applied = models.BooleanField(default=False)

    class Meta:
        unique_together = ('order', 'product_variant')
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

    def save(self, *args, **kwargs):
        self.amount = (self.quantity * self.unit_rate) - self.discounted_amount
