from django.contrib import admin

from .models import RoiPricingConfig


@admin.register(RoiPricingConfig)
class RoiPricingConfigAdmin(admin.ModelAdmin):
    list_display = ('id', 'cost_per_kw', 'battery_cost_per_kw', 'panel_wattage', 'updated_at')
    fields = (
        'cost_per_kw',
        'battery_cost_per_kw',
        'panel_wattage',
        'sqft_per_kw',
        'default_tariff_per_kwh',
        'savings_fraction',
        'irradiance_factors',
        'subsidy_inr',
    )

    def has_add_permission(self, request):
        return not RoiPricingConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
