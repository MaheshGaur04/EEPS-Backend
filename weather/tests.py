import json
from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase

from .services import get_weather_for_query, reverse_geocode


class ReverseGeocodeTests(SimpleTestCase):
    @patch('weather.services.urllib.request.urlopen')
    def test_returns_readable_place_for_coordinates(self, urlopen):
        response = urlopen.return_value.__enter__.return_value
        response.read.return_value = json.dumps({
            'address': {
                'city': 'Lucknow',
                'state': 'Uttar Pradesh',
                'country': 'India',
            },
        }).encode()

        place = reverse_geocode(26.8467, 80.9462)

        self.assertEqual(place['name'], 'Lucknow, Uttar Pradesh, India')
        self.assertEqual(place['latitude'], 26.8467)
        self.assertEqual(place['longitude'], 80.9462)
        request = urlopen.call_args.args[0]
        self.assertIn('zoom=16', request.full_url)

    @patch('weather.services.urllib.request.urlopen', side_effect=OSError('geocoder unavailable'))
    def test_does_not_present_coordinates_as_a_place_when_geocoding_fails(self, _urlopen):
        self.assertIsNone(reverse_geocode(26.8467, 80.9462))


class WeatherCacheTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    @patch('weather.services.build_weather_payload', return_value={'provider': 'Open-Meteo'})
    @patch('weather.services.fetch_forecast', return_value={'current': {}})
    @patch(
        'weather.services.geocode_location',
        return_value={
            'name': 'Hamirpur, India',
            'latitude': 25.95,
            'longitude': 80.15,
            'timezone': 'Asia/Kolkata',
        },
    )
    def test_reuses_recent_weather_for_equivalent_location_queries(
        self, geocode_location, fetch_forecast, build_weather_payload
    ):
        first = get_weather_for_query(location='Hamirpur')
        second = get_weather_for_query(location=' hamirpur ')

        self.assertEqual(first, second)
        geocode_location.assert_called_once_with('Hamirpur')
        fetch_forecast.assert_called_once()
        build_weather_payload.assert_called_once()
