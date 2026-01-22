"""
Frontend views for serving Django templates.
"""
from django.shortcuts import render, redirect
from django.views import View


class CustomerLoginView(View):
    """Customer login page."""
    template_name = 'accounts/customer_login.html'
    
    def get(self, request):
        return render(request, self.template_name)


class CustomerRegisterView(View):
    """Customer registration page."""
    template_name = 'accounts/customer_register.html'
    
    def get(self, request):
        return render(request, self.template_name)


class CustomerHomeView(View):
    """Customer - browse products and place orders."""
    template_name = 'customer/home.html'
    
    def get(self, request):
        return render(request, self.template_name)


class StaffLoginView(View):
    """Staff login page."""
    template_name = 'accounts/staff_login.html'
    
    def get(self, request):
        return render(request, self.template_name)


class StaffDashboardView(View):
    """Staff dashboard - product and inventory management."""
    template_name = 'staff/dashboard.html'
    
    def get(self, request):
        return render(request, self.template_name)


class AdminLoginView(View):
    """Admin login page."""
    template_name = 'accounts/admin_login.html'
    
    def get(self, request):
        return render(request, self.template_name)


class AdminDashboardView(View):
    """Admin dashboard - user, discount, and order management."""
    template_name = 'admin/dashboard.html'
    
    def get(self, request):
        return render(request, self.template_name)


class HomeView(View):
    """Home/landing page - redirects to customer login."""
    
    def get(self, request):
        return redirect('customer_login')
