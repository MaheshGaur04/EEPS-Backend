"""Open-Meteo weather + geocoding (real forecast data, no API key)."""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request

from django.core.cache import cache

GEOCODE_URL = 'https://geocoding-api.open-meteo.com/v1/search'
FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
# Open-Meteo reverse is unreliable; Nominatim is used for lat/lon → place name
NOMINATIM_REVERSE_URL = 'https://nominatim.openstreetmap.org/reverse'
WEATHER_CACHE_TIMEOUT = 300

# WMO weather interpretation codes → short label
WEATHER_CODES = {
    0: 'Clear sky',
    1: 'Mainly clear',
    2: 'Partly cloudy',
    3: 'Overcast',
    45: 'Fog',
    48: 'Depositing rime fog',
    51: 'Light drizzle',
    53: 'Moderate drizzle',
    55: 'Dense drizzle',
    56: 'Light freezing drizzle',
    57: 'Dense freezing drizzle',
    61: 'Slight rain',
    63: 'Moderate rain',
    65: 'Heavy rain',
    66: 'Light freezing rain',
    67: 'Heavy freezing rain',
    71: 'Slight snow',
    73: 'Moderate snow',
    75: 'Heavy snow',
    77: 'Snow grains',
    80: 'Slight rain showers',
    81: 'Moderate rain showers',
    82: 'Violent rain showers',
    85: 'Slight snow showers',
    86: 'Heavy snow showers',
    95: 'Thunderstorm',
    96: 'Thunderstorm with slight hail',
    99: 'Thunderstorm with heavy hail',
}


def _get_json(url: str, timeout: int = 20) -> dict:
    req = urllib.request.Request(url, headers={'User-Agent': 'EarthEnergy/1.0'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))


def describe_code(code) -> str:
    try:
        return WEATHER_CODES.get(int(code), 'Unknown')
    except (TypeError, ValueError):
        return 'Unknown'


def solar_outlook(cloud_cover: float | None, radiation: float | None, *, is_day: bool | None = None) -> str:
    cloud = float(cloud_cover or 0)
    rad = float(radiation or 0)
    if is_day is False or (is_day is None and rad < 20 and cloud < 90):
        # Night / very low sun angle — cloud cover still useful for tomorrow
        if cloud <= 30:
            return 'Nighttime now — clear skies favour strong generation after sunrise'
        if cloud <= 60:
            return 'Nighttime now — mixed skies; expect moderate generation tomorrow'
        return 'Nighttime now — heavy cloud may limit generation after sunrise'
    if cloud <= 25 and rad >= 400:
        return 'Excellent solar generation conditions'
    if cloud <= 45 and rad >= 250:
        return 'Good solar generation conditions'
    if cloud <= 70:
        return 'Moderate solar output expected'
    return 'Low solar output — heavy cloud cover'


def geocode_location(query: str, *, country_code: str = 'IN') -> dict | None:
    params = urllib.parse.urlencode({
        'name': query.strip(),
        'count': 5,
        'language': 'en',
        'format': 'json',
        'countryCode': country_code,
    })
    data = _get_json(f'{GEOCODE_URL}?{params}')
    results = data.get('results') or []
    if not results:
        # retry without country filter
        params = urllib.parse.urlencode({
            'name': query.strip(),
            'count': 5,
            'language': 'en',
            'format': 'json',
        })
        data = _get_json(f'{GEOCODE_URL}?{params}')
        results = data.get('results') or []
    if not results:
        return None
    hit = results[0]
    parts = [hit.get('name'), hit.get('admin1'), hit.get('country')]
    label = ', '.join([p for p in parts if p])
    return {
        'name': label,
        'latitude': hit['latitude'],
        'longitude': hit['longitude'],
        'timezone': hit.get('timezone') or 'Asia/Kolkata',
        'country': hit.get('country'),
        'admin1': hit.get('admin1'),
    }


def reverse_geocode(lat: float, lon: float) -> dict | None:
    params = urllib.parse.urlencode({
        'lat': lat,
        'lon': lon,
        'format': 'json',
        'zoom': 16,
        'addressdetails': 1,
    })
    try:
        req = urllib.request.Request(
            f'{NOMINATIM_REVERSE_URL}?{params}',
            headers={'User-Agent': 'EarthEnergy/1.0 (solar-roi; contact@earthenergy.local)'},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception as exc:
        print(f'Nominatim reverse failed: {exc}')
        return None

    address = data.get('address') or {}
    city = (
        address.get('city')
        or address.get('town')
        or address.get('village')
        or address.get('suburb')
        or address.get('county')
        or address.get('state_district')
    )
    state = address.get('state')
    country = address.get('country')
    parts = [city, state, country]
    name = ', '.join([p for p in parts if p]) or data.get('display_name')
    if not name:
        return None
    return {
        'name': name,
        'latitude': lat,
        'longitude': lon,
        'timezone': 'Asia/Kolkata',
        'country': country,
        'admin1': state,
    }


def fetch_forecast(lat: float, lon: float, timezone: str = 'auto') -> dict:
    params = urllib.parse.urlencode({
        'latitude': lat,
        'longitude': lon,
        'current': ','.join([
            'temperature_2m',
            'relative_humidity_2m',
            'apparent_temperature',
            'precipitation',
            'weather_code',
            'cloud_cover',
            'wind_speed_10m',
            'shortwave_radiation',
            'is_day',
        ]),
        'hourly': ','.join([
            'temperature_2m',
            'weather_code',
            'cloud_cover',
            'precipitation_probability',
            'shortwave_radiation',
        ]),
        'daily': ','.join([
            'weather_code',
            'temperature_2m_max',
            'temperature_2m_min',
            'precipitation_sum',
            'precipitation_probability_max',
            'sunshine_duration',
            'shortwave_radiation_sum',
            'wind_speed_10m_max',
        ]),
        'timezone': timezone or 'auto',
        'forecast_days': 7,
    })
    return _get_json(f'{FORECAST_URL}?{params}')


def build_weather_payload(place: dict, raw: dict) -> dict:
    current = raw.get('current') or {}
    daily = raw.get('daily') or {}
    hourly = raw.get('hourly') or {}

    days = []
    times = daily.get('time') or []
    for i, day in enumerate(times):
        sunshine_sec = (daily.get('sunshine_duration') or [None])[i]
        sunshine_hours = round(float(sunshine_sec) / 3600, 1) if sunshine_sec is not None else None
        rad_sum = (daily.get('shortwave_radiation_sum') or [None])[i]
        code = (daily.get('weather_code') or [None])[i]
        days.append({
            'date': day,
            'weatherCode': code,
            'condition': describe_code(code),
            'tempMaxC': (daily.get('temperature_2m_max') or [None])[i],
            'tempMinC': (daily.get('temperature_2m_min') or [None])[i],
            'precipitationMm': (daily.get('precipitation_sum') or [None])[i],
            'precipProbabilityPct': (daily.get('precipitation_probability_max') or [None])[i],
            'sunshineHours': sunshine_hours,
            'solarRadiationSum': rad_sum,
            'windMaxKmh': (daily.get('wind_speed_10m_max') or [None])[i],
            'solarOutlook': solar_outlook(
                None if rad_sum is None else (100 if float(rad_sum) < 8 else 40 if float(rad_sum) < 15 else 15),
                None if rad_sum is None else float(rad_sum) * 40,  # rough daytime avg proxy
            ),
        })

    # Next 12 daylight-relevant hours from now (first 12 returned slots are fine)
    hours = []
    h_times = hourly.get('time') or []
    for i, t in enumerate(h_times[:24]):
        code = (hourly.get('weather_code') or [None])[i]
        cloud = (hourly.get('cloud_cover') or [None])[i]
        rad = (hourly.get('shortwave_radiation') or [None])[i]
        hours.append({
            'time': t,
            'tempC': (hourly.get('temperature_2m') or [None])[i],
            'weatherCode': code,
            'condition': describe_code(code),
            'cloudCoverPct': cloud,
            'precipProbabilityPct': (hourly.get('precipitation_probability') or [None])[i],
            'solarRadiationWm2': rad,
        })

    cloud = current.get('cloud_cover')
    radiation = current.get('shortwave_radiation')

    return {
        'provider': 'Open-Meteo',
        'location': place,
        'current': {
            'time': current.get('time'),
            'tempC': current.get('temperature_2m'),
            'feelsLikeC': current.get('apparent_temperature'),
            'humidityPct': current.get('relative_humidity_2m'),
            'precipitationMm': current.get('precipitation'),
            'weatherCode': current.get('weather_code'),
            'condition': describe_code(current.get('weather_code')),
            'cloudCoverPct': cloud,
            'windKmh': current.get('wind_speed_10m'),
            'solarRadiationWm2': radiation,
            'isDay': bool(current.get('is_day')),
            'solarOutlook': solar_outlook(cloud, radiation, is_day=bool(current.get('is_day'))),
        },
        'hourly': hours,
        'daily': days,
        'units': raw.get('current_units') or {},
    }


def get_weather_for_query(*, location: str | None = None, lat: float | None = None, lon: float | None = None) -> dict:
    if lat is not None and lon is not None:
        cache_identity = f'coordinates:{lat:.5f}:{lon:.5f}'
    elif location and location.strip():
        cache_identity = f'location:{location.strip().casefold()}'
    else:
        raise ValueError('Provide location or lat/lon')

    cache_digest = hashlib.sha256(cache_identity.encode('utf-8')).hexdigest()
    cache_key = f'weather:forecast:v1:{cache_digest}'
    cached_weather = cache.get(cache_key)
    if cached_weather is not None:
        return cached_weather

    place = None
    if lat is not None and lon is not None:
        place = reverse_geocode(float(lat), float(lon))
    elif location and location.strip():
        place = geocode_location(location.strip())

    if not place:
        raise LookupError('Location not found')

    raw = fetch_forecast(place['latitude'], place['longitude'], place.get('timezone') or 'auto')
    weather = build_weather_payload(place, raw)
    cache.set(cache_key, weather, WEATHER_CACHE_TIMEOUT)
    return weather
