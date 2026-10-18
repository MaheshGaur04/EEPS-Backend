from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.test import APIClient

from accounts.models import User


class RoiAccountThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.first_user = User.objects.create_user(
            email='first@example.com',
            mobile='9876543210',
            password='StrongCustomerPassword123!',
            full_name='First Customer',
            location='Hamirpur',
        )
        self.second_user = User.objects.create_user(
            email='second@example.com',
            mobile='9876501234',
            password='AnotherStrongPassword123!',
            full_name='Second Customer',
            location='Kanpur',
        )
        self.payload = {
            'monthlyBill': 6000,
            'averageLoadKw': 4,
            'rooftopSizeSqft': 450,
            'location': 'Hamirpur, Uttar Pradesh',
        }

    @patch('roi.views.call_gemini_narrative', return_value=None)
    @patch.object(ScopedRateThrottle, 'THROTTLE_RATES', {'roi_calculate': '2/day'})
    def test_account_can_calculate_roi_twice_per_day(self, _gemini_patch):
        self.client.force_authenticate(user=self.first_user)

        first = self.client.post('/api/roi/calculate', self.payload, format='json')
        second = self.client.post('/api/roi/calculate', self.payload, format='json')
        third = self.client.post('/api/roi/calculate', self.payload, format='json')

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(third.status_code, 429)

    @patch('roi.views.call_gemini_narrative', return_value=None)
    @patch.object(ScopedRateThrottle, 'THROTTLE_RATES', {'roi_calculate': '2/day'})
    def test_roi_limit_is_independent_per_account(self, _gemini_patch):
        self.client.force_authenticate(user=self.first_user)
        for _ in range(2):
            response = self.client.post('/api/roi/calculate', self.payload, format='json')
            self.assertEqual(response.status_code, 200)

        self.client.force_authenticate(user=self.second_user)
        response = self.client.post('/api/roi/calculate', self.payload, format='json')

        self.assertEqual(response.status_code, 200)
