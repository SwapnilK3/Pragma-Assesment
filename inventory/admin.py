from django.contrib import admin

from inventory.models import StockInventory, StockTransaction


# Register your models here.
admin.site.register([StockInventory, StockTransaction])
