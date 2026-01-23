from django.urls import path

from orders.views import OrderCheckoutView, OrderDetailView, OrderListView, OrderPreviewView, UserAddressListView

urlpatterns = [
    path('', OrderListView.as_view(), name='order-list'),
    path('addresses/', UserAddressListView.as_view(), name='user-addresses'),
    path('preview/', OrderPreviewView.as_view(), name='order-preview'),
    path('checkout/', OrderCheckoutView.as_view(), name='order-checkout'),
    path('<uuid:order_id>/', OrderDetailView.as_view(), name='order-detail'),
]