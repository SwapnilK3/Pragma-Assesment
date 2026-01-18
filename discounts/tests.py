from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from accounts.backends import User
from products.models import Category, ProductVariant, Product
from discounts.models import DiscountRule, AppliedDiscount
from discounts.factories import DiscountRuleFactory
from orders.factories import UserFactory, CategoryFactory, ProductFactory, ProductVariantFactory


class DiscountRuleAPITest(APITestCase):
    """Test cases for DiscountRule API endpoints."""
    
    def setUp(self):
        """Set up test data before each test."""
        self.client = APIClient()
        
        # Create admin user
        self.admin_user = UserFactory(email='admin@example.com', is_staff=True, is_superuser=True)
        self.admin_user.set_password('adminpass123')
        self.admin_user.save()
        
        # Create regular user
        self.regular_user = UserFactory(email='user@example.com')
        self.regular_user.set_password('userpass123')
        self.regular_user.save()
        
        # Create category and product for testing
        self.category = CategoryFactory(name='Electronics')
        self.product = ProductFactory(name='Test Product', category=self.category)
        self.variant = ProductVariantFactory(product=self.product, price=Decimal('100.00'))
        
        # Create some discount rules
        self.order_discount = DiscountRuleFactory(
            name='10% Order Discount',
            scope='order',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_order_amount=Decimal('100.00')
        )
        
        self.category_discount = DiscountRuleFactory(
            name='Electronics 15% Off',
            scope='category',
            discount_type='percentage',
            discount_value=Decimal('15.00'),
            categories=self.category
        )
        
        self.item_discount = DiscountRuleFactory(
            name='$20 Off Product',
            scope='item',
            discount_type='fix',
            discount_value=Decimal('20.00'),
            product_variant=self.variant
        )
    
    def authenticate_admin(self):
        """Authenticate as admin user."""
        self.client.force_authenticate(user=self.admin_user)
    
    def authenticate_user(self):
        """Authenticate as regular user."""
        self.client.force_authenticate(user=self.regular_user)
    
    # ==================== LIST Tests ====================
    
    def test_list_discount_rules_as_admin(self):
        """Test listing discount rules as admin."""
        self.authenticate_admin()
        url = reverse('discount-rule-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 3)
    
    def test_list_discount_rules_as_regular_user(self):
        """Test that regular users cannot list discount rules."""
        self.authenticate_user()
        url = reverse('discount-rule-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_list_discount_rules_unauthenticated(self):
        """Test that unauthenticated users cannot list discount rules."""
        url = reverse('discount-rule-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_list_discount_rules_filter_by_scope(self):
        """Test filtering discount rules by scope."""
        self.authenticate_admin()
        url = reverse('discount-rule-list')
        response = self.client.get(url, {'scope': 'order'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['scope'], 'order')
    
    def test_list_discount_rules_filter_by_discount_type(self):
        """Test filtering discount rules by discount type."""
        self.authenticate_admin()
        url = reverse('discount-rule-list')
        response = self.client.get(url, {'discount_type': 'fix'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['discount_type'], 'fix')
    
    # ==================== CREATE Tests ====================
    
    def test_create_order_discount_rule(self):
        """Test creating an order-level discount rule."""
        self.authenticate_admin()
        url = reverse('discount-rule-list')
        
        payload = {
            'name': 'New Year Sale',
            'scope': 'order',
            'discount_type': 'percentage',
            'discount_value': '25.00',
            'min_order_amount': '500.00',
            'start_date': timezone.now().isoformat(),
            'end_date': (timezone.now() + timedelta(days=7)).isoformat()
        }
        
        response = self.client.post(url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['name'], 'New Year Sale')
        self.assertEqual(response.data['data']['scope'], 'order')
        self.assertEqual(Decimal(response.data['data']['discount_value']), Decimal('25.00'))
    
    def test_create_category_discount_rule(self):
        """Test creating a category-level discount rule."""
        self.authenticate_admin()
        url = reverse('discount-rule-list')
        
        payload = {
            'name': 'Electronics Sale',
            'scope': 'category',
            'discount_type': 'percentage',
            'discount_value': '20.00',
            'categories': str(self.category.id),
            'start_date': timezone.now().isoformat()
        }
        
        response = self.client.post(url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['scope'], 'category')
    
    def test_create_item_discount_rule(self):
        """Test creating an item-level discount rule."""
        self.authenticate_admin()
        url = reverse('discount-rule-list')
        
        payload = {
            'name': 'Product Special',
            'scope': 'item',
            'discount_type': 'fix',
            'discount_value': '50.00',
            'product_variant': str(self.variant.id),
            'min_quantity': '2',
            'start_date': timezone.now().isoformat()
        }
        
        response = self.client.post(url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['scope'], 'item')
    
    def test_create_discount_rule_without_optional_fields(self):
        """Test creating a discount rule with only required fields."""
        self.authenticate_admin()
        url = reverse('discount-rule-list')
        
        payload = {
            'name': 'Simple Discount',
            'scope': 'order',
            'discount_type': 'fix',
            'discount_value': '10.00',
            'start_date': timezone.now().isoformat()
        }
        
        response = self.client.post(url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Verify optional fields are null
        self.assertIsNone(response.data['data']['min_order_amount'])
        self.assertIsNone(response.data['data']['min_quantity'])
        self.assertIsNone(response.data['data']['end_date'])
    
    def test_create_discount_rule_invalid_percentage(self):
        """Test that percentage discount value must be between 0 and 100."""
        self.authenticate_admin()
        url = reverse('discount-rule-list')
        
        payload = {
            'name': 'Invalid Discount',
            'scope': 'order',
            'discount_type': 'percentage',
            'discount_value': '150.00',  # Invalid - over 100%
            'start_date': timezone.now().isoformat()
        }
        
        response = self.client.post(url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
    
    def test_create_category_discount_without_category(self):
        """Test that category-scoped discounts require a category."""
        self.authenticate_admin()
        url = reverse('discount-rule-list')
        
        payload = {
            'name': 'Invalid Category Discount',
            'scope': 'category',
            'discount_type': 'percentage',
            'discount_value': '10.00',
            'start_date': timezone.now().isoformat()
            # Missing categories field
        }
        
        response = self.client.post(url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
    
    def test_create_item_discount_without_variant(self):
        """Test that item-scoped discounts require a product variant."""
        self.authenticate_admin()
        url = reverse('discount-rule-list')
        
        payload = {
            'name': 'Invalid Item Discount',
            'scope': 'item',
            'discount_type': 'fix',
            'discount_value': '10.00',
            'start_date': timezone.now().isoformat()
            # Missing product_variant field
        }
        
        response = self.client.post(url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
    
    # ==================== RETRIEVE Tests ====================
    
    def test_retrieve_discount_rule(self):
        """Test retrieving a specific discount rule."""
        self.authenticate_admin()
        url = reverse('discount-rule-detail', kwargs={'pk': self.order_discount.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['name'], '10% Order Discount')
    
    def test_retrieve_nonexistent_discount_rule(self):
        """Test retrieving a non-existent discount rule."""
        self.authenticate_admin()
        url = reverse('discount-rule-detail', kwargs={'pk': '00000000-0000-0000-0000-000000000000'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data['success'])
    
    # ==================== UPDATE Tests ====================
    
    def test_update_discount_rule(self):
        """Test updating a discount rule."""
        self.authenticate_admin()
        url = reverse('discount-rule-detail', kwargs={'pk': self.order_discount.id})
        
        payload = {
            'name': 'Updated Order Discount',
            'scope': 'order',
            'discount_type': 'percentage',
            'discount_value': '20.00',
            'min_order_amount': '200.00',
            'start_date': timezone.now().isoformat()
        }
        
        response = self.client.put(url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['name'], 'Updated Order Discount')
        self.assertEqual(Decimal(response.data['data']['discount_value']), Decimal('20.00'))
    
    def test_partial_update_discount_rule(self):
        """Test partially updating a discount rule."""
        self.authenticate_admin()
        url = reverse('discount-rule-detail', kwargs={'pk': self.order_discount.id})
        
        payload = {
            'discount_value': '30.00'
        }
        
        response = self.client.patch(url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(Decimal(response.data['data']['discount_value']), Decimal('30.00'))
        # Original name should be preserved
        self.assertEqual(response.data['data']['name'], '10% Order Discount')
    
    def test_update_discount_rule_toggle_active(self):
        """Test toggling a discount rule's active status."""
        self.authenticate_admin()
        url = reverse('discount-rule-detail', kwargs={'pk': self.order_discount.id})
        
        payload = {
            'is_active': False
        }
        
        response = self.client.patch(url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['data']['is_active'])
    
    # ==================== DELETE Tests ====================
    
    def test_delete_discount_rule(self):
        """Test soft deleting a discount rule."""
        self.authenticate_admin()
        url = reverse('discount-rule-detail', kwargs={'pk': self.order_discount.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify it's soft deleted (is_active = False)
        self.order_discount.refresh_from_db()
        self.assertFalse(self.order_discount.is_active)
    
    # ==================== ACTIVE Action Tests ====================
    
    def test_get_active_discount_rules(self):
        """Test getting only active and currently valid discount rules."""
        self.authenticate_admin()
        
        # Create an expired discount
        expired_discount = DiscountRuleFactory(
            name='Expired Discount',
            start_date=timezone.now() - timedelta(days=30),
            end_date=timezone.now() - timedelta(days=1),
            is_active=True
        )
        
        # Create an inactive discount
        inactive_discount = DiscountRuleFactory(
            name='Inactive Discount',
            is_active=False
        )
        
        url = reverse('discount-rule-active')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Should only return active, non-expired discounts
        names = [d['name'] for d in response.data['data']]
        self.assertNotIn('Expired Discount', names)
        self.assertNotIn('Inactive Discount', names)


class DiscountRuleModelTest(TestCase):
    """Test cases for DiscountRule model."""
    
    def setUp(self):
        """Set up test data."""
        self.category = CategoryFactory()
        self.product = ProductFactory(category=self.category)
        self.variant = ProductVariantFactory(product=self.product)
    
    def test_create_order_discount_rule(self):
        """Test creating an order discount rule."""
        rule = DiscountRule.objects.create(
            name='Test Order Discount',
            scope='order',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_order_amount=Decimal('100.00')
        )
        
        self.assertEqual(rule.scope, 'order')
        self.assertEqual(rule.discount_type, 'percentage')
        self.assertEqual(rule.discount_value, Decimal('10.00'))
        self.assertTrue(rule.is_active)
    
    def test_create_category_discount_rule(self):
        """Test creating a category discount rule."""
        rule = DiscountRule.objects.create(
            name='Test Category Discount',
            scope='category',
            discount_type='fix',
            discount_value=Decimal('50.00'),
            categories=self.category
        )
        
        self.assertEqual(rule.categories, self.category)
    
    def test_create_item_discount_rule(self):
        """Test creating an item discount rule."""
        rule = DiscountRule.objects.create(
            name='Test Item Discount',
            scope='item',
            discount_type='percentage',
            discount_value=Decimal('25.00'),
            product_variant=self.variant,
            min_quantity=Decimal('2')
        )
        
        self.assertEqual(rule.product_variant, self.variant)
        self.assertEqual(rule.min_quantity, Decimal('2'))
    
    def test_discount_rule_optional_fields(self):
        """Test that optional fields can be null."""
        rule = DiscountRule.objects.create(
            name='Minimal Rule',
            scope='order',
            discount_type='fix',
            discount_value=Decimal('10.00')
        )
        
        self.assertIsNone(rule.min_order_amount)
        self.assertIsNone(rule.min_quantity)
        self.assertIsNone(rule.categories)
        self.assertIsNone(rule.product_variant)
        self.assertIsNone(rule.end_date)

