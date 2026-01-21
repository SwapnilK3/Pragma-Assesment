from django.urls import path, include
from rest_framework.routers import DefaultRouter

from inventory.views import StockInventoryViewSet, StockTransactionViewSet

router = DefaultRouter()
router.register(r'stock', StockInventoryViewSet, basename='stock-inventory')
router.register(r'transactions', StockTransactionViewSet, basename='stock-transaction')

urlpatterns = router.urls
