import json
import time
import urllib.error
import urllib.request

from django.conf import settings
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.permissions import IsSuperAdmin

from .engine import build_template_narrative, calculate_roi_numbers, pricing_as_dict
from .models import RoiPricingConfig


class RoiInputSerializer(serializers.Serializer):
    monthlyBill = serializers.FloatField(min_value=500, max_value=200000)
    averageLoadKw = serializers.FloatField(min_value=0.5, max_value=50)
    rooftopSizeSqft = serializers.FloatField(min_value=100, max_value=10000)
    location = serializers.CharField(min_length=2)
    roofType = serializers.ChoiceField(choices=['Flat', 'Sloped', 'Mixed'], default='Sloped', required=False)
    batteryBackup = serializers.BooleanField(default=False, required=False)
    preferredUsage = serializers.CharField(default='Self consumption and savings', required=False)
    tariffPerKwh = serializers.FloatField(min_value=1, max_value=50, required=False, allow_null=True)
    orientation = serializers.ChoiceField(
        choices=['South', 'South-East', 'South-West', 'East', 'West', 'North', 'Flat'],
        default='South',
        required=False,
    )
    tilt = serializers.ChoiceField(choices=['Low', 'Optimal', 'Steep'], default='Optimal', required=False)
    shading = serializers.ChoiceField(choices=['Low', 'Medium', 'High'], default='Low', required=False)


class PricingConfigSerializer(serializers.ModelSerializer):
    costPerKw = serializers.IntegerField(source='cost_per_kw')
    batteryCostPerKw = serializers.IntegerField(source='battery_cost_per_kw')
    panelWattage = serializers.IntegerField(source='panel_wattage')
    sqftPerKw = serializers.FloatField(source='sqft_per_kw')
    defaultTariffPerKwh = serializers.FloatField(source='default_tariff_per_kwh')
    savingsFraction = serializers.FloatField(source='savings_fraction')
    irradianceFactors = serializers.JSONField(source='irradiance_factors', required=False)
    subsidyINR = serializers.IntegerField(source='subsidy_inr')

    class Meta:
        model = RoiPricingConfig
        fields = [
            'costPerKw',
            'batteryCostPerKw',
            'panelWattage',
            'sqftPerKw',
            'defaultTariffPerKwh',
            'savingsFraction',
            'irradianceFactors',
            'subsidyINR',
            'updated_at',
        ]
        read_only_fields = ['updated_at']


def _extract_narrative_json(raw: str):
    text = raw.strip().replace('```json', '').replace('```', '').strip()
    first = text.find('{')
    last = text.rfind('}')
    if first == -1 or last == -1:
        return None
    try:
        parsed = json.loads(text[first:last + 1])
        summary = parsed.get('summary')
        suggestions = parsed.get('suggestions')
        if not isinstance(summary, str) or not summary.strip():
            return None
        if not isinstance(suggestions, list):
            suggestions = []
        suggestions = [str(s) for s in suggestions if s][:6]
        return {'summary': summary.strip(), 'suggestions': suggestions, 'narrativeSource': 'gemini'}
    except json.JSONDecodeError:
        return None


def call_gemini_narrative(payload: dict, numbers: dict) -> dict | None:
    """Ask Gemini only for summary + suggestions. Never trust it for costs/kW."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return None

    prompt = (
        'You are an expert solar energy consultant for India. '
        'The system size and costs below were already calculated by our pricing engine — DO NOT change them. '
        'Respond ONLY with JSON (no markdown) containing keys: '
        'summary (string, 2-4 sentences explaining the recommendation to a homeowner), '
        'suggestions (array of 3-5 short actionable strings). '
        f'Customer inputs: {json.dumps(payload)}. '
        f'Engine numbers (fixed): {json.dumps({k: numbers[k] for k in numbers if k != "meta"})}.'
    )

    models = []
    primary = settings.GEMINI_MODEL
    for name in (primary, 'gemini-3.6-flash', 'gemini-3.5-flash', 'gemini-flash-latest'):
        if name and name not in models:
            models.append(name)

    body = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {
            'temperature': 0.35,
            'maxOutputTokens': 4096,
            'responseMimeType': 'application/json',
        },
    }
    encoded = json.dumps(body).encode('utf-8')

    for model in models:
        url = (
            f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
            f'?key={api_key}'
        )
        for attempt in range(3):
            req = urllib.request.Request(
                url,
                data=encoded,
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    result = json.loads(resp.read().decode('utf-8'))
                parts = result.get('candidates', [{}])[0].get('content', {}).get('parts', [])
                raw = parts[0].get('text') if parts else None
                parsed = _extract_narrative_json(raw) if raw else None
                if parsed:
                    return parsed
                print(f'Gemini narrative empty/invalid JSON from {model}')
                break
            except urllib.error.HTTPError as exc:
                err_body = exc.read().decode('utf-8', errors='ignore')
                print(f'Gemini narrative HTTP error {exc.code} ({model}): {err_body[:300]}')
                if exc.code == 503 and attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                break
            except Exception as exc:
                print(f'Gemini narrative failed ({model}): {exc}')
                break

    return None


class CalculateRoiView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'roi_calculate'

    def post(self, request):
        serializer = RoiInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        payload = serializer.validated_data
        pricing = pricing_as_dict()
        numbers = calculate_roi_numbers(payload, pricing)

        narrative = call_gemini_narrative(
            {
                'monthlyBill': payload['monthlyBill'],
                'averageLoadKw': payload['averageLoadKw'],
                'rooftopSizeSqft': payload['rooftopSizeSqft'],
                'location': payload['location'],
                'roofType': payload.get('roofType', 'Sloped'),
                'batteryBackup': payload.get('batteryBackup', False),
                'preferredUsage': payload.get('preferredUsage', 'Self consumption and savings'),
                'tariffPerKwh': payload.get('tariffPerKwh') or pricing['defaultTariffPerKwh'],
                'orientation': payload.get('orientation', 'South'),
                'tilt': payload.get('tilt', 'Optimal'),
                'shading': payload.get('shading', 'Low'),
            },
            numbers,
        )
        if not narrative:
            narrative = build_template_narrative(payload, numbers)

        estimate = {**numbers, **narrative}
        return Response({
            'message': 'Solar ROI estimate generated successfully',
            'estimate': estimate,
            'input': payload,
        })


class RoiPricingConfigView(APIView):
    """GET (authenticated) current defaults; PUT (super admin) update."""

    def get_permissions(self):
        if self.request.method == 'PUT':
            return [IsAuthenticated(), IsSuperAdmin()]
        return [IsAuthenticated()]

    def get(self, request):
        cfg = RoiPricingConfig.get_solo()
        return Response({'pricing': PricingConfigSerializer(cfg).data})

    def put(self, request):
        cfg = RoiPricingConfig.get_solo()
        serializer = PricingConfigSerializer(cfg, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response({'message': 'ROI pricing updated', 'pricing': serializer.data})
