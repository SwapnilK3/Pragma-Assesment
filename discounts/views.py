from django.db import models
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from core.utils import rest_api_formatter
from discounts.models import DiscountRule, AppliedDiscount
from discounts.serializers import (
    DiscountRuleSerializer,
    DiscountRuleListSerializer,
    AppliedDiscountSerializer
)


class DiscountRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Discount Rules.
    
    Provides CRUD operations for discount rules:
    - list: Get all discount rules (with filtering)
    - create: Create a new discount rule
    - retrieve: Get a specific discount rule
    - update: Update a discount rule
    - partial_update: Partially update a discount rule
    - destroy: Soft delete a discount rule
    
    Optional fields that represent conditions:
    - If min_order_amount is not set, no minimum order amount is required
    - If min_quantity is not set, no minimum quantity is required
    - If categories is not set (for category scope), applies to all categories
    - If product_variant is not set (for item scope), applies to all variants
    - If end_date is not set, discount never expires
    """
    queryset = DiscountRule.objects.filter(is_active=True)
    serializer_class = DiscountRuleSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['scope', 'discount_type', 'is_active', 'requires_loyalty', 'is_stackable']
    search_fields = ['name']
    ordering_fields = ['start_date', 'end_date', 'discount_value']
    ordering = ['-start_date']
    
    def get_serializer_class(self):
        """Use lightweight serializer for list action."""
        if self.action == 'list':
            return DiscountRuleListSerializer
        return DiscountRuleSerializer
    
    def get_queryset(self):
        """Return all discount rules for admin users."""
        return DiscountRule.objects.select_related(
            'categories', 'product_variant'
        ).all()
    
    def list(self, request, *args, **kwargs):
        """List all discount rules with optional filtering."""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        
        return rest_api_formatter(
            data=serializer.data,
            status_code=status.HTTP_200_OK,
            success=True,
            message='Discount rules retrieved successfully'
        )
    
    def create(self, request, *args, **kwargs):
        """Create a new discount rule."""
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            discount_rule = serializer.save()
            
            return rest_api_formatter(
                data=DiscountRuleSerializer(discount_rule).data,
                status_code=status.HTTP_201_CREATED,
                success=True,
                message='Discount rule created successfully'
            )
        
        return rest_api_formatter(
            data=None,
            status_code=status.HTTP_400_BAD_REQUEST,
            success=False,
            message='Failed to create discount rule',
            error_code='VALIDATION_ERROR',
            error_message=str(serializer.errors)
        )
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific discount rule."""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            
            return rest_api_formatter(
                data=serializer.data,
                status_code=status.HTTP_200_OK,
                success=True,
                message='Discount rule retrieved successfully'
            )
        except Exception:
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
                success=False,
                message='Discount rule not found',
                error_code='NOT_FOUND'
            )
    
    def update(self, request, *args, **kwargs):
        """Update a discount rule."""
        partial = kwargs.pop('partial', False)
        
        try:
            instance = self.get_object()
        except Exception:
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
                success=False,
                message='Discount rule not found',
                error_code='NOT_FOUND'
            )
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            discount_rule = serializer.save()
            
            return rest_api_formatter(
                data=DiscountRuleSerializer(discount_rule).data,
                status_code=status.HTTP_200_OK,
                success=True,
                message='Discount rule updated successfully'
            )
        
        return rest_api_formatter(
            data=None,
            status_code=status.HTTP_400_BAD_REQUEST,
            success=False,
            message='Failed to update discount rule',
            error_code='VALIDATION_ERROR',
            error_message=str(serializer.errors)
        )
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete a discount rule by setting is_active to False."""
        try:
            instance = self.get_object()
            instance.is_active = False
            instance.save(update_fields=['is_active'])
            
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_200_OK,
                success=True,
                message='Discount rule deleted successfully'
            )
        except Exception:
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
                success=False,
                message='Discount rule not found',
                error_code='NOT_FOUND'
            )
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get only active discount rules that are currently valid."""
        from django.utils import timezone
        now = timezone.now()
        
        queryset = self.get_queryset().filter(
            is_active=True,
            start_date__lte=now
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=now)
        )
        
        serializer = DiscountRuleListSerializer(queryset, many=True)
        
        return rest_api_formatter(
            data=serializer.data,
            status_code=status.HTTP_200_OK,
            success=True,
            message='Active discount rules retrieved successfully'
        )


class AppliedDiscountViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing Applied Discounts (read-only).
    Applied discounts are created automatically when orders are placed.
    """
    queryset = AppliedDiscount.objects.all()
    serializer_class = AppliedDiscountSerializer
    permission_classes = [IsAuthenticated]
    # filter_backends = [DjangoFilterBackend, OrderingFilter]
    # filterset_fields = ['order', 'discount_rule', 'scope']
    # ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter applied discounts by user's orders."""
        user = self.request.user
        if user.is_staff:
            return AppliedDiscount.objects.select_related(
                'order', 'discount_rule'
            ).all()
        return AppliedDiscount.objects.select_related(
            'order', 'discount_rule'
        ).filter(order__user=user)
    
    def list(self, request, *args, **kwargs):
        """List applied discounts."""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        
        return rest_api_formatter(
            data=serializer.data,
            status_code=status.HTTP_200_OK,
            success=True,
            message='Applied discounts retrieved successfully'
        )
