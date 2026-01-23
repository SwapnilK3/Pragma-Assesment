"""
Tests for Inventory app ViewSets and Serializers.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from inventory.models import StockInventory, StockTransaction
from inventory import TransactionType
from products.models import Category, SKU, Product, ProductVariant


class StockInventoryViewSetTest(APITestCase):
    """Tests for StockInventoryViewSet CRUD operations."""

    def setUp(self):
        # Clear existing data to ensure test isolation
        StockTransaction.objects.all().delete()
        StockInventory.objects.all().delete()
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
            name="128GB",
            product=self.product,
            product_sku=self.sku,
            price=999.99
        )
        # Use all_objects to bypass IsActiveModelManager for test setup
        self.inventory = StockInventory.objects.create(
            product_variant=self.variant,
            total_quantity=100,
            reserved_quantity=10
        )

    def test_list_inventory(self):
        """Test listing all stock inventory."""
        url = reverse('stock-inventory-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Handle paginated response
        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(data), 1)

    def test_retrieve_inventory(self):
        """Test retrieving a single inventory item."""
        url = reverse('stock-inventory-detail', args=[self.inventory.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_quantity'], 100)
        self.assertEqual(response.data['reserved_quantity'], 10)
        self.assertEqual(response.data['remaining_quantity'], 90)

    def test_create_inventory(self):
        """Test creating stock inventory."""
        new_product = Product.objects.create(name="Samsung", category=self.category)

        url = reverse('stock-inventory-list')
        data = {
            'product': str(new_product.id),
            'total_quantity': 50,
            'reserved_quantity': 5
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])

    def test_create_inventory_with_initial_quantity(self):
        """Test creating inventory with initial INWARD transaction."""
        new_product = Product.objects.create(name="Pixel", category=self.category)

        url = reverse('stock-inventory-list')
        data = {
            'product': str(new_product.id),
            'initial_quantity': 200
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Check transaction was created
        inventory = StockInventory.objects.get(product=new_product)
        self.assertEqual(inventory.stock_transaction.count(), 1)
        self.assertEqual(
            inventory.stock_transaction.first().type,
            TransactionType.INWARD
        )

    def test_update_inventory(self):
        """Test updating stock inventory."""
        url = reverse('stock-inventory-detail', args=[self.inventory.id])
        data = {'total_quantity': 150}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.total_quantity, 150)

    def test_delete_inventory(self):
        """Test soft deleting stock inventory."""
        url = reverse('stock-inventory-detail', args=[self.inventory.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.inventory.refresh_from_db()
        self.assertFalse(self.inventory.is_active)

    def test_add_stock_action(self):
        """Test adding stock via custom action."""
        url = reverse('stock-inventory-add-stock', args=[self.inventory.id])
        data = {
            'quantity': 50,
            'metadata': {'note': 'Restocking'}
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        # Check transaction was created
        self.assertEqual(self.inventory.stock_transaction.count(), 1)

    def test_add_stock_invalid_quantity(self):
        """Test adding stock with invalid quantity."""
        url = reverse('stock-inventory-add-stock', args=[self.inventory.id])
        data = {'quantity': 0}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_low_stock_action(self):
        """Test getting low stock items."""
        # Create low stock item
        low_stock_product = Product.objects.create(name="Low Stock Item", category=self.category)
        StockInventory.objects.create(
            product=low_stock_product,
            total_quantity=5,
            reserved_quantity=0
        )

        url = reverse('stock-inventory-low-stock')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have 1 low stock item (remaining < 10)
        self.assertEqual(len(response.data), 1)

    def test_filter_by_product(self):
        """Test filtering inventory by product."""
        url = reverse('stock-inventory-list') + f'?product_variant={self.variant.id}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(data), 1)


class StockTransactionViewSetTest(APITestCase):
    """Tests for StockTransactionViewSet operations."""

    def setUp(self):
        # Clear existing data to ensure test isolation
        StockTransaction.objects.all().delete()
        StockInventory.objects.all().delete()
        ProductVariant.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()

        self.category = Category.objects.create(name="Electronics")
        self.product = Product.objects.create(name="iPhone", category=self.category)
        self.inventory = StockInventory.objects.create(
            product=self.product,
            total_quantity=100
        )
        self.transaction = StockTransaction.objects.create(
            inventory=self.inventory,
            type=TransactionType.INWARD,
            quantity=50,
            metadata={'note': 'Initial stock'}
        )

    def test_list_transactions(self):
        """Test listing all transactions."""
        url = reverse('stock-transaction-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(data), 1)

    def test_retrieve_transaction(self):
        """Test retrieving a single transaction."""
        url = reverse('stock-transaction-detail', args=[self.transaction.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['quantity'], 50)
        self.assertEqual(response.data['type'], TransactionType.INWARD)

    def test_create_transaction(self):
        """Test creating a transaction."""
        url = reverse('stock-transaction-list')
        data = {
            'inventory': str(self.inventory.id),
            'type': TransactionType.INWARD,
            'quantity': 25,
            'metadata': {'note': 'Additional stock'}
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(StockTransaction.objects.count(), 2)

    def test_create_transaction_invalid_quantity(self):
        """Test creating transaction with invalid quantity."""
        url = reverse('stock-transaction-list')
        data = {
            'inventory': str(self.inventory.id),
            'type': TransactionType.INWARD,
            'quantity': 0
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_transaction(self):
        """Test soft deleting a transaction."""
        url = reverse('stock-transaction-detail', args=[self.transaction.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.transaction.refresh_from_db()
        self.assertFalse(self.transaction.is_active)

    def test_filter_by_inventory(self):
        """Test filtering transactions by inventory."""
        url = reverse('stock-transaction-list') + f'?inventory={self.inventory.id}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(data), 1)

    def test_filter_by_type(self):
        """Test filtering transactions by type."""
        url = reverse('stock-transaction-list') + f'?type={TransactionType.INWARD}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual(len(data), 1)

