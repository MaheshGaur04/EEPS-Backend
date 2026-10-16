from django.contrib import admin

from .models import Contact


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'source', 'reviewed', 'created_at')
    list_filter = ('reviewed', 'source')
    search_fields = ('name', 'email', 'phone', 'message')
