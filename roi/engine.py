"""Deterministic solar ROI number engine (source of truth)."""

from __future__ import annotations

from .models import DEFAULT_IRRADIANCE_FACTORS, DEFAULT_SUBSIDY_INR, RoiPricingConfig


ORIENTATION_FACTORS = {
    'South': 1.0,
    'South-East': 0.96,
    'South-West': 0.96,
    'East': 0.9,
    'West': 0.9,
    'North': 0.78,
    'Flat': 0.92,
}

TILT_FACTORS = {
    'Low': 0.94,
    'Optimal': 1.0,
    'Steep': 0.95,
}

SHADING_FACTORS = {
    'Low': 1.0,
    'Medium': 0.88,
    'High': 0.72,
}

ROOF_TYPE_USABLE = {
    'Flat': 0.85,
    'Sloped': 0.75,
    'Mixed': 0.7,
}


def clamp(value: float, min_v: float, max_v: float) -> float:
    return min(max(value, min_v), max_v)


def pricing_as_dict(config: RoiPricingConfig | None = None) -> dict:
    cfg = config or RoiPricingConfig.get_solo()
    return {
        'costPerKw': cfg.cost_per_kw,
        'batteryCostPerKw': cfg.battery_cost_per_kw,
        'panelWattage': cfg.panel_wattage,
        'sqftPerKw': cfg.sqft_per_kw,
        'defaultTariffPerKwh': cfg.default_tariff_per_kwh,
        'savingsFraction': cfg.savings_fraction,
        'irradianceFactors': cfg.irradiance_factors or DEFAULT_IRRADIANCE_FACTORS,
        'subsidyINR': int(cfg.subsidy_inr or DEFAULT_SUBSIDY_INR),
    }


def irradiance_factor(location: str, factors: dict) -> float:
    loc = (location or '').lower()
    best = 1.0
    best_len = 0
    for key, value in (factors or {}).items():
        k = str(key).lower()
        if k in loc and len(k) > best_len:
            best = float(value)
            best_len = len(k)
    return best


def compute_subsidy(pricing: dict) -> int:
    """Fixed scheme assistance (default ₹1,08,000)."""
    return int(pricing.get('subsidyINR') or DEFAULT_SUBSIDY_INR)


def calculate_roi_numbers(payload: dict, pricing: dict | None = None) -> dict:
    """Return deterministic ROI numbers. Never calls Gemini."""
    p = pricing or pricing_as_dict()

    monthly_bill = float(payload['monthlyBill'])
    load_kw = float(payload['averageLoadKw'])
    roof_sqft = float(payload['rooftopSizeSqft'])
    location = payload.get('location') or ''
    roof_type = payload.get('roofType') or 'Sloped'
    battery = bool(payload.get('batteryBackup'))
    tariff = payload.get('tariffPerKwh')
    if tariff is None or tariff == '':
        tariff = p['defaultTariffPerKwh']
    tariff = float(tariff)

    orientation = payload.get('orientation') or 'South'
    tilt = payload.get('tilt') or 'Optimal'
    shading = payload.get('shading') or 'Low'

    usable_frac = ROOF_TYPE_USABLE.get(roof_type, 0.75)
    usable_sqft = roof_sqft * usable_frac
    max_kw_by_roof = usable_sqft / float(p['sqftPerKw'])

    # Bill-driven + load-driven sizing
    estimated_monthly_kwh = monthly_bill / max(tariff, 1.0)
    # ~120–140 generation kWh/kW/month typical India residential; use 130 * irradiance
    irr = irradiance_factor(location, p['irradianceFactors'])
    gen_per_kw_month = 130.0 * irr
    kw_from_bill = estimated_monthly_kwh / max(gen_per_kw_month, 1.0)
    kw_from_load = load_kw * 1.25
    raw_kw = (kw_from_bill * 0.55) + (kw_from_load * 0.45)

    site_factor = (
        ORIENTATION_FACTORS.get(orientation, 1.0)
        * TILT_FACTORS.get(tilt, 1.0)
        * SHADING_FACTORS.get(shading, 1.0)
    )
    # Compensating for poor site: slightly larger system if shading, but clamp by roof
    if shading == 'High':
        raw_kw *= 1.05

    recommended_kw = clamp(raw_kw, 1.0, min(max(max_kw_by_roof, 1.0), 15.0))
    recommended_kw = round(recommended_kw, 1)

    panel_w = int(p['panelWattage'])
    panel_count = max(4, int((recommended_kw * 1000 + panel_w - 1) // panel_w))

    cost_per_kw = float(p['batteryCostPerKw'] if battery else p['costPerKw'])
    # Mild metro premium already captured partly via irradiance; keep cost stable
    estimated_cost = int(round(recommended_kw * cost_per_kw))

    # Effective generation after site losses
    monthly_gen_kwh = recommended_kw * gen_per_kw_month * site_factor
    monthly_savings = int(round(min(monthly_bill * float(p['savingsFraction']), monthly_gen_kwh * tariff)))
    annual_savings = monthly_savings * 12

    subsidy = min(compute_subsidy(p), estimated_cost)
    net_cost = max(estimated_cost - subsidy, 0)
    payback = round(net_cost / max(annual_savings, 1), 2)

    return {
        'recommendedSystemSizeKw': recommended_kw,
        'estimatedCostINR': estimated_cost,
        'estimatedSavingsPerMonthINR': monthly_savings,
        'annualSavingsINR': annual_savings,
        'paybackYears': payback,
        'panelCount': panel_count,
        'subsidyINR': subsidy,
        'netCostINR': net_cost,
        'source': 'engine',
        'meta': {
            'irradianceFactor': round(irr, 3),
            'siteFactor': round(site_factor, 3),
            'maxKwByRoof': round(max_kw_by_roof, 2),
            'tariffPerKwh': tariff,
            'usableRoofSqft': round(usable_sqft, 1),
        },
    }


def build_template_narrative(payload: dict, numbers: dict) -> dict:
    kw = numbers['recommendedSystemSizeKw']
    monthly = numbers['estimatedSavingsPerMonthINR']
    payback = numbers['paybackYears']
    subsidy = numbers.get('subsidyINR', 0)
    roof_area = int(payload.get('rooftopSizeSqft') or 0)
    location = payload.get('location') or 'your area'

    suggestions = [
        f'A {kw} kW system fits your bill, load, and usable roof area in {location}.',
        f'Expected monthly savings are around ₹{monthly:,} after site and tariff adjustments.',
        (
            'Include battery backup if you need evening or outage coverage; it raises CapEx but improves resilience.'
            if payload.get('batteryBackup')
            else 'A grid-tied system is usually the most cost-effective path if bill reduction is the main goal.'
        ),
        (
            f'Central PM Surya Ghar assistance of about ₹{subsidy:,} can lower your net cost — confirm eligibility with your DISCOM.'
            if subsidy
            else 'Confirm state/DISCOM incentives in addition to any central scheme eligibility.'
        ),
    ]
    if roof_area < 350:
        suggestions.append('Roof area is tight — prefer high-efficiency modules and a compact layout.')
    elif numbers.get('meta', {}).get('siteFactor', 1) < 0.85:
        suggestions.append('Shading or orientation reduces yield — consider trimming trees or a slightly adjusted array layout.')

    summary = (
        f"For a property in {location} with {roof_area} sq ft roof and a ₹{int(payload['monthlyBill']):,} monthly bill, "
        f"a {kw} kW rooftop system is a practical fit. Gross cost is about ₹{numbers['estimatedCostINR']:,}; "
        f"after an estimated subsidy of ₹{subsidy:,}, net cost is ₹{numbers['netCostINR']:,} with a payback near {payback} years."
    )
    return {'summary': summary, 'suggestions': suggestions, 'narrativeSource': 'template'}
