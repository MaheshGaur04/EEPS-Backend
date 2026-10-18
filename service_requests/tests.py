from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User, UserRole
from .models import ServiceRequest


class AdminServiceRequestDeletionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            mobile='9999999999',
            password='SecureAdminPassword123!',
            full_name='Test Admin',
            location='HQ',
        )
        self.customer = User.objects.create_user(
            email='customer@example.com',
            mobile='9876543210',
            password='StrongCustomerPassword123!',
            full_name='Test Customer',
            location='Hamirpur',
            role=UserRole.CUSTOMER,
        )
        self.service_request = ServiceRequest.objects.create(
            user=self.customer,
            subject='Panel inspection',
            category='Maintenance',
            service_type='Inspection',
            system_size='5 kW',
            property_address='Hamirpur',
            description='Inspect rooftop solar panels and wiring.',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_bulk_delete_endpoint_is_not_allowed(self):
        response = self.client.delete('/api/admin/service-requests')

        self.assertEqual(response.status_code, 405)
        self.assertTrue(ServiceRequest.objects.filter(pk=self.service_request.pk).exists())
        self.assertFalse(ServiceRequest.objects.get(pk=self.service_request.pk).archived)

    def test_single_request_delete_archives_instead_of_removing(self):
        response = self.client.delete(f'/api/admin/service-requests/{self.service_request.pk}')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(ServiceRequest.objects.filter(pk=self.service_request.pk).exists())
        archived = ServiceRequest.objects.get(pk=self.service_request.pk)
        self.assertTrue(archived.archived)
        self.assertIsNotNone(archived.archived_at)
        self.assertEqual(archived.archived_by, self.admin)
