"""
Core models module containing abstract base classes.
All models in the application should inherit from these base classes.

Usage:
    - AbstractUUID: Provides UUID primary key
    - AbstractMonitor: Provides created_at and updated_at timestamps
    - AbstractActive: Provides is_active soft delete functionality
    - AbstractBaseModel: Combines all three (UUID + Monitor + Active)
"""
import uuid

from django.db import models
from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField

from . import MediaType, MediaAccess
from .validators import validate_possible_number


class ActiveManager(models.Manager):
    """Manager that returns only active (non-deleted) records."""

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class AbstractUUID(models.Model):
    """
    Abstract base model that provides UUID primary key.
    Inherit from this when you need UUID as primary key.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this record"
    )

    class Meta:
        abstract = True


class AbstractMonitor(models.Model):
    """
    Abstract base model that provides timestamp fields.
    Inherit from this when you need created_at and updated_at tracking.
    """
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the record was last updated"
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']


class AbstractActive(models.Model):
    """
    Abstract base model that provides soft delete functionality.
    Inherit from this when you need is_active flag for soft deletion.
    """
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Soft delete flag. Set to False to deactivate."
    )

    # Managers
    objects = ActiveManager()

    class Meta:
        abstract = True

    def soft_delete(self):
        """Soft delete the record by setting is_active to False."""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'] if hasattr(self, 'updated_at') else ['is_active'])


class AbstractBaseModel(AbstractUUID, AbstractMonitor, AbstractActive):
    """
    Complete abstract base model combining:
    - UUID primary key
    - created_at / updated_at timestamps
    - is_active soft delete flag

    Use this as the default base for most models.
    """

    class Meta:
        abstract = True
        ordering = ['-created_at']


class PossiblePhoneNumberField(PhoneNumberField):
    """Less strict field for phone numbers written to database."""

    default_validators = [validate_possible_number]


class Address(AbstractUUID, AbstractActive):
    """
    Address Model
    """
    address_line_1 = models.CharField(max_length=256)
    address_line_2 = models.CharField(max_length=256, null=True, blank=True)
    city = models.CharField(max_length=256)
    city_area = models.CharField(max_length=128, null=True, blank=True)
    postal_code = models.CharField(max_length=20)
    country = CountryField()
    country_area = models.CharField(max_length=128, null=True, blank=True)
    phone = PossiblePhoneNumberField(blank=True, default="", db_index=True)
    validation_skipped = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.city} - {self.country_area} - {self.country.name} - {self.postal_code}"

    class Meta:
        verbose_name_plural = 'Addresses'
        verbose_name = 'Address'

    @property
    def address_string(self):
        address_parts = [
            self.address_line_1,
            self.address_line_2,
            self.city,
            self.city_area,
            self.country.name,
            self.country_area,
            self.postal_code if self.postal_code else ""
        ]

        # Filtering out None or empty values
        filtered_parts = list(filter(None, address_parts))

        # Joining the filtered list into a single string
        return ", ".join(filtered_parts)


class MediaFile(AbstractBaseModel):
    media_type = models.CharField(
        max_length=50, choices=MediaType.CHOICES, default=MediaType.FILE
    )
    extension = models.CharField(max_length=50, null=True, blank=True)
    url = models.URLField()
    access = models.CharField(
        max_length=50, choices=MediaAccess.CHOICES, default=MediaAccess.PROTECTED
    )

    class Meta:
        verbose_name = "MediaFile"
        verbose_name_plural = "MediaFiles"

    def __str__(self):
        return f"{self.id} - {self.url}"

# class Currency(AbstractUUID, AbstractActive):
#     name = models.CharField(max_length=50, unique=True)
#     short_name = models.CharField(max_length=50)
#     symbol = models.CharField(max_length=50, null=True, blank=True)
#
#     class Meta:
#         db_table = "currency"
#         verbose_name = "Currency"
#         verbose_name_plural = "Currencies"
#
#     def __str__(self):
#         return self.name
