import logging

from django.db import models, IntegrityError, DatabaseError
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from core.utils import rest_api_formatter, Pagination
from discounts.cache import invalidate_all_discount_caches
from discounts.models import DiscountRule, AppliedDiscount
from discounts.serializers import (
    DiscountRuleSerializer,
    DiscountRuleListSerializer,
    AppliedDiscountSerializer
)

logger = logging.getLogger(__name__)


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
        logger.info(f"Discount rules list requested by user: {request.user.email}")

        try:
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)

            logger.debug(f"Retrieved {queryset.count()} discount rules")
            return rest_api_formatter(
                data=serializer.data,
                status_code=status.HTTP_200_OK,
                success=True,
                message='Discount rules retrieved successfully'
            )

        except DatabaseError as e:
            logger.critical(f"Database error listing discount rules: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                success=False,
                message='Service temporarily unavailable',
                error_code='DATABASE_ERROR',
                error_message='Please try again later'
            )

        except Exception as e:
            logger.exception(f"Unexpected error listing discount rules: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
                message='An unexpected error occurred',
                error_code='INTERNAL_ERROR',
                error_message='Please try again later'
            )

    def create(self, request, *args, **kwargs):
        """Create a new discount rule."""
        logger.info(f"Discount rule creation by user: {request.user.email}")

        try:
            serializer = self.get_serializer(data=request.data)

            if serializer.is_valid():
                discount_rule = serializer.save()

                # Invalidate all discount caches when a new rule is created
                invalidate_all_discount_caches()

                logger.info(f"Discount rule created: {discount_rule.name} (ID: {discount_rule.id})")
                return rest_api_formatter(
                    data=DiscountRuleSerializer(discount_rule).data,
                    status_code=status.HTTP_201_CREATED,
                    success=True,
                    message='Discount rule created successfully'
                )

            logger.warning(f"Discount rule validation failed: {serializer.errors}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False,
                message='Failed to create discount rule',
                error_code='VALIDATION_ERROR',
                error_message=str(serializer.errors)
            )

        except IntegrityError as e:
            logger.error(f"Integrity error creating discount rule: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_409_CONFLICT,
                success=False,
                message='Discount rule could not be created due to a conflict',
                error_code='INTEGRITY_ERROR',
                error_message='A discount rule with similar properties may already exist'
            )

        except DatabaseError as e:
            logger.critical(f"Database error creating discount rule: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                success=False,
                message='Service temporarily unavailable',
                error_code='DATABASE_ERROR',
                error_message='Please try again later'
            )

        except Exception as e:
            logger.exception(f"Unexpected error creating discount rule: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
                message='An unexpected error occurred',
                error_code='INTERNAL_ERROR',
                error_message='Please try again later'
            )

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific discount rule."""
        rule_id = kwargs.get('pk')
        logger.info(f"Discount rule retrieve requested - ID: {rule_id}")

        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)

            logger.debug(f"Discount rule {rule_id} retrieved successfully")
            return rest_api_formatter(
                data=serializer.data,
                status_code=status.HTTP_200_OK,
                success=True,
                message='Discount rule retrieved successfully'
            )

        except Exception as e:
            logger.warning(f"Discount rule not found - ID: {rule_id}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
                success=False,
                message='Discount rule not found',
                error_code='NOT_FOUND',
                error_message='The requested discount rule does not exist'
            )

    def update(self, request, *args, **kwargs):
        """Update a discount rule."""
        partial = kwargs.pop('partial', False)
        rule_id = kwargs.get('pk')
        logger.info(f"Discount rule update requested - ID: {rule_id}, Partial: {partial}")

        try:
            instance = get_object_or_404(DiscountRule, pk=rule_id)
        except Http404:
            logger.warning(f"Discount rule not found for update - ID: {rule_id}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
                success=False,
                message='Discount rule not found',
                error_code='NOT_FOUND',
                error_message='The requested discount rule does not exist'
            )

        try:
            serializer = self.get_serializer(instance, data=request.data, partial=partial)

            if serializer.is_valid():
                discount_rule = serializer.save()

                # Invalidate all discount caches when a rule is updated
                invalidate_all_discount_caches()

                logger.info(f"Discount rule updated: {discount_rule.name} (ID: {discount_rule.id})")
                return rest_api_formatter(
                    data=DiscountRuleSerializer(discount_rule).data,
                    status_code=status.HTTP_200_OK,
                    success=True,
                    message='Discount rule updated successfully'
                )

            logger.warning(f"Discount rule update validation failed - ID: {rule_id}: {serializer.errors}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False,
                message='Failed to update discount rule',
                error_code='VALIDATION_ERROR',
                error_message=str(serializer.errors)
            )

        except IntegrityError as e:
            logger.error(f"Integrity error updating discount rule {rule_id}: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_409_CONFLICT,
                success=False,
                message='Update failed due to a conflict',
                error_code='INTEGRITY_ERROR',
                error_message='Please check the data and try again'
            )

        except DatabaseError as e:
            logger.critical(f"Database error updating discount rule {rule_id}: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                success=False,
                message='Service temporarily unavailable',
                error_code='DATABASE_ERROR',
                error_message='Please try again later'
            )

        except Exception as e:
            logger.exception(f"Unexpected error updating discount rule {rule_id}: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
                message='An unexpected error occurred',
                error_code='INTERNAL_ERROR',
                error_message='Please try again later'
            )

    def destroy(self, request, *args, **kwargs):
        """Soft delete a discount rule by setting is_active to False."""
        rule_id = kwargs.get('pk')
        logger.info(f"Discount rule delete requested - ID: {rule_id}")

        try:
            instance = get_object_or_404(DiscountRule, pk=rule_id)
            rule_name = instance.name
            instance.is_active = False
            instance.save(update_fields=['is_active'])

            # Invalidate all discount caches when a rule is deleted
            invalidate_all_discount_caches()

            logger.info(f"Discount rule soft deleted: {rule_name} (ID: {rule_id})")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_200_OK,
                success=True,
                message='Discount rule deleted successfully'
            )

        except Http404:
            logger.warning(f"Discount rule not found for delete - ID: {rule_id}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
                success=False,
                message='Discount rule not found',
                error_code='NOT_FOUND',
                error_message='The requested discount rule does not exist'
            )

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get only active discount rules that are currently valid."""
        logger.info(f"Active discount rules requested by user: {request.user.email}")

        try:
            now = timezone.now()

            queryset = self.get_queryset().filter(
                is_active=True,
                start_date__lte=now
            ).filter(
                models.Q(end_date__isnull=True) | models.Q(end_date__gte=now)
            )

            serializer = DiscountRuleListSerializer(queryset, many=True)

            logger.debug(f"Retrieved {queryset.count()} active discount rules")
            return rest_api_formatter(
                data=serializer.data,
                status_code=status.HTTP_200_OK,
                success=True,
                message='Active discount rules retrieved successfully'
            )

        except DatabaseError as e:
            logger.critical(f"Database error retrieving active discount rules: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                success=False,
                message='Service temporarily unavailable',
                error_code='DATABASE_ERROR',
                error_message='Please try again later'
            )

        except Exception as e:
            logger.exception(f"Unexpected error retrieving active discount rules: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
                message='An unexpected error occurred',
                error_code='INTERNAL_ERROR',
                error_message='Please try again later'
            )


class AppliedDiscountViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing Applied Discounts (read-only).
    Applied discounts are created automatically when orders are placed.
    Uses Pagination class from core.utils (20 items per page).
    """
    queryset = AppliedDiscount.objects.all()
    serializer_class = AppliedDiscountSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination

    def get_queryset(self):
        """Filter applied discounts by user's orders."""
        user = self.request.user
        if user.is_staff:
            return AppliedDiscount.objects.select_related(
                'order', 'discount_rule'
            ).filter(is_active=True).order_by('-created_at')
        return AppliedDiscount.objects.select_related(
            'order', 'discount_rule'
        ).filter(
            is_active=True,
            order__user=user
        ).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        """List applied discounts with pagination."""
        logger.info(f"Applied discounts list requested by user: {request.user.email}")

        try:
            queryset = self.filter_queryset(self.get_queryset())

            # Use the pagination class
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)

            logger.debug(f"Retrieved {queryset.count()} applied discounts")
            return rest_api_formatter(
                data=serializer.data,
                status_code=status.HTTP_200_OK,
                success=True,
                message='Applied discounts retrieved successfully'
            )

        except DatabaseError as e:
            logger.critical(f"Database error listing applied discounts: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                success=False,
                message='Service temporarily unavailable',
                error_code='DATABASE_ERROR',
                error_message='Please try again later'
            )

        except Exception as e:
            logger.exception(f"Unexpected error listing applied discounts: {str(e)}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False,
                message='An unexpected error occurred',
                error_code='INTERNAL_ERROR',
                error_message='Please try again later'
            )

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific applied discount."""
        discount_id = kwargs.get('pk')
        logger.info(f"Applied discount retrieve requested - ID: {discount_id}")

        try:
            instance = get_object_or_404(AppliedDiscount, pk=discount_id)
            serializer = self.get_serializer(instance)

            return rest_api_formatter(
                data=serializer.data,
                status_code=status.HTTP_200_OK,
                success=True,
                message='Applied discount retrieved successfully'
            )

        except Http404:
            logger.warning(f"Applied discount not found - ID: {discount_id}")
            return rest_api_formatter(
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
                success=False,
                message='Applied discount not found',
                error_code='NOT_FOUND',
                error_message='The requested applied discount does not exist'
            )
