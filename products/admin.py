from django.contrib import admin
from products.models import (
    Category,
    SKU,
    Product,
    ProductVariant,
    ProductMedia,
    VariantMedia,
)

# Register product-related models
admin.site.register([Category, SKU, Product, ProductVariant, ProductMedia, VariantMedia])
