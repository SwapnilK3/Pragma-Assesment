from django.contrib import admin
from orders.models import Order, OrderItem

# Register order models
admin.site.register([Order, OrderItem])
