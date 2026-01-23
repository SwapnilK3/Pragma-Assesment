import logging
from decimal import Decimal
from typing import Any

from django.db import transaction, IntegrityError, DatabaseError
from django.db.models import QuerySet
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.utils import rest_api_formatter, Pagination
from discounts.utils import calculate_preview_discounts
from orders.models import Order
from orders.serializers import (
    OrderSerializer,
    OrderDetailSerializer,
    OrderListSerializer
)
from products.models import ProductVariant

logger = logging.getLogger(__name__)


class OrderPreviewView(APIView):
    """
    API view for previewing order totals and discounts without creating an order.
    
    POST /api/order/preview/
    Accepts: { items: [{product_variant_id, quantity}] }
    Returns: Preview of order totals, applicable discounts and payment summary
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Preview order totals and discounts."""
        user_id = request.user.id
        logger.info(f"Order preview requested by user ID: {user_id}")

        try:
            items_data = request.data.get('items', [])

            if not items_data:
                return rest_api_formatter(
                    data=None,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    success=False,
                    message='No items provided',
                    error_code='VALIDATION_ERROR',
                    error_message='Please add items to your cart'
                )

            # Build cart items list
            cart_items = []
            subtotal = Decimal('0')

            for item in items_data:
                variant_id = item.get('product_variant_id')
                quantity = item.get('quantity', 1)

                try:
                    variant = ProductVariant.objects.select_related('product__category').get(
                        id=variant_id,
                        is_active=True
                    )
                    item_total = variant.price * quantity
                    subtotal += item_total

                    cart_items.append({
                        'variant_id': str(variant.id),
                        'product_name': variant.product.name,
                        'variant_name': variant.name,
                        'quantity': quantity,
                        'unit_price': str(variant.price),
                        'total': str(item_total),
                        'category_id': str(variant.product.category.id) if variant.product.category else None,
                        'category_name': variant.product.category.name if variant.product.category else None
                    })
                except ProductVariant.DoesNotExist:
                    return rest_api_formatter(
                        data=None,
                        status_code=status.HTTP_400_BAD_REQUEST,
                        success=False,
                        message=f'Product variant not found: {variant_id}',
                        error_code='INVALID_VARIANT'
                    )

            # Calculate discounts using shared utility
            discount_result = calculate_preview_discounts(request.user, cart_items, subtotal)
            
            total_discount = discount_result['total_discount']
            final_amount = subtotal - total_discount

            # Build payment summary
            payment_summary = {
                'items': cart_items,
                'subtotal': str(subtotal.quantize(Decimal('0.01'))),
                'applied_discounts': discount_result['applied_discounts'],
                'not_applied_discounts': discount_result['not_applied_discounts'],
                'discounts': discount_result['discount_details'],
                'stackable_count': discount_result['stackable_count'],
                'non_stackable_count': discount_result['non_stackable_count'],
                'total_discount': str(Decimal(total_discount).quantize(Decimal('0.01'))),
                'tax': '0.00',
                'final_amount': str(final_amount.quantize(Decimal('0.01'))),
                'currency': '₹',
                'discount_explanation': self._get_discount_explanation(
                    discount_result['applied_discounts'],
                    discount_result['not_applied_discounts'],
                    discount_result['best_non_stackable']
                ),
                'payment_methods': [
                    {'id': 'cod', 'name': 'Cash on Delivery', 'icon': 'bi-cash'},
                    {'id': 'upi', 'name': 'UPI', 'icon': 'bi-phone', 'disabled': True},
                    {'id': 'card', 'name': 'Credit/Debit Card', 'icon': 'bi-credit-card', 'disabled': True},
                    {'id': 'netbanking', 'name': 'Net Banking', 'icon': 'bi-bank', 'disabled': True}
                ]
            }

            logger.info(f"Order preview generated for user ID: {user_id}, subtotal: {subtotal}, discounts: {total_discount}")
            return rest_api_formatter(
                data=payment_summary,
                status_code=status.HTTP_200_OK,
                success=True,
                message='Order preview generated'
            )

        except Exception as e:
            logger.exception(f"Error generating order preview for user ID: {user_id}: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
                message='Failed to generate preview',
                error_code='INTERNAL_ERROR'
            )

    def _get_discount_explanation(self, applied_discounts, not_applied_discounts, best_non_stackable):
        """Generate a human-readable explanation of how discounts are applied."""
        stackable = [d for d in applied_discounts if d.get('is_stackable', False)]
        
        explanations = []
        if stackable:
            stackable_total = sum(Decimal(d['discount_amount']) for d in stackable)
            count = len(stackable)
            explanations.append(f"{count} stackable discount{'s' if count > 1 else ''} applied (₹{stackable_total})")

        if best_non_stackable:
            explanations.append(f"Best non-stackable: {best_non_stackable['rule_name']} (₹{best_non_stackable['discount_amount']})")

        return " + ".join(explanations) if explanations else "No discounts applicable to this order"


class OrderCheckoutView(APIView):
    """
    API view for creating an order (Checkout).
    
    POST /api/order/checkout/
    Accepts: { items: [{product_variant_id, quantity}], shipping_address_id, payment_mode }
    Returns: Complete order details with items and discount breakdown
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """Create a new order with items."""
        user_id = request.user.id
        logger.info(f"Checkout initiated by user ID: {user_id}")

        try:
            serializer = OrderSerializer(
                data=request.data,
                context={'user': request.user}
            )

            if serializer.is_valid():
                order = serializer.save()

                # Return created order with full details
                detail_serializer = OrderDetailSerializer(order)

                logger.info(f"Order created successfully: {order.order_number} for user ID: {user_id}")
                return rest_api_formatter(
                    data=detail_serializer.data,
                    status_code=status.HTTP_201_CREATED,
                    success=True,
                    message='Order created successfully'
                )

            logger.warning(f"Checkout validation failed for user ID: {user_id}: {serializer.errors}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False,
                message='Validation failed',
                error_code='VALIDATION_ERROR',
                error_message='Invalid input data',
                error_fields=serializer.errors
            )

        except IntegrityError as e:
            logger.error(f"Checkout integrity error for user ID: {user_id}: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_409_CONFLICT,
                success=False,
                message='Order could not be created due to a conflict',
                error_code='INTEGRITY_ERROR',
                error_message='Please try again'
            )

        except DatabaseError as e:
            logger.critical(f"Database error during checkout for user ID: {user_id}: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                success=False,
                message='Service temporarily unavailable',
                error_code='DATABASE_ERROR',
                error_message='Please try again later'
            )

        except Exception as e:
            logger.exception(f"Unexpected error during checkout for user ID: {user_id}: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
                message='An unexpected error occurred',
                error_code='INTERNAL_ERROR',
                error_message='Please try again later'
            )


class OrderDetailView(APIView):
    """
    API view for retrieving order details.
    
    GET /api/order/{id}/
    Returns: Order details with items, totals, and discount breakdown
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        """Retrieve order details (user can only see their own orders, admin/staff can see all)."""
        user_id = request.user.id
        user_role = getattr(request.user, 'role', 'customer')
        logger.info(f"Order detail requested - Order ID: {order_id}, User ID: {user_id}, Role: {user_role}")

        try:
            # Admin and staff can view any order
            if user_role in ['admin', 'staff']:
                order = Order.objects.prefetch_related(
                    'order_items__product_variant__product'
                ).select_related('user', 'shipping_address').get(id=order_id)
            else:
                # Regular users can only see their own orders
                order = Order.objects.prefetch_related(
                    'order_items__product_variant__product'
                ).select_related('user', 'shipping_address').get(
                    id=order_id,
                    user=request.user
                )

            data = OrderDetailSerializer(order).data

            logger.debug(f"Order {order_id} retrieved successfully for user ID: {user_id}")
            return rest_api_formatter(
                data=data,
                status_code=status.HTTP_200_OK,
                success=True,
                message='Order retrieved successfully'
            )

        except Order.DoesNotExist:
            logger.warning(f"Order not found - Order ID: {order_id}, User ID: {user_id}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
                success=False,
                message='Order not found',
                error_code='ORDER_NOT_FOUND',
                error_message='Order does not exist or you do not have permission to view it'
            )

        except ValueError as e:
            logger.warning(f"Invalid order ID format: {order_id}, User ID: {user_id}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False,
                message='Invalid order ID format',
                error_code='INVALID_ORDER_ID',
                error_message='The provided order ID is not valid'
            )

        except DatabaseError as e:
            logger.critical(f"Database error retrieving order {order_id}: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                success=False,
                message='Service temporarily unavailable',
                error_code='DATABASE_ERROR',
                error_message='Please try again later'
            )

        except Exception as e:
            logger.exception(f"Unexpected error retrieving order {order_id}: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
                message='An unexpected error occurred',
                error_code='INTERNAL_ERROR',
                error_message='Please try again later'
            )


class OrderListView(APIView):
    """
    API view for listing orders.
    
    GET /api/order/
    - For regular users: Returns their own orders
    - For admin/staff: Returns all orders (with optional filters)
    
    Query params (admin only):
    - all=true: Get all orders (not just current user's)
    - status: Filter by order_status
    - user_id: Filter by user ID
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self, request) -> QuerySet[Any, Any]:
        user = request.user
        is_admin_or_staff = user.role in ['admin', 'staff']
        show_all = request.query_params.get('all', 'false').lower() == 'true'

        # Admin/staff can see all orders if requested
        if is_admin_or_staff and show_all:
            queryset = Order.objects.filter(is_active=True)
        else:
            queryset = Order.objects.filter(user=user, is_active=True)

        # Apply filters for admin/staff
        if is_admin_or_staff:
            status_filter = request.query_params.get('status')
            if status_filter:
                queryset = queryset.filter(order_status=status_filter)

            user_filter = request.query_params.get('user_id')
            if user_filter:
                queryset = queryset.filter(user_id=user_filter)

        return queryset.select_related('user').order_by('-created_at')

    def get(self, request):
        """List all orders for the authenticated user."""
        user_id = request.user.id
        logger.info(f"Order list requested by user ID: {user_id}")

        try:
            paginator = Pagination()
            queryset = self.get_queryset(request)
            order_count = queryset.count()

            paginated_queryset = paginator.paginate_queryset(queryset, request)
            data = OrderListSerializer(paginated_queryset, many=True).data

            # Include pagination metadata
            pagination_info = {
                'current_page': paginator.page.number,
                'next_page': paginator.page.next_page_number() if paginator.page.has_next() else None,
                'previous_page': paginator.page.previous_page_number() if paginator.page.has_previous() else None,
                'total_pages': paginator.page.paginator.num_pages,
                'total_count': order_count,
                'page_count': len(data),
                'page_size': paginator.get_page_size(request),
            }

            logger.debug(f"Retrieved {order_count} orders for user ID: {user_id}")
            return rest_api_formatter(
                data={
                    'results': data,
                    'pagination': pagination_info
                },
                status_code=status.HTTP_200_OK,
                success=True,
                message=f'Retrieved {order_count} orders'
            )

        except DatabaseError as e:
            logger.critical(f"Database error listing orders for user ID: {user_id}: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                success=False,
                message='Service temporarily unavailable',
                error_code='DATABASE_ERROR',
                error_message='Please try again later'
            )

        except Exception as e:
            logger.exception(f"Unexpected error listing orders for user ID: {user_id}: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
                message='An unexpected error occurred',
                error_code='INTERNAL_ERROR',
                error_message='Please try again later'
            )


class UserAddressListView(APIView):
    """
    API view for listing user's saved shipping addresses from previous orders.
    
    GET /api/order/addresses/
    Returns: List of unique addresses used in user's previous orders
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get user's saved addresses from previous orders."""
        user = request.user
        logger.info(f"Fetching saved addresses for user ID: {user.id}")

        try:
            # Get unique addresses from user's previous orders
            orders_with_addresses = Order.objects.filter(
                user=user,
                is_active=True,
                shipping_address__isnull=False
            ).select_related('shipping_address').order_by('-created_at')

            # Get unique addresses (by content, not just ID)
            seen_addresses = {}
            addresses = []

            for order in orders_with_addresses:
                addr = order.shipping_address
                if not addr:
                    continue

                # Create a unique key based on address content
                addr_key = f"{addr.address_line_1}|{addr.city}|{addr.postal_code}|{addr.country}"

                if addr_key not in seen_addresses:
                    seen_addresses[addr_key] = True
                    addresses.append({
                        'id': str(addr.id),
                        'address_line_1': addr.address_line_1,
                        'address_line_2': addr.address_line_2 or '',
                        'city': addr.city,
                        'city_area': addr.city_area or '',
                        'postal_code': addr.postal_code,
                        'country': str(addr.country) if addr.country else '',
                        'country_area': addr.country_area or '',
                        'phone': str(addr.phone) if addr.phone else '',
                        'display': addr.address_string
                    })

            return rest_api_formatter(
                data=addresses,
                status_code=status.HTTP_200_OK,
                success=True,
                message='Addresses retrieved successfully'
            )

        except Exception as e:
            logger.exception(f"Error fetching addresses for user ID: {user.id}: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
                message='An unexpected error occurred',
                error_code='INTERNAL_ERROR',
                error_message='Please try again later'
            )
