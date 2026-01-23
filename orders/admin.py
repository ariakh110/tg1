from django.contrib import admin

from .models import Order, OrderOffer, OrderStatusHistory

admin.site.register(Order)
admin.site.register(OrderOffer)
admin.site.register(OrderStatusHistory)
