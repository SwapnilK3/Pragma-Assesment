"""
Tests for Products app ViewSets and Serializers.
"""
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from products.models import Category, SKU, Product, ProductVariant, ProductMedia, VariantMedia
from core.models import MediaFile


class CategoryViewSetTest(APITestCase):
    """Tests for CategoryViewSet (read-only)."""

    def setUp(self):
        # Clear existing data
        Category.objects.all().delete()

        self.parent_category = Category.objects.create(
            name="Electronics",
            description_plaintext="Electronic items"
        )
        self.child_category = Category.objects.create(
            name="Phones",
            description_plaintext="Mobile phones",
            parent=self.parent_category
        )

    def test_list_categories(self):
        """Test listing all categories."""
        url = reverse('category-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Handle both paginated and non-paginated responses
        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(data), 2)

    def test_retrieve_category(self):
        """Test retrieving a single category."""
        url = reverse('category-detail', args=[self.parent_category.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Electronics')

    def test_category_tree(self):
        """Test getting category tree (root categories only)."""
        url = reverse('category-tree')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Only parent (root)
        self.assertEqual(response.data[0]['name'], 'Electronics')

    def test_search_categories(self):
        """Test searching categories by name."""
        url = reverse('category-list') + '?search=Phones'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Phones')


class SKUViewSetTest(APITestCase):
    """Tests for SKUViewSet (read-only)."""

    def setUp(self):
        SKU.objects.all().delete()
        self.sku = SKU.objects.create(
            short_name="PC-001",
            description="Piece unit",
            quantity=1,
            unit="piece"
        )

    def test_list_skus(self):
        """Test listing all SKUs."""
        url = reverse('sku-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(data), 1)

    def test_retrieve_sku(self):
        """Test retrieving a single SKU."""
        url = reverse('sku-detail', args=[self.sku.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['short_name'], 'PC-001')


class ProductViewSetTest(APITestCase):
    """Tests for ProductViewSet CRUD operations."""

    def setUp(self):
        ProductVariant.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        SKU.objects.all().delete()

        self.category = Category.objects.create(
            name="Electronics",
            description_plaintext="Electronic items"
        )
        self.sku = SKU.objects.create(
            short_name="PC-001",
            description="Piece unit"
        )
        self.product = Product.objects.create(
            name="iPhone 15",
            description_plaintext="Latest iPhone",
            category=self.category,
            rating=4.5
        )

    def test_list_products(self):
        """Test listing all products."""
        url = reverse('product-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'iPhone 15')

    def test_retrieve_product(self):
        """Test retrieving a single product with details."""
        url = reverse('product-detail', args=[self.product.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'iPhone 15')
        self.assertEqual(response.data['category_name'], 'Electronics')

    def test_create_product(self):
        """Test creating a product."""
        url = reverse('product-list')
        data = {
            'name': 'Samsung Galaxy',
            'description_plaintext': 'Android phone',
            'category': str(self.category.id),
            'rating': 4.2
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['name'], 'Samsung Galaxy')
        self.assertEqual(Product.objects.count(), 2)

    def test_create_product_with_media(self):
        """Test creating a product with media URLs."""
        url = reverse('product-list')
        data = {
            'name': 'Pixel Phone',
            'description_plaintext': 'Google phone',
            'category': str(self.category.id),
            'media_urls': [
                'https://example.com/image1.jpg',
                'https://example.com/image2.png'
            ]
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        product = Product.objects.get(name='Pixel Phone')
        self.assertEqual(ProductMedia.objects.filter(product=product).count(), 2)

    def test_create_product_with_variants(self):
        """Test creating a product with nested variants."""
        url = reverse('product-list')
        data = {
            'name': 'OnePlus',
            'description_plaintext': 'OnePlus phone',
            'category': str(self.category.id),
            'variants_data': [
                {
                    'name': '128GB',
                    'price': 699.99,
                    'product_sku': str(self.sku.id)
                },
                {
                    'name': '256GB',
                    'price': 799.99,
                    'product_sku': str(self.sku.id)
                }
            ]
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        product = Product.objects.get(name='OnePlus')
        self.assertEqual(product.variants.count(), 2)

    def test_update_product(self):
        """Test updating a product."""
        url = reverse('product-detail', args=[self.product.id])
        data = {
            'name': 'iPhone 15 Pro',
            'rating': 4.8
        }
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'iPhone 15 Pro')
        self.assertEqual(float(self.product.rating), 4.8)

    def test_delete_product(self):
        """Test soft deleting a product."""
        url = reverse('product-detail', args=[self.product.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_active)

    def test_filter_by_category(self):
        """Test filtering products by category."""
        url = reverse('product-list') + f'?category={self.category.id}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(data), 1)

    def test_search_products(self):
        """Test searching products by name."""
        url = reverse('product-list') + '?search=iPhone'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(data), 1)


class ProductVariantViewSetTest(APITestCase):
    """Tests for ProductVariantViewSet CRUD operations."""

    def setUp(self):
        ProductVariant.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        SKU.objects.all().delete()

        self.category = Category.objects.create(name="Electronics")
        self.sku = SKU.objects.create(short_name="PC-001")
        self.product = Product.objects.create(
            name="iPhone 15",
            category=self.category
        )
        self.variant = ProductVariant.objects.create(
            name="128GB Black",
            product=self.product,
            product_sku=self.sku,
            price=Decimal('999.99')
        )

    def test_list_variants(self):
        """Test listing all variants."""
        url = reverse('product-variant-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(data), 1)

    def test_retrieve_variant(self):
        """Test retrieving a single variant."""
        url = reverse('product-variant-detail', args=[self.variant.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], '128GB Black')
        self.assertEqual(response.data['sku_name'], 'PC-001')

    def test_create_variant(self):
        """Test creating a variant."""
        url = reverse('product-variant-list')
        data = {
            'name': '256GB White',
            'product': str(self.product.id),
            'product_sku': str(self.sku.id),
            'price': 1099.99
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(ProductVariant.objects.count(), 2)

    def test_create_variant_with_media(self):
        """Test creating a variant with media URLs."""
        url = reverse('product-variant-list')
        data = {
            'name': '512GB Gold',
            'product': str(self.product.id),
            'product_sku': str(self.sku.id),
            'price': 1299.99,
            'media_urls': ['https://example.com/variant1.jpg']
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        variant = ProductVariant.objects.get(name='512GB Gold')
        self.assertEqual(VariantMedia.objects.filter(variant=variant).count(), 1)

    def test_update_variant(self):
        """Test updating a variant."""
        url = reverse('product-variant-detail', args=[self.variant.id])
        data = {'price': 899.99}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.price, Decimal('899.99'))

    def test_delete_variant(self):
        """Test soft deleting a variant."""
        url = reverse('product-variant-detail', args=[self.variant.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.variant.refresh_from_db()
        self.assertFalse(self.variant.is_active)

    def test_filter_by_product(self):
        """Test filtering variants by product."""
        url = reverse('product-variant-list') + f'?product={self.product.id}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(data), 1)

