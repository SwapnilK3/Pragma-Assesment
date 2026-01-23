from django.urls import path, include
from rest_framework.routers import DefaultRouter

from products.views import CategoryViewSet, SKUViewSet, ProductViewSet, ProductVariantViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'skus', SKUViewSet, basename='sku')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'variants', ProductVariantViewSet, basename='product-variant')

urlpatterns = router.urls
