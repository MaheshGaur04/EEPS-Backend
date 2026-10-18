from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.test import APIClient
class ContactSubmissionThrottleTests(TestCase):
    @patch.object(ScopedRateThrottle, 'THROTTLE_RATES', {'contact': '1/minute'})
    def test_public_contact_submission_is_throttled(self):
        cache.clear()
        client = APIClient()
        payload = {
            'name': 'Test Customer',
            'email': 'customer@example.com',
            'phone': '9876543210',
            'message': 'Please contact me about solar installation.',
        }

        first = client.post('/api/contact', payload, format='json')
        second = client.post('/api/contact', payload, format='json')

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 429)
