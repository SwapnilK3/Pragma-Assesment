from django.db import models
from django.db.models import TextField, JSONField

from core.models import AbstractUUID, AbstractBaseModel, MediaFile


class Category(AbstractBaseModel):
    name = models.CharField(max_length=250)
    description = JSONField(blank=True, null=True)
    description_plaintext = TextField(blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, related_name="children", on_delete=models.CASCADE
    )
    background_image = models.ImageField(
        upload_to="category-backgrounds", blank=True, null=True
    )
    background_image_alt = models.CharField(max_length=128, blank=True)

    objects = models.Manager()

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self) -> str:
        return self.name


class SKU(AbstractUUID):
    """
    Also known as Stock Keeping Unit, this model stores the details of each SKU
    that is available for ordering.
    """
    short_name = models.CharField(max_length=128)
    description = models.TextField(null=True, blank=True)
    quantity = models.IntegerField(default=0)
    unit = models.CharField(max_length=128, null=True, blank=True)

    class Meta:
        verbose_name_plural = 'SKUs'
        verbose_name = 'SKU'
        ordering = ('short_name',)

    def __str__(self):
        return self.short_name


class Product(AbstractBaseModel):
    name = models.CharField(max_length=250)
    description = JSONField(blank=True, null=True)
    description_plaintext = TextField(blank=True)
    category = models.ForeignKey(
        Category,
        related_name="products",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    default_variant = models.OneToOneField(
        "ProductVariant",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    rating = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"


class ProductVariant(AbstractBaseModel):
    product_sku = models.ForeignKey(
        SKU,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The unit of each Product"
    )
    name = models.CharField(max_length=255, blank=True)
    product = models.ForeignKey(
        Product, related_name="variants", on_delete=models.CASCADE
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Unit price for this variant"
    )


class ProductMedia(models.Model):
    product = models.ForeignKey(
        "Product", related_name="product_media", on_delete=models.CASCADE
    )
    media = models.ForeignKey(
        MediaFile, related_name="product_media", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("product", "media")


class VariantMedia(models.Model):
    variant = models.ForeignKey(
        "ProductVariant", related_name="variant_media", on_delete=models.CASCADE
    )
    media = models.ForeignKey(
        MediaFile, related_name="variant_media", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("variant", "media")
