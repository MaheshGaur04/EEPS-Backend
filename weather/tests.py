import json
from unittest.mock import patch

from django.test import SimpleTestCase

from .services import reverse_geocode


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
