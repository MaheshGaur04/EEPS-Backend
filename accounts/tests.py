from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.test import APIClient
from .models import User


class RegistrationPasswordPolicyTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.payload = {
            'fullName': 'New Customer',
            'email': 'new-customer@example.com',
            'mobile': '9876501234',
            'password': 'VeryStrongPass123!',
            'location': 'Hamirpur',
        }

    def test_short_password_is_rejected(self):
        payload = {**self.payload, 'password': 'short'}

        response = self.client.post('/api/auth/register', payload, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.data['errors'])
        self.assertFalse(User.objects.filter(email=payload['email']).exists())

    def test_common_password_is_rejected(self):
        payload = {**self.payload, 'password': 'Password123456'}

        response = self.client.post('/api/auth/register', payload, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.data['errors'])
        self.assertFalse(User.objects.filter(email=payload['email']).exists())

    def test_numeric_password_is_rejected(self):
        payload = {**self.payload, 'password': '123456789012'}

        response = self.client.post('/api/auth/register', payload, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.data['errors'])
        self.assertFalse(User.objects.filter(email=payload['email']).exists())

    def test_password_similar_to_user_attributes_is_rejected(self):
        payload = {**self.payload, 'password': 'new-customer@example.com'}

        response = self.client.post('/api/auth/register', payload, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.data['errors'])
        self.assertFalse(User.objects.filter(email=payload['email']).exists())

    def test_strong_password_is_accepted(self):
        response = self.client.post('/api/auth/register', self.payload, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(email=self.payload['email']).exists())


class LoginSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='customer@example.com',
            mobile='9876543210',
            password='StrongPass123!',
            full_name='Test Customer',
            location='Hamirpur',
        )

    def test_invalid_credentials_have_same_response(self):
        responses = [
            self.client.post(
                '/api/auth/login',
                {'identifier': 'missing@example.com', 'password': 'WrongPass123!'},
                format='json',
            ),
            self.client.post(
                '/api/auth/login',
                {'identifier': self.user.email, 'password': 'WrongPass123!'},
                format='json',
            ),
        ]
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        responses.append(self.client.post(
            '/api/auth/login',
            {'identifier': self.user.email, 'password': 'StrongPass123!'},
            format='json',
        ))

        self.assertEqual([response.status_code for response in responses], [401, 401, 401])
        self.assertEqual([response.data for response in responses], [
            {'error': 'Invalid email/mobile or password'},
            {'error': 'Invalid email/mobile or password'},
            {'error': 'Invalid email/mobile or password'},
        ])

    @patch.object(ScopedRateThrottle, 'THROTTLE_RATES', {'login': '1/minute'})
    def test_login_is_throttled(self):
        payload = {'identifier': self.user.email, 'password': 'StrongPass123!'}

        first = self.client.post('/api/auth/login', payload, format='json')
        second = self.client.post('/api/auth/login', payload, format='json')

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)

    @patch.object(ScopedRateThrottle, 'THROTTLE_RATES', {'register': '1/minute'})
    def test_registration_is_throttled(self):
        payload = {
            'fullName': 'New Customer',
            'email': 'new-customer@example.com',
            'mobile': '9876501234',
            'password': 'StrongPass123!',
            'location': 'Hamirpur',
        }

        first = self.client.post('/api/auth/register', payload, format='json')
        second = self.client.post('/api/auth/register', payload, format='json')

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 429)

    @patch.object(ScopedRateThrottle, 'THROTTLE_RATES', {'refresh': '1/minute'})
    def test_refresh_is_throttled(self):
        first = self.client.post('/api/auth/refresh', {}, format='json')
        second = self.client.post('/api/auth/refresh', {}, format='json')

        self.assertEqual(first.status_code, 401)
        self.assertEqual(second.status_code, 429)
