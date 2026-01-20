from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from discounts.cache import (
    invalidate_all_discount_caches,
    cache_active_discount_rule_ids,
    get_cached_active_discount_rule_ids,
    invalidate_discount_cache,
    ACTIVE_RULES_CACHE_KEY,
    LOYALTY_RULES_CACHE_KEY,
    cache_loyalty_discount_rule_ids,
    get_cached_loyalty_discount_rule_ids
)
from discounts.factories import DiscountRuleFactory
from discounts.models import DiscountRule, AppliedDiscount
from discounts.utils import get_discount_amount
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


class DiscountEngineTest(TestCase):
    """Test cases for the discount calculation engine in utils.py."""

    def setUp(self):
        """Set up test data."""

        # Create user
        self.user = UserFactory(email='customer@example.com', is_loyalty_member=False)
        self.loyalty_user = UserFactory(email='vip@example.com', is_loyalty_member=True)

        # Create categories
        self.electronics = CategoryFactory(name='Electronics')
        self.clothing = CategoryFactory(name='Clothing')

        # Create products and variants
        self.laptop = ProductFactory(name='Laptop', category=self.electronics)
        self.laptop_variant = ProductVariantFactory(
            product=self.laptop,
            price=Decimal('1000.00')
        )

        self.phone = ProductFactory(name='Phone', category=self.electronics)
        self.phone_variant = ProductVariantFactory(
            product=self.phone,
            price=Decimal('500.00')
        )

        self.shirt = ProductFactory(name='Shirt', category=self.clothing)
        self.shirt_variant = ProductVariantFactory(
            product=self.shirt,
            price=Decimal('50.00')
        )

    def create_order_with_items(self, user, items):
        """
        Helper to create an order with items.
        items: list of (variant, quantity, unit_rate) tuples
        """
        from orders.models import Order, OrderItem

        # Create order without triggering save (to avoid discount calculation)
        order = Order.objects.create(
            user=user,
            total_payable_amount=Decimal('0'),
            discount_amount=Decimal('0'),
            total_payable_tax=Decimal('0')
        )

        for variant, quantity, unit_rate in items:
            OrderItem.objects.create(
                order=order,
                product_variant=variant,
                quantity=quantity,
                unit_rate=unit_rate
            )

        return order

    def test_no_discount_when_no_rules(self):
        """Test that no discount is applied when there are no discount rules."""

        order = self.create_order_with_items(self.user, [
            (self.laptop_variant, 1, Decimal('1000.00'))
        ])

        discount = get_discount_amount(order)
        self.assertEqual(discount, Decimal('0'))

    def test_order_percentage_discount(self):
        """Test order-level percentage discount."""

        # Create 10% order discount
        DiscountRuleFactory(
            name='10% Off Orders',
            scope='order',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            is_active=True,
            is_stackable=True
        )

        # Order total: $1000
        order = self.create_order_with_items(self.user, [
            (self.laptop_variant, 1, Decimal('1000.00'))
        ])

        discount = get_discount_amount(order)
        self.assertEqual(discount, Decimal('100.00'))

    def test_order_fixed_discount(self):
        """Test order-level fixed discount."""

        # Create $50 fixed order discount
        DiscountRuleFactory(
            name='$50 Off Orders',
            scope='order',
            discount_type='fix',
            discount_value=Decimal('50.00'),
            is_active=True,
            is_stackable=True
        )

        # Order total: $1000
        order = self.create_order_with_items(self.user, [
            (self.laptop_variant, 1, Decimal('1000.00'))
        ])

        discount = get_discount_amount(order)
        self.assertEqual(discount, Decimal('50.00'))

    def test_min_order_amount_not_met(self):
        """Test discount not applied when min_order_amount is not met."""

        # Create discount requiring min $500 order
        DiscountRuleFactory(
            name='10% Off $500+',
            scope='order',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_order_amount=Decimal('500.00'),
            is_active=True
        )

        # Order total: $50 (less than $500)
        order = self.create_order_with_items(self.user, [
            (self.shirt_variant, 1, Decimal('50.00'))
        ])

        discount = get_discount_amount(order)
        self.assertEqual(discount, Decimal('0'))

    def test_min_order_amount_met(self):
        """Test discount applied when min_order_amount is met."""

        # Create discount requiring min $500 order
        DiscountRuleFactory(
            name='10% Off $500+',
            scope='order',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            min_order_amount=Decimal('500.00'),
            is_active=True,
            is_stackable=True
        )

        # Order total: $1000 (>= $500)
        order = self.create_order_with_items(self.user, [
            (self.laptop_variant, 1, Decimal('1000.00'))
        ])

        discount = get_discount_amount(order)
        self.assertEqual(discount, Decimal('100.00'))

    def test_category_percentage_discount(self):
        """Test category-level percentage discount."""

        # Create 15% discount on Electronics
        DiscountRuleFactory(
            name='15% Off Electronics',
            scope='category',
            discount_type='percentage',
            discount_value=Decimal('15.00'),
            categories=self.electronics,
            is_active=True,
            is_stackable=True
        )

        # Order: $1000 laptop + $50 shirt = $1050
        # Only laptop qualifies for category discount
        order = self.create_order_with_items(self.user, [
            (self.laptop_variant, 1, Decimal('1000.00')),
            (self.shirt_variant, 1, Decimal('50.00'))
        ])

        discount = get_discount_amount(order)
        # 15% of $1000 = $150
        self.assertEqual(discount, Decimal('150.00'))

    def test_category_fixed_discount(self):
        """Test category-level fixed discount."""

        # Create $100 fixed discount on Electronics
        DiscountRuleFactory(
            name='$100 Off Electronics',
            scope='category',
            discount_type='fix',
            discount_value=Decimal('100.00'),
            categories=self.electronics,
            is_active=True,
            is_stackable=True
        )

        # Order: $1500 electronics
        order = self.create_order_with_items(self.user, [
            (self.laptop_variant, 1, Decimal('1000.00')),
            (self.phone_variant, 1, Decimal('500.00'))
        ])

        discount = get_discount_amount(order)
        self.assertEqual(discount, Decimal('100.00'))

    def test_category_min_quantity_not_met(self):
        """Test category discount not applied when min_quantity is not met."""

        # Create discount requiring min 3 items in category
        DiscountRuleFactory(
            name='10% Off 3+ Electronics',
            scope='category',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            categories=self.electronics,
            min_quantity=Decimal('3'),
            is_active=True
        )

        # Only 2 electronics items
        order = self.create_order_with_items(self.user, [
            (self.laptop_variant, 1, Decimal('1000.00')),
            (self.phone_variant, 1, Decimal('500.00'))
        ])

        discount = get_discount_amount(order)
        self.assertEqual(discount, Decimal('0'))

    def test_item_percentage_discount(self):
        """Test item-level percentage discount."""

        # Create 20% discount on laptop
        DiscountRuleFactory(
            name='20% Off Laptop',
            scope='item',
            discount_type='percentage',
            discount_value=Decimal('20.00'),
            product_variant=self.laptop_variant,
            is_active=True,
            is_stackable=True
        )

        # Order: $1000 laptop + $500 phone
        order = self.create_order_with_items(self.user, [
            (self.laptop_variant, 1, Decimal('1000.00')),
            (self.phone_variant, 1, Decimal('500.00'))
        ])

        discount = get_discount_amount(order)
        # 20% of $1000 = $200
        self.assertEqual(discount, Decimal('200.00'))

    def test_item_min_quantity_met(self):
        """Test item discount applied when min_quantity is met."""

        # Create discount requiring min 2 of same item
        DiscountRuleFactory(
            name='10% Off 2+ Shirts',
            scope='item',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            product_variant=self.shirt_variant,
            min_quantity=Decimal('2'),
            is_active=True,
            is_stackable=True
        )

        # Buy 3 shirts
        order = self.create_order_with_items(self.user, [
            (self.shirt_variant, 3, Decimal('50.00'))  # Total: $150
        ])

        discount = get_discount_amount(order)
        # 10% of $150 = $15
        self.assertEqual(discount, Decimal('15.00'))

    def test_loyalty_discount_for_member(self):
        """Test loyalty-only discount is applied for loyalty members."""

        # Create loyalty-only discount
        DiscountRuleFactory(
            name='VIP 10% Off',
            scope='order',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            requires_loyalty=True,
            is_active=True,
            is_stackable=True
        )

        # Loyalty member order
        order = self.create_order_with_items(self.loyalty_user, [
            (self.laptop_variant, 1, Decimal('1000.00'))
        ])

        discount = get_discount_amount(order)
        self.assertEqual(discount, Decimal('100.00'))

    def test_loyalty_discount_not_for_non_member(self):
        """Test loyalty-only discount is NOT applied for non-members."""

        # Create loyalty-only discount
        DiscountRuleFactory(
            name='VIP 10% Off',
            scope='order',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            requires_loyalty=True,
            is_active=True
        )

        # Non-loyalty member order
        order = self.create_order_with_items(self.user, [
            (self.laptop_variant, 1, Decimal('1000.00'))
        ])

        discount = get_discount_amount(order)
        self.assertEqual(discount, Decimal('0'))

    def test_stackable_discounts_sum(self):
        """Test that stackable discounts are summed together."""

        # Create two stackable discounts
        DiscountRuleFactory(
            name='10% Off',
            scope='order',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            is_stackable=True,
            is_active=True
        )
        DiscountRuleFactory(
            name='$50 Off',
            scope='order',
            discount_type='fix',
            discount_value=Decimal('50.00'),
            is_stackable=True,
            is_active=True
        )

        # Order total: $1000
        order = self.create_order_with_items(self.user, [
            (self.laptop_variant, 1, Decimal('1000.00'))
        ])

        discount = get_discount_amount(order)
        # 10% of $1000 = $100 + $50 = $150
        self.assertEqual(discount, Decimal('150.00'))

    def test_non_stackable_picks_best(self):
        """Test that non-stackable discounts pick the best one."""

        # Create two non-stackable discounts
        DiscountRuleFactory(
            name='5% Off',
            scope='order',
            discount_type='percentage',
            discount_value=Decimal('5.00'),
            is_stackable=False,
            is_active=True
        )
        DiscountRuleFactory(
            name='$100 Off',
            scope='order',
            discount_type='fix',
            discount_value=Decimal('100.00'),
            is_stackable=False,
            is_active=True
        )

        # Order total: $1000
        order = self.create_order_with_items(self.user, [
            (self.laptop_variant, 1, Decimal('1000.00'))
        ])

        discount = get_discount_amount(order)
        # Best is $100 (5% of $1000 = $50, but $100 > $50)
        self.assertEqual(discount, Decimal('100.00'))

    def test_stackable_and_non_stackable_combined(self):
        """Test combining stackable and non-stackable discounts."""

        # Create stackable discount
        DiscountRuleFactory(
            name='5% Stackable',
            scope='order',
            discount_type='percentage',
            discount_value=Decimal('5.00'),
            is_stackable=True,
            is_active=True
        )
        # Create non-stackable discounts
        DiscountRuleFactory(
            name='$30 Non-Stackable',
            scope='order',
            discount_type='fix',
            discount_value=Decimal('30.00'),
            is_stackable=False,
            is_active=True
        )
        DiscountRuleFactory(
            name='$80 Non-Stackable',
            scope='order',
            discount_type='fix',
            discount_value=Decimal('80.00'),
            is_stackable=False,
            is_active=True
        )

        # Order total: $1000
        order = self.create_order_with_items(self.user, [
            (self.laptop_variant, 1, Decimal('1000.00'))
        ])

        discount = get_discount_amount(order)
        # Stackable: 5% of $1000 = $50
        # Best non-stackable: $80
        # Total: $50 + $80 = $130
        self.assertEqual(discount, Decimal('130.00'))

    def test_expired_discount_not_applied(self):
        """Test that expired discounts are not applied."""

        # Create expired discount
        DiscountRuleFactory(
            name='Expired Discount',
            scope='order',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            start_date=timezone.now() - timedelta(days=30),
            end_date=timezone.now() - timedelta(days=1),
            is_active=True
        )

        order = self.create_order_with_items(self.user, [
            (self.laptop_variant, 1, Decimal('1000.00'))
        ])

        discount = get_discount_amount(order)
        self.assertEqual(discount, Decimal('0'))

    def test_future_discount_not_applied(self):
        """Test that future discounts (not yet started) are not applied."""

        # Create future discount
        DiscountRuleFactory(
            name='Future Discount',
            scope='order',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            start_date=timezone.now() + timedelta(days=7),
            is_active=True
        )

        order = self.create_order_with_items(self.user, [
            (self.laptop_variant, 1, Decimal('1000.00'))
        ])

        discount = get_discount_amount(order)
        self.assertEqual(discount, Decimal('0'))

    def test_inactive_discount_not_applied(self):
        """Test that inactive discounts are not applied."""

        # Create inactive discount
        DiscountRuleFactory(
            name='Inactive Discount',
            scope='order',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            is_active=False
        )

        order = self.create_order_with_items(self.user, [
            (self.laptop_variant, 1, Decimal('1000.00'))
        ])

        discount = get_discount_amount(order)
        self.assertEqual(discount, Decimal('0'))

    def test_applied_discount_created(self):
        """Test that AppliedDiscount records are created."""

        rule = DiscountRuleFactory(
            name='10% Off',
            scope='order',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            is_active=True,
            is_stackable=True
        )

        order = self.create_order_with_items(self.user, [
            (self.laptop_variant, 1, Decimal('1000.00'))
        ])

        get_discount_amount(order)

        # Check AppliedDiscount was created
        applied = AppliedDiscount.objects.filter(order=order, discount_rule=rule)
        self.assertEqual(applied.count(), 1)
        self.assertEqual(applied.first().discount_amount, Decimal('100.00'))
        self.assertEqual(applied.first().scope, 'order')

    def test_discount_cannot_exceed_order_total(self):
        """Test that total discount cannot exceed order total."""

        # Create discount larger than order
        DiscountRuleFactory(
            name='$500 Off',
            scope='order',
            discount_type='fix',
            discount_value=Decimal('500.00'),
            is_active=True,
            is_stackable=True
        )

        # Order total: only $50
        order = self.create_order_with_items(self.user, [
            (self.shirt_variant, 1, Decimal('50.00'))
        ])

        discount = get_discount_amount(order)
        # Should be capped at order total
        self.assertEqual(discount, Decimal('50.00'))


class DiscountCacheTest(TestCase):
    """Test cases for scalable discount caching (2 entries for all users)."""

    def setUp(self):
        """Set up test data."""
        from django.core.cache import cache
        
        # Clear cache before each test
        cache.clear()
        
        # Create users
        self.regular_user = UserFactory(
            email='regular@test.com',
            is_loyalty_member=False
        )
        self.loyalty_user = UserFactory(
            email='loyalty@test.com',
            is_loyalty_member=True
        )
        
        # Create category and product
        self.category = CategoryFactory(name='Test Category')
        self.product = ProductFactory(name='Test Product', category=self.category)
        self.variant = ProductVariantFactory(product=self.product, price=Decimal('100.00'))
        
        # Create discount rules
        self.public_discount = DiscountRuleFactory(
            name='Public 10% Off',
            scope='order',
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            requires_loyalty=False,
            is_active=True
        )
        
        self.loyalty_discount = DiscountRuleFactory(
            name='Loyalty 20% Off',
            scope='order',
            discount_type='percentage',
            discount_value=Decimal('20.00'),
            requires_loyalty=True,
            is_active=True
        )

    def tearDown(self):
        """Clean up after each test."""
        from django.core.cache import cache
        cache.clear()

    def test_cache_keys_are_constant(self):
        """Test that cache keys are constant (not per-user) for scalability."""

        # Keys should be constant strings, not user-specific
        self.assertEqual(ACTIVE_RULES_CACHE_KEY, 'discount_rules:active')
        self.assertEqual(LOYALTY_RULES_CACHE_KEY, 'discount_rules:loyalty')

    def test_cache_stores_active_rule_ids(self):
        """Test that active discount rule IDs are cached correctly."""
        rule_ids = ['rule-1', 'rule-2', 'rule-3']
        
        # Cache should be empty initially
        cached = get_cached_active_discount_rule_ids()
        self.assertIsNone(cached)
        
        # Store in cache
        result = cache_active_discount_rule_ids(rule_ids)
        self.assertTrue(result)
        
        # Retrieve from cache
        cached = get_cached_active_discount_rule_ids()
        self.assertEqual(cached, rule_ids)

    def test_cache_stores_loyalty_rule_ids(self):
        """Test that loyalty discount rule IDs are cached correctly."""

        rule_ids = ['loyalty-rule-1', 'loyalty-rule-2']
        
        # Cache should be empty initially
        cached = get_cached_loyalty_discount_rule_ids()
        self.assertIsNone(cached)
        
        # Store in cache
        result = cache_loyalty_discount_rule_ids(rule_ids)
        self.assertTrue(result)
        
        # Retrieve from cache
        cached = get_cached_loyalty_discount_rule_ids()
        self.assertEqual(cached, rule_ids)

    def test_loyalty_user_gets_more_discounts(self):
        """Test that loyalty users see loyalty-only discounts."""
        from discounts.helpers import get_eligible_discount_rules
        from orders.models import Order, OrderItem
        
        # Create orders
        regular_order = Order.objects.create(
            user=self.regular_user,
            order_status='created'
        )
        # Add order item to make subtotal > 0
        OrderItem.objects.create(
            order=regular_order,
            product_variant=self.variant,
            quantity=2,
            amount=Decimal('200.00')
        )
        
        loyalty_order = Order.objects.create(
            user=self.loyalty_user,
            order_status='created'
        )
        OrderItem.objects.create(
            order=loyalty_order,
            product_variant=self.variant,
            quantity=2,
            amount=Decimal('200.00')
        )
        
        regular_rules = list(get_eligible_discount_rules(regular_order))
        loyalty_rules = list(get_eligible_discount_rules(loyalty_order))
        
        # Regular user: only public discount
        self.assertEqual(len(regular_rules), 1)
        self.assertEqual(regular_rules[0].name, 'Public 10% Off')
        
        # Loyalty user: both discounts
        self.assertEqual(len(loyalty_rules), 2)
        rule_names = {r.name for r in loyalty_rules}
        self.assertIn('Public 10% Off', rule_names)
        self.assertIn('Loyalty 20% Off', rule_names)

    def test_invalidate_clears_all_caches(self):
        """Test invalidating all discount caches."""
        
        # Cache data
        cache_active_discount_rule_ids(['rule-1', 'rule-2'])
        cache_loyalty_discount_rule_ids(['rule-2'])
        
        # Verify cached
        self.assertIsNotNone(get_cached_active_discount_rule_ids())
        self.assertIsNotNone(get_cached_loyalty_discount_rule_ids())
        
        # Invalidate all
        result = invalidate_discount_cache()
        self.assertTrue(result)
        
        # Verify all cleared
        self.assertIsNone(get_cached_active_discount_rule_ids())
        self.assertIsNone(get_cached_loyalty_discount_rule_ids())

    def test_invalidate_all_alias_works(self):
        """Test that invalidate_all_discount_caches alias works."""

        cache_active_discount_rule_ids(['rule-1'])
        self.assertIsNotNone(get_cached_active_discount_rule_ids())
        
        result = invalidate_all_discount_caches()
        self.assertTrue(result)
        
        self.assertIsNone(get_cached_active_discount_rule_ids())

    def test_only_two_cache_entries_for_scalability(self):
        """Test that only 2 cache entries exist regardless of user count."""
        from discounts.cache import (
            cache_active_discount_rule_ids,
            cache_loyalty_discount_rule_ids,
            get_cached_active_discount_rule_ids,
            get_cached_loyalty_discount_rule_ids
        )
        
        # Cache active and loyalty rules (simulating what happens after DB query)
        all_active = [str(self.public_discount.id), str(self.loyalty_discount.id)]
        loyalty_only = [str(self.loyalty_discount.id)]
        
        cache_active_discount_rule_ids(all_active)
        cache_loyalty_discount_rule_ids(loyalty_only)
        
        # All users share the same cache entries
        # Regular user filters out loyalty rules in memory
        active = get_cached_active_discount_rule_ids()
        loyalty = get_cached_loyalty_discount_rule_ids()
        
        self.assertEqual(len(active), 2)
        self.assertEqual(len(loyalty), 1)
        
        # Simulate filtering for regular user (done in application code)
        loyalty_set = set(loyalty)
        regular_user_rules = [r for r in active if r not in loyalty_set]
        self.assertEqual(len(regular_user_rules), 1)
        
        # Loyalty user gets all
        loyalty_user_rules = active
        self.assertEqual(len(loyalty_user_rules), 2)
