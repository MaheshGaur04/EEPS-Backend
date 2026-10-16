from django.db import models


class RoiPricingConfig(models.Model):
    """Singleton admin-editable pricing & subsidy defaults for the ROI engine."""

    cost_per_kw = models.PositiveIntegerField(default=72000)
    battery_cost_per_kw = models.PositiveIntegerField(default=82000)
    panel_wattage = models.PositiveIntegerField(default=550)
    sqft_per_kw = models.FloatField(default=100.0)
    default_tariff_per_kwh = models.FloatField(default=8.0)
    savings_fraction = models.FloatField(default=0.72)
    # JSON: {"rajasthan": 1.12, "delhi": 1.05, ...}
    irradiance_factors = models.JSONField(default=dict, blank=True)
    # Fixed PM Surya Ghar / scheme assistance (₹1,08,000)
    subsidy_inr = models.PositiveIntegerField(default=108000)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'ROI pricing config'
        verbose_name_plural = 'ROI pricing config'

    def __str__(self):
        return f'ROI pricing (₹{self.cost_per_kw}/kW)'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        if not obj.irradiance_factors:
            obj.irradiance_factors = DEFAULT_IRRADIANCE_FACTORS.copy()
            obj.save(update_fields=['irradiance_factors'])
        if not obj.subsidy_inr:
            obj.subsidy_inr = DEFAULT_SUBSIDY_INR
            obj.save(update_fields=['subsidy_inr'])
        return obj


DEFAULT_IRRADIANCE_FACTORS = {
    'rajasthan': 1.15,
    'gujarat': 1.12,
    'madhya pradesh': 1.08,
    'maharashtra': 1.05,
    'pune': 1.06,
    'mumbai': 1.02,
    'delhi': 1.05,
    'haryana': 1.06,
    'punjab': 1.07,
    'uttar pradesh': 1.04,
    'bihar': 1.0,
    'west bengal': 0.98,
    'karnataka': 1.08,
    'tamil nadu': 1.07,
    'telangana': 1.09,
    'andhra pradesh': 1.08,
    'kerala': 0.95,
    'assam': 0.92,
    'odisha': 1.02,
    'chhattisgarh': 1.06,
    'jharkhand': 1.02,
    'himachal': 0.95,
    'uttarakhand': 0.98,
    'jammu': 0.96,
    'goa': 1.04,
}

DEFAULT_SUBSIDY_INR = 108000

