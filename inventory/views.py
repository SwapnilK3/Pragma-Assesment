"""
ViewSets for Inventory app.
"""
import logging

from django.db import DatabaseError
from rest_framework.permissions import AllowAny
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from core.utils import rest_api_formatter
from inventory.models import StockInventory, StockTransaction
from inventory.serializers import (
    StockInventoryListSerializer, StockInventoryDetailSerializer, StockInventoryCreateSerializer,
    StockTransactionSerializer, StockTransactionCreateSerializer
)

logger = logging.getLogger(__name__)


class StockInventoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for StockInventory CRUD operations.
    Manages stock levels for products and variants.
    """
    queryset = StockInventory.objects.filter(is_active=True).select_related('product', 'product_variant')
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'product_variant', 'is_unlimited_stock', 'is_active']
    search_fields = ['product__name', 'product_variant__name']
    ordering_fields = ['total_quantity', 'remaining_quantity', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return StockInventoryListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return StockInventoryCreateSerializer
        return StockInventoryDetailSerializer

    def create(self, request, *args, **kwargs):
        logger.info(f"Creating stock inventory")
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                inventory = serializer.save()
                logger.info(f"Stock inventory created: {inventory.id}")
                return rest_api_formatter(
                    status_code=status.HTTP_201_CREATED,
                    success=True,
                    message='Stock inventory created successfully',
                    data=StockInventoryDetailSerializer(inventory).data
                )

            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False,
                message='Validation failed',
                error_code='VALIDATION_ERROR',
                error_message='Invalid input data',
                error_fields=list(serializer.errors.keys())
            )

        except DatabaseError as e:
            logger.error(f"Database error creating inventory: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                success=False,
                message='Service temporarily unavailable',
                error_code='DATABASE_ERROR',
                error_message='Please try again later'
            )

        except Exception as e:
            logger.exception(f"Error creating inventory: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
                message='An unexpected error occurred',
                error_code='INTERNAL_ERROR',
                error_message=str(e)
            )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        logger.info(f"Updating stock inventory: {instance.id}")

        try:
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            if serializer.is_valid():
                inventory = serializer.save()
                return rest_api_formatter(
                    status_code=status.HTTP_200_OK,
                    success=True,
                    message='Stock inventory updated successfully',
                    data=StockInventoryDetailSerializer(inventory).data
                )

            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False,
                message='Validation failed',
                error_code='VALIDATION_ERROR',
                error_message='Invalid input data',
                error_fields=list(serializer.errors.keys())
            )

        except Exception as e:
            logger.exception(f"Error updating inventory: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
                message='An unexpected error occurred',
                error_code='INTERNAL_ERROR',
                error_message=str(e)
            )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        logger.info(f"Soft deleting stock inventory: {instance.id}")

        try:
            instance.soft_delete()
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_200_OK,
                success=True,
                message='Stock inventory deleted successfully'
            )

        except Exception as e:
            logger.exception(f"Error deleting inventory: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
                message='An unexpected error occurred',
                error_code='INTERNAL_ERROR',
                error_message=str(e)
            )

    @action(detail=True, methods=['post'])
    def add_stock(self, request, pk=None):
        """Add stock (INWARD transaction)."""
        inventory = self.get_object()
        quantity = request.data.get('quantity', 0)
        metadata = request.data.get('metadata', {})

        if quantity <= 0:
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False,
                message='Quantity must be greater than 0',
                error_code='VALIDATION_ERROR'
            )

        try:
            from inventory import TransactionType
            StockTransaction.objects.create(
                inventory=inventory,
                type=TransactionType.INWARD,
                quantity=quantity,
                metadata=metadata
            )
            inventory.recalculate_inventory_data()
            inventory.save()

            return rest_api_formatter(
                status_code=status.HTTP_200_OK,
                success=True,
                message=f'Added {quantity} units to stock',
                data=StockInventoryDetailSerializer(inventory).data
            )

        except Exception as e:
            logger.exception(f"Error adding stock: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
                message='An unexpected error occurred',
                error_code='INTERNAL_ERROR',
                error_message=str(e)
            )

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get items with low stock (remaining_quantity < 10)."""
        low_stock_items = self.queryset.filter(
            remaining_quantity__lt=10,
            is_unlimited_stock=False
        )
        return Response(StockInventoryListSerializer(low_stock_items, many=True).data)


class StockTransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for StockTransaction operations.
    Records all stock movements (INWARD/OUTWARD).
    """
    queryset = StockTransaction.objects.filter(is_active=True).select_related('inventory')
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['inventory', 'type', 'is_active']
    ordering_fields = ['quantity', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return StockTransactionCreateSerializer
        return StockTransactionSerializer

    def create(self, request, *args, **kwargs):
        logger.info(f"Creating stock transaction")
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                transaction = serializer.save()
                logger.info(f"Stock transaction created: {transaction.id}")
                return rest_api_formatter(
                    status_code=status.HTTP_201_CREATED,
                    success=True,
                    message='Stock transaction created successfully',
                    data=StockTransactionSerializer(transaction).data
                )

            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False,
                message='Validation failed',
                error_code='VALIDATION_ERROR',
                error_message='Invalid input data',
                error_fields=list(serializer.errors.keys())
            )

        except Exception as e:
            logger.exception(f"Error creating transaction: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
                message='An unexpected error occurred',
                error_code='INTERNAL_ERROR',
                error_message=str(e)
            )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        logger.info(f"Soft deleting stock transaction: {instance.id}")

        try:
            inventory = instance.inventory
            instance.soft_delete()

            # Recalculate inventory after transaction deletion
            inventory.recalculate_inventory_data()
            inventory.save()

            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_200_OK,
                success=True,
                message='Stock transaction deleted successfully'
            )

        except Exception as e:
            logger.exception(f"Error deleting transaction: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
                message='An unexpected error occurred',
                error_code='INTERNAL_ERROR',
                error_message=str(e)
            )
