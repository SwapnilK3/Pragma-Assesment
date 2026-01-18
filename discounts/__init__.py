class DiscountScope:
    ORDER = 'order'
    ITEM = 'item'
    CATEGORY = 'category'

    CHOICES = (
        (ORDER, 'Order'),
        (ITEM, 'Item'),
        (CATEGORY, 'Category')
    )

class DiscountType:
    FIX = 'fix'
    PERCENTAGE = 'percentage'

    CHOICES = (
        (FIX, 'Fix'),
        (PERCENTAGE, 'Percentage'),
    )

