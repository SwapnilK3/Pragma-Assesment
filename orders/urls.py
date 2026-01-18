from django.urls import path
from orders.views import OrderCheckoutView, OrderDetailView, OrderListView

urlpatterns = [
    path('', OrderListView.as_view(), name='order-list'),
    path('checkout/', OrderCheckoutView.as_view(), name='order-checkout'),
    path('<uuid:order_id>/', OrderDetailView.as_view(), name='order-detail'),
]
