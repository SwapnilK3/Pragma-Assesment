# from decimal import Decimal
# from django.test import TestCase
# from django.urls import reverse
# from rest_framework.test import APITestCase, APIClient
# from rest_framework import status
#
# from accounts.backends import User
# from products.models import Category, Product, ProductVariant
# from orders.models import Order, OrderItem
# from orders.factories import (
#     UserFactory, CategoryFactory, ProductFactory,
#     ProductVariantFactory, AddressFactory
# )
#
#
# class OrderAPITest(APITestCase):
#     """Test cases for Order API endpoints."""
#
#     def setUp(self):
#         """Set up test data before each test."""
#         self.client = APIClient()
#
#         # Create test user
#         self.user = UserFactory(email='testuser@example.com')
#         self.user.set_password('testpass123')
#         self.user.save()
#
#         # Create categories
#         self.category = CategoryFactory(name='Electronics')
#
#         # Create products with variants
#         self.product1 = ProductFactory(
#             name='iPhone 15 Pro',
#             category=self.category,
#             rating=4.8
#         )
#
#         self.variant1 = ProductVariantFactory(
#             name='iPhone 15 Pro - 128GB',
#             product=self.product1,
#             price=Decimal('999.00')
#         )
#
#         self.product1.default_variant = self.variant1
#         self.product1.save()
#
#         self.product2 = ProductFactory(
#             name='Samsung Galaxy S24',
#             category=self.category,
#             rating=4.6
#         )
#
#         self.variant2 = ProductVariantFactory(
#             name='Samsung Galaxy S24 - 256GB',
#             product=self.product2,
#             price=Decimal('849.00')
#         )
#
#         self.product2.default_variant = self.variant2
#         self.product2.save()
#
#         # Login and get token
#         self.login_url = reverse('login')
#         login_response = self.client.post(
#             self.login_url,
#             {
#                 'email': 'testuser@example.com',
#                 'password': 'testpass123'
#             },
#             format='json'
#         )
#         self.access_token = login_response.data['data']['tokens']['access']
#         self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
#
#     def test_create_order_success(self):
#         """Test successful order creation with valid items."""
#         # Create address for this test
#         address = AddressFactory()
#
#         url = reverse('order-checkout')
#         payload = {
#             'items': [
#                 {
#                     'product_variant_id': str(self.variant1.id),
#                     'quantity': 2
#                 },
#                 {
#                     'product_variant_id': str(self.variant2.id),
#                     'quantity': 1
#                 }
#             ],
#             'shipping_address_id': str(address.id),
#             'payment_mode': 'online'
#         }
#
#         response = self.client.post(url, payload, format='json')
#
#         # Assert response
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#         self.assertTrue(response.data['success'])
#         self.assertEqual(response.data['message'], 'Order created successfully')
#
#         # Assert order data
#         order_data = response.data['data']
#         self.assertIsNotNone(order_data['id'])
#         self.assertIsNotNone(order_data['order_number'])
#         self.assertEqual(order_data['user_email'], 'testuser@example.com')
#         self.assertEqual(order_data['order_status'], 'created')
#         self.assertEqual(order_data['payment_status'], 'payment_pending')
#
#         # Verify order in database first
#         order = Order.objects.get(id=order_data['id'])
#         self.assertEqual(order.user, self.user)
#         self.assertEqual(order.order_items.count(), 2)
#
#         # Now check the serialized response
#         self.assertEqual(len(order_data['order_items']), 2)
#
#         # Assert calculations
#         expected_subtotal = (2 * Decimal('999.00')) + (1 * Decimal('849.00'))
#         self.assertEqual(Decimal(order_data['subtotal']), expected_subtotal)
#         self.assertEqual(Decimal(order_data['total_payable_amount']), expected_subtotal)
#
#         # Verify order in database
#         order = Order.objects.get(id=order_data['id'])
#         self.assertEqual(order.user, self.user)
#         self.assertEqual(order.order_items.count(), 2)
#
#         # Verify order items
#         order_item1 = order.order_items.filter(product_variant=self.variant1).first()
#         self.assertIsNotNone(order_item1)
#         self.assertEqual(order_item1.quantity, 2)
#         self.assertEqual(order_item1.unit_rate, Decimal('999.00'))
#         self.assertEqual(order_item1.amount, Decimal('1998.00'))
#
#         order_item2 = order.order_items.filter(product_variant=self.variant2).first()
#         self.assertIsNotNone(order_item2)
#         self.assertEqual(order_item2.quantity, 1)
#         self.assertEqual(order_item2.unit_rate, Decimal('849.00'))
#         self.assertEqual(order_item2.amount, Decimal('849.00'))
#
#     def test_create_order_empty_items(self):
#         """Test order creation fails with empty items."""
#         url = reverse('order-checkout')
#         payload = {
#             'items': [],
#             'payment_mode': 'online'
#         }
#
#         response = self.client.post(url, payload, format='json')
#
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertFalse(response.data['success'])
#         self.assertEqual(response.data['errors']['code'], 'VALIDATION_ERROR')
#
#     def test_create_order_invalid_variant(self):
#         """Test order creation fails with invalid variant ID."""
#         url = reverse('order-checkout')
#         payload = {
#             'items': [
#                 {
#                     'product_variant_id': '00000000-0000-0000-0000-000000000000',
#                     'quantity': 1
#                 }
#             ],
#             'payment_mode': 'online'
#         }
#
#         response = self.client.post(url, payload, format='json')
#
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertFalse(response.data['success'])
#
#     def test_create_order_inactive_variant(self):
#         """Test order creation fails with inactive variant."""
#         # Make variant inactive
#         self.variant1.is_active = False
#         self.variant1.save()
#
#         url = reverse('order-checkout')
#         payload = {
#             'items': [
#                 {
#                     'product_variant_id': str(self.variant1.id),
#                     'quantity': 1
#                 }
#             ],
#             'payment_mode': 'online'
#         }
#
#         response = self.client.post(url, payload, format='json')
#
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertFalse(response.data['success'])
#
#     def test_create_order_without_auth(self):
#         """Test order creation fails without authentication."""
#         self.client.credentials()  # Remove auth
#
#         url = reverse('order-checkout')
#         payload = {
#             'items': [
#                 {
#                     'product_variant_id': str(self.variant1.id),
#                     'quantity': 1
#                 }
#             ]
#         }
#
#         response = self.client.post(url, payload, format='json')
#
#         self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
#
#     def test_retrieve_order_success(self):
#         """Test retrieving order details."""
#         # Create address for this test
#         address = AddressFactory()
#
#         # First create an order
#         order = Order.objects.create(
#             user=self.user,
#             shipping_address=address,
#             order_status='created',
#             payment_status='payment_pending',
#             total_payable_amount=Decimal('999.00')
#         )
#
#         OrderItem.objects.create(
#             order=order,
#             product_variant=self.variant1,
#             quantity=1,
#             unit_rate=self.variant1.price
#         )
#
#         # Retrieve order
#         url = reverse('order-detail', kwargs={'order_id': order.id})
#         response = self.client.get(url)
#
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertTrue(response.data['success'])
#         self.assertEqual(response.data['data']['id'], str(order.id))
#         self.assertEqual(len(response.data['data']['order_items']), 1)
#
#     def test_retrieve_order_not_found(self):
#         """Test retrieving non-existent order."""
#         url = reverse('order-detail', kwargs={'order_id': '00000000-0000-0000-0000-000000000000'})
#         response = self.client.get(url)
#
#         self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
#         self.assertFalse(response.data['success'])
#         self.assertEqual(response.data['errors']['code'], 'ORDER_NOT_FOUND')
#
#     def test_retrieve_other_user_order(self):
#         """Test user cannot retrieve another user's order."""
#         # Create another user and order
#         other_user = UserFactory(email='otheruser@example.com')
#         other_order = Order.objects.create(
#             user=other_user,
#             order_status='created',
#             payment_status='payment_pending',
#             total_payable_amount=Decimal('100.00')
#         )
#
#         # Try to retrieve other user's order
#         url = reverse('order-detail', kwargs={'order_id': other_order.id})
#         response = self.client.get(url)
#
#         self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
#         self.assertEqual(response.data['errors']['code'], 'ORDER_NOT_FOUND')
#
#     def test_list_orders_success(self):
#         """Test listing user's orders."""
#         # Create multiple orders
#         for i in range(3):
#             order = Order.objects.create(
#                 user=self.user,
#                 order_status='created',
#                 payment_status='payment_pending',
#                 total_payable_amount=Decimal(str(100.00 * (i + 1)))
#             )
#
#         url = reverse('order-list')
#         response = self.client.get(url)
#
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertTrue(response.data['success'])
#         self.assertEqual(len(response.data['data']), 3)
#
#         # Verify orders are sorted by most recent first
#         orders_data = response.data['data']
#         self.assertGreaterEqual(orders_data[0]['created_at'], orders_data[1]['created_at'])
#
#     def test_list_orders_empty(self):
#         """Test listing orders when user has no orders."""
#         url = reverse('order-list')
#         response = self.client.get(url)
#
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertTrue(response.data['success'])
#         self.assertEqual(len(response.data['data']), 0)
#
#     def test_order_item_calculation(self):
#         """Test that OrderItem amount is calculated correctly on save."""
#         order = Order.objects.create(
#             user=self.user,
#             order_status='created',
#             payment_status='payment_pending'
#         )
#
#         order_item = OrderItem(
#             order=order,
#             product_variant=self.variant1,
#             quantity=3,
#             unit_rate=Decimal('100.00'),
#             discounted_amount=Decimal('50.00')
#         )
#         order_item.save()
#
#         # Amount should be (quantity * unit_rate) - discounted_amount
#         expected_amount = (3 * Decimal('100.00')) - Decimal('50.00')
#         self.assertEqual(order_item.amount, expected_amount)
#
#
# class OrderModelTest(TestCase):
#     """Test cases for Order and OrderItem models."""
#
#     def setUp(self):
#         """Set up test data."""
#         self.user = UserFactory()
#         self.category = CategoryFactory()
#         self.product = ProductFactory(category=self.category)
#         self.variant = ProductVariantFactory(
#             product=self.product,
#             price=Decimal('150.00')
#         )
#
#     def test_order_creation(self):
#         """Test creating an order."""
#         order = Order.objects.create(
#             user=self.user,
#             order_status='created',
#             payment_status='payment_pending',
#             total_payable_amount=Decimal('300.00')
#         )
#
#         self.assertIsNotNone(order.id)
#         self.assertIsNotNone(order.order_number)
#         self.assertEqual(order.user, self.user)
#         self.assertEqual(order.total_payable_amount, Decimal('300.00'))
#
#     def test_order_item_creation(self):
#         """Test creating an order item."""
#         order = Order.objects.create(user=self.user)
#
#         order_item = OrderItem.objects.create(
#             order=order,
#             product_variant=self.variant,
#             quantity=2,
#             unit_rate=Decimal('150.00')
#         )
#
#         self.assertIsNotNone(order_item.id)
#         self.assertEqual(order_item.quantity, 2)
#         self.assertEqual(order_item.unit_rate, Decimal('150.00'))
#         self.assertEqual(order_item.amount, Decimal('300.00'))
#
#     def test_order_item_unique_constraint(self):
#         """Test that duplicate order items for same variant are prevented."""
#         order = Order.objects.create(user=self.user)
#
#         OrderItem.objects.create(
#             order=order,
#             product_variant=self.variant,
#             quantity=1,
#             unit_rate=Decimal('100.00')
#         )
#
#         # Try to create duplicate
#         from django.db import IntegrityError
#         with self.assertRaises(IntegrityError):
#             OrderItem.objects.create(
#                 order=order,
#                 product_variant=self.variant,
#                 quantity=2,
#                 unit_rate=Decimal('100.00')
#             )
