from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Permission, Group
from django.db import models

from core.models import AbstractUUID, AbstractMonitor, Address


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def create_user(self, email, first_name, last_name, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        if not first_name:
            raise ValueError('The First Name field must be set')
        if not last_name:
            raise ValueError('The Last Name field must be set')
        if not password:
            raise ValueError('The Password field must be set')

        email = self.normalize_email(email).lower()
        user = self.model(
            email=email,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name, last_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)


        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, first_name, last_name, password, **extra_fields)


class User(AbstractBaseUser, AbstractUUID, AbstractMonitor, PermissionsMixin):
    """
    Custom User model with UUID primary key and role-based access.
    Contains common fields for all user types.

    Inherits from:
    - AbstractUUID: UUID primary key
    - AbstractMonitor: created_at, updated_at timestamps
    """
    # Authentication
    email = models.EmailField(unique=True, db_index=True)

    # Common User Info
    first_name = models.CharField(max_length=256, blank=True)
    last_name = models.CharField(max_length=256, blank=True)
    addresses = models.ManyToManyField(
        Address, blank=True, related_name="user_addresses"
    )

    # Status
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(
        default=False,
        help_text="Flag for Staff User",
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Flag indicating if user verification (email, etc.) is complete"
    )
    is_loyalty_member = models.BooleanField(
        default=False,
        help_text="Flag indicating if user is a loyalty program member"
    )

    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(
        max_length=1,
        choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')],
        blank=True,
        null=True
    )

    is_superuser = models.BooleanField(
        default=False,
        help_text=(
            "Designates that this user has all permissions without "
            "explicitly assigning them."
        ),
    )
    groups = models.ManyToManyField(
        Group,
        blank=True,
        help_text=(
            "The groups this user belongs to. A user will get all permissions "
            "granted to each of their groups."
        ),
        related_name="pragma_user_set",
        related_query_name="pragma_user",
    )

    user_permissions = models.ManyToManyField(
        Permission,
        blank=True,
        help_text="Specific permissions for this user.",
        related_name="pragma_user_set",
        related_query_name="pragma_user",
    )

    objects = UserManager()

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    def save(self, *args, **kwargs):
        self.email = self.email.lower().strip()
        self.first_name = ' '.join(self.first_name.strip().split())
        self.last_name = ' '.join(self.last_name.strip().split())
        super().save(*args, **kwargs)

