class OrderStatus:
    CREATED = 'created'
    SCHEDULED = 'scheduled'
    HANDED_OVER = 'handed_over'
    CANCELLED = 'cancelled'

    CHOICES = (
        (CREATED, 'Created'),
        (SCHEDULED, 'Scheduled'),
        (HANDED_OVER, 'Handed Over'),
        (CANCELLED, 'Cancelled')
    )


class PaymentStatus:
    PAID = 'paid'
    PAYMENT_PENDING = 'payment_pending'
    PENDING_REFUND = 'payment_refund'
    PAYMENT_REFUNDED = 'payment_refunded'

    CHOICES = (
        (PAID, 'Paid'),
        (PAYMENT_PENDING, 'Payment Pending'),
        (PENDING_REFUND, 'Payment Refund'),
        (PAYMENT_REFUNDED, 'Payment Refunded'),
    )


class PaymentMode:
    UPI = "upi"
    ONLINE = "online"
    BANK_TRANSFER = "bank_transfer"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    CASH = "cash"
    OTHER = "other"

    CHOICES = (
        (UPI, 'UPI'),
        (ONLINE, 'Online'),
        (BANK_TRANSFER, 'Bank Transfer'),
        (CREDIT_CARD, 'Credit Card'),
        (DEBIT_CARD, 'Debit Card'),
        (CASH, 'Cash'),
        (OTHER, 'Other')
    )
