from typing import Any

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


class OrderCheckoutView(APIView):
    """
    API view for creating an order (Checkout).
    
    POST /api/order/checkout/
    Accepts: { items: [{product_variant_id, quantity}], shipping_address_id, payment_mode }
    Returns: Complete order details with items and discount breakdown
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Create a new order with items."""
        serializer = OrderSerializer(
            data=request.data,
            context={'user': request.user}
        )

        if serializer.is_valid():
            order = serializer.save()

            # Return created order with full details
            # Note: We use the order instance directly, which should have items accessible
            detail_serializer = OrderDetailSerializer(order)

            return rest_api_formatter(
                data=detail_serializer.data,
                status_code=status.HTTP_201_CREATED,
                success=True,
                message='Order created successfully'
            )

        return rest_api_formatter(
            data=None,
            status_code=status.HTTP_400_BAD_REQUEST,
            success=False,
            message='Validation failed',
            error_code='VALIDATION_ERROR',
            error_message='Invalid input data',
            error_fields=serializer.errors
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
        try:
            order = Order.objects.prefetch_related(
                'order_items__product_variant__product'
            ).select_related('user', 'shipping_address').get(
                id=order_id,
                user=request.user
            )

            data = OrderDetailSerializer(order).data

            return rest_api_formatter(
                data=data,
                status_code=status.HTTP_200_OK,
                success=True,
                message='Order retrieved successfully'
            )

        except Order.DoesNotExist:
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
                success=False,
                message='Order not found',
                error_code='ORDER_NOT_FOUND',
                error_message='Order does not exist or you do not have permission to view it'
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

        paginator = Pagination()
        queryset = self.get_queryset(request)

        paginated_queryset = paginator.paginate_queryset(queryset, request)
        data = OrderListSerializer(paginated_queryset, many=True).data

        # return paginator.get_paginated_response(serializer.data)
        return rest_api_formatter(
            data=data,
            status_code=status.HTTP_200_OK,
            success=True,
            message=f'Retrieved {queryset.count()} orders'
        )
