import logging

from django.db import DatabaseError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.utils import rest_api_formatter
from products.models import Category, SKU, Product, ProductVariant
from products.serializers import (
    CategorySerializer, SKUSerializer,
    ProductListSerializer, ProductDetailSerializer, ProductCreateSerializer,
    ProductVariantListSerializer, ProductVariantDetailSerializer, ProductVariantCreateSerializer
)

logger = logging.getLogger(__name__)


class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Category CRUD operations.
    Categories can be created/managed by staff/admin.
    """
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]  # TODO: Add IsAdminUser for write operations
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def create(self, request, *args, **kwargs):
        logger.info(f"Creating category: {request.data.get('name', 'N/A')}")
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                category = serializer.save()
                logger.info(f"Category created: {category.id} - {category.name}")
                return rest_api_formatter(
                    status_code=status.HTTP_201_CREATED,
                    success=True,
                    message='Category created successfully',
                    data=CategorySerializer(category).data
                )
            logger.warning(f"Category creation validation failed: {serializer.errors}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False,
                message='Validation failed',
                error_code='VALIDATION_ERROR',
                error_message=str(serializer.errors)
            )
        except DatabaseError as e:
            logger.error(f"Database error creating category: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                success=False,
                message='Database error',
                error_code='DATABASE_ERROR'
            )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        logger.info(f"Updating category: {instance.id}")
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            category = serializer.save()
            return rest_api_formatter(
                status_code=status.HTTP_200_OK,
                success=True,
                message='Category updated successfully',
                data=CategorySerializer(category).data
            )
        return rest_api_formatter(
            data=None,
            status_code=status.HTTP_400_BAD_REQUEST,
            success=False,
            message='Validation failed',
            error_message=str(serializer.errors)
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        logger.info(f"Deleting category: {instance.id}")
        instance.is_active = False
        instance.save()
        return rest_api_formatter(
            status_code=status.HTTP_204_NO_CONTENT,
            success=True,
            message='Category deleted successfully'
        )

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Get categories as a tree structure (parent-child hierarchy)."""
        root_categories = self.queryset.filter(parent__isnull=True)
        return Response(CategorySerializer(root_categories, many=True).data)


class SKUViewSet(viewsets.ModelViewSet):
    """
    ViewSet for SKU CRUD operations.
    SKUs can be created/managed by staff/admin.
    """
    queryset = SKU.objects.all()
    serializer_class = SKUSerializer
    permission_classes = [AllowAny]  # TODO: Add IsAdminUser for write operations
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['short_name', 'description']
    ordering_fields = ['short_name']
    ordering = ['short_name']

    def create(self, request, *args, **kwargs):
        logger.info(f"Creating SKU: {request.data.get('short_name', 'N/A')}")
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                sku = serializer.save()
                logger.info(f"SKU created: {sku.id} - {sku.short_name}")
                return rest_api_formatter(
                    status_code=status.HTTP_201_CREATED,
                    success=True,
                    message='SKU created successfully',
                    data=SKUSerializer(sku).data
                )
            logger.warning(f"SKU creation validation failed: {serializer.errors}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False,
                message='Validation failed',
                error_code='VALIDATION_ERROR',
                error_message=str(serializer.errors)
            )
        except DatabaseError as e:
            logger.error(f"Database error creating SKU: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                success=False,
                message='Database error',
                error_code='DATABASE_ERROR'
            )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        logger.info(f"Updating SKU: {instance.id}")
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            sku = serializer.save()
            return rest_api_formatter(
                status_code=status.HTTP_200_OK,
                success=True,
                message='SKU updated successfully',
                data=SKUSerializer(sku).data
            )
        return rest_api_formatter(
            data=None,
            status_code=status.HTTP_400_BAD_REQUEST,
            success=False,
            message='Validation failed',
            error_message=str(serializer.errors)
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        logger.info(f"Deleting SKU: {instance.id}")
        instance.delete()
        return rest_api_formatter(
            status_code=status.HTTP_204_NO_CONTENT,
            success=True,
            message='SKU deleted successfully'
        )


def get_all_child_category_ids(category_id):
    """
    Recursively get all child category IDs for a given parent category.
    Includes the parent category itself.
    """
    from products.models import Category

    ids = [category_id]
    children = Category.objects.filter(parent_id=category_id, is_active=True)
    for child in children:
        ids.extend(get_all_child_category_ids(child.id))
    return ids


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Product CRUD operations.
    Handles nested MediaFile creation during product creation/update.
    Supports hierarchical category filtering (parent includes all children).
    """
    queryset = Product.objects.filter(is_active=True).select_related('category', 'default_variant')
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']  # Removed 'category' - handled manually for hierarchy
    search_fields = ['name', 'description_plaintext']
    ordering_fields = ['name', 'rating', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Override to support hierarchical category filtering."""
        queryset = super().get_queryset()

        # Handle category filter with parent-child hierarchy
        category_id = self.request.query_params.get('category')
        if category_id:
            # Get all child category IDs (including the parent itself)
            all_category_ids = get_all_child_category_ids(category_id)
            queryset = queryset.filter(category_id__in=all_category_ids)

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ProductCreateSerializer
        return ProductDetailSerializer

    def create(self, request, *args, **kwargs):
        logger.info(f"Creating product: {request.data.get('name', 'N/A')}")
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                product = serializer.save()
                logger.info(f"Product created: {product.id}")
                return rest_api_formatter(
                    status_code=status.HTTP_201_CREATED,
                    success=True,
                    message='Product created successfully',
                    data=ProductDetailSerializer(product).data
                )

            logger.warning(f"Product validation failed: {serializer.errors}")
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
            logger.error(f"Database error creating product: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                success=False,
                message='Service temporarily unavailable',
                error_code='DATABASE_ERROR',
                error_message='Please try again later'
            )

        except Exception as e:
            logger.exception(f"Error creating product: {str(e)}")
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
        logger.info(f"Updating product: {instance.id}")

        try:
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            if serializer.is_valid():
                product = serializer.save()
                logger.info(f"Product updated: {product.id}")
                return rest_api_formatter(
                    status_code=status.HTTP_200_OK,
                    success=True,
                    message='Product updated successfully',
                    data=ProductDetailSerializer(product).data
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
            logger.exception(f"Error updating product: {str(e)}")
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
        logger.info(f"Soft deleting product: {instance.id}")

        try:
            instance.soft_delete()
            # Also soft delete variants
            instance.variants.update(is_active=False)

            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_200_OK,
                success=True,
                message='Product deleted successfully'
            )

        except Exception as e:
            logger.exception(f"Error deleting product: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
                message='An unexpected error occurred',
                error_code='INTERNAL_ERROR',
                error_message=str(e)
            )


class ProductVariantViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ProductVariant CRUD operations.
    Handles nested MediaFile creation during variant creation/update.
    """
    queryset = ProductVariant.objects.filter(is_active=True).select_related('product', 'product_sku')
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'product_sku', 'is_active']
    search_fields = ['name']
    ordering_fields = ['name', 'price', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductVariantListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ProductVariantCreateSerializer
        return ProductVariantDetailSerializer

    def create(self, request, *args, **kwargs):
        logger.info(f"Creating variant for product: {request.data.get('product', 'N/A')}")
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                variant = serializer.save()
                logger.info(f"Variant created: {variant.id}")
                return rest_api_formatter(
                    status_code=status.HTTP_201_CREATED,
                    success=True,
                    message='Product variant created successfully',
                    data=ProductVariantDetailSerializer(variant).data
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
            logger.exception(f"Error creating variant: {str(e)}")
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
        logger.info(f"Updating variant: {instance.id}")

        try:
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            if serializer.is_valid():
                variant = serializer.save()
                return rest_api_formatter(
                    status_code=status.HTTP_200_OK,
                    success=True,
                    message='Product variant updated successfully',
                    data=ProductVariantDetailSerializer(variant).data
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
            logger.exception(f"Error updating variant: {str(e)}")
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
        logger.info(f"Soft deleting variant: {instance.id}")

        try:
            instance.soft_delete()
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_200_OK,
                success=True,
                message='Product variant deleted successfully'
            )

        except Exception as e:
            logger.exception(f"Error deleting variant: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
                message='An unexpected error occurred',
                error_code='INTERNAL_ERROR',
                error_message=str(e)
            )
