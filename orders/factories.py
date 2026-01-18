import factory
from factory.django import DjangoModelFactory

from accounts.backends import User
from core.models import Address
from products.models import Category, Product, ProductVariant, SKU


class UserFactory(DjangoModelFactory):
    """Factory for User model."""

    class Meta:
        model = User

    email = factory.Faker('email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True
    is_verified = True


class CategoryFactory(DjangoModelFactory):
    """Factory for Category model."""

    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f'Category {n}')
    description = factory.Faker('sentence')
    is_active = True


class SKUFactory(DjangoModelFactory):
    """Factory for SKU model."""

    class Meta:
        model = SKU

    short_name = factory.Sequence(lambda n: f'SKU-{n:06d}')
    description = factory.Faker('sentence')
    quantity = factory.Faker('random_int', min=0, max=1000)
    unit = 'piece'


class ProductFactory(DjangoModelFactory):
    """Factory for Product model."""

    class Meta:
        model = Product

    name = factory.Faker('catch_phrase')
    description = factory.Faker('paragraph')
    category = factory.SubFactory(CategoryFactory)
    rating = factory.Faker('pydecimal', left_digits=1, right_digits=1, min_value=1, max_value=5)
    is_active = True


class ProductVariantFactory(DjangoModelFactory):
    """Factory for ProductVariant model."""

    class Meta:
        model = ProductVariant

    name = factory.LazyAttribute(lambda obj: f'{obj.product.name} - Variant')
    product = factory.SubFactory(ProductFactory)
    product_sku = factory.SubFactory(SKUFactory)
    price = factory.Faker('pydecimal', left_digits=4, right_digits=2, positive=True, min_value=10, max_value=5000)
    is_active = True


class AddressFactory(DjangoModelFactory):
    """Factory for Address model."""

    class Meta:
        model = Address

    address_line_1 = factory.Faker('street_address')
    address_line_2 = factory.Faker('secondary_address')
    city = factory.Faker('city')
    city_area = factory.Faker('city')
    country_area = factory.Faker('state')
    country = 'US'
    postal_code = factory.Faker('zipcode')
    phone = '+12025551234'
    validation_skipped = False
    is_active = True
