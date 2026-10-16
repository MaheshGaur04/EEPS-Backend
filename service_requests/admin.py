from django.contrib import admin

from .models import ServiceRequest


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ('subject', 'user', 'status', 'priority', 'category', 'archived', 'created_at')
    list_filter = ('status', 'priority', 'archived', 'category')
    search_fields = ('subject', 'property_address', 'description', 'user__email', 'user__full_name')
