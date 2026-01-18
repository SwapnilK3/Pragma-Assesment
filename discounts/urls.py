from django.urls import path, include
from rest_framework.routers import DefaultRouter

from discounts.views import DiscountRuleViewSet, AppliedDiscountViewSet

router = DefaultRouter()
router.register(r'rules', DiscountRuleViewSet, basename='discount-rule')
router.register(r'applied', AppliedDiscountViewSet, basename='applied-discount')

urlpatterns = [
    path('', include(router.urls)),
]
