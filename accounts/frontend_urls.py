"""
Frontend URL configuration for authentication pages.
"""
from django.urls import path

from accounts.frontend_views import (
    CustomerLoginView,
    CustomerRegisterView,
    CustomerHomeView,
    StaffLoginView,
    StaffDashboardView,
    AdminLoginView,
    AdminDashboardView,
    HomeView,
)

urlpatterns = [
    # Home
    # path('', HomeView.as_view(), name='home'),
    
    # Customer authentication and shop
    path('login/', CustomerLoginView.as_view(), name='customer_login'),
    path('register/', CustomerRegisterView.as_view(), name='customer_register'),
    path('', CustomerHomeView.as_view(), name='customer_home'),
    
    # Staff authentication and dashboard
    path('staff/login/', StaffLoginView.as_view(), name='staff_login'),
    path('staff/', StaffDashboardView.as_view(), name='staff_dashboard'),
    
    # Admin authentication and dashboard
    path('admin-portal/login/', AdminLoginView.as_view(), name='admin_login'),
    path('admin-portal/', AdminDashboardView.as_view(), name='admin_dashboard'),
]
