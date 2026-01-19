import logging
from typing import Any

from django.db import transaction, IntegrityError, DatabaseError
from django.db.models import QuerySet
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.utils import rest_api_formatter, Pagination
from orders.models import Order
from orders.serializers import (
    OrderSerializer,
    OrderDetailSerializer,
    OrderListSerializer
)

logger = logging.getLogger(__name__)


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
        """Retrieve order details (user can only see their own orders)."""
        user_id = request.user.id
        logger.info(f"Order detail requested - Order ID: {order_id}, User ID: {user_id}")

        try:
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
    API view for listing user's orders.
    
    GET /api/order/
    Returns: List of all orders for authenticated user
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self, request) -> QuerySet[Any, Any]:
        queryset = Order.objects.filter(
            user=request.user,
            is_active=True
        ).select_related('user').order_by('-created_at')
        return queryset

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

            logger.debug(f"Retrieved {order_count} orders for user ID: {user_id}")
            return rest_api_formatter(
                data=data,
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
