from django.db.models import Case, IntegerField, Q, When
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User, UserRole
from accounts.permissions import IsSuperAdmin
from accounts.serializers import UserPublicSerializer
from contacts.models import Contact
from contacts.serializers import ContactSerializer

from .mailer import send_status_email
from .models import ServiceRequest, ServiceRequestStatus
from .serializers import (
    ServiceRequestListSerializer,
    ServiceRequestSerializer,
    ServiceRequestWriteSerializer,
)

PRIORITY_ORDER = Case(
    When(priority='URGENT', then=1),
    When(priority='HIGH', then=2),
    When(priority='MEDIUM', then=3),
    When(priority='LOW', then=4),
    default=3,
    output_field=IntegerField(),
)

EDITABLE_STATUSES = {ServiceRequestStatus.PENDING, ServiceRequestStatus.REJECTED}


class MyServiceRequestListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = ServiceRequest.objects.filter(user=request.user, archived=False).order_by('-created_at')
        return Response({'serviceRequests': ServiceRequestListSerializer(qs, many=True).data})

    def post(self, request):
        serializer = ServiceRequestWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        sr = ServiceRequest.objects.create(
            user=request.user,
            subject=data['subject'],
            category=data['category'],
            service_type=data['serviceType'],
            system_size=data['systemSize'],
            property_address=data['propertyAddress'],
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            preferred_date=data.get('preferredDate') or None,
            priority=data.get('priority', 'MEDIUM'),
            description=data['description'],
            status=ServiceRequestStatus.PENDING,
        )
        return Response(
            {
                'message': 'Your service created successfully, waiting for admin approval',
                'serviceRequest': ServiceRequestSerializer(sr).data,
            },
            status=status.HTTP_201_CREATED,
        )


class MyServiceRequestDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        sr = ServiceRequest.objects.filter(pk=pk).first()
        if not sr:
            return Response({'error': 'Service request not found'}, status=status.HTTP_404_NOT_FOUND)
        if sr.archived:
            return Response({'error': 'Cannot update archived request'}, status=status.HTTP_400_BAD_REQUEST)
        if sr.user_id != request.user.id:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        if sr.status not in EDITABLE_STATUSES:
            return Response({'error': f'Cannot edit request in status {sr.status}'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ServiceRequestWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        mapping = {
            'subject': 'subject',
            'category': 'category',
            'serviceType': 'service_type',
            'systemSize': 'system_size',
            'propertyAddress': 'property_address',
            'preferredDate': 'preferred_date',
            'priority': 'priority',
            'description': 'description',
            'latitude': 'latitude',
            'longitude': 'longitude',
        }
        for src, dest in mapping.items():
            if src in data:
                setattr(sr, dest, data[src])
        sr.save()
        return Response({'message': 'Service request updated', 'serviceRequest': ServiceRequestSerializer(sr).data})

    def delete(self, request, pk):
        sr = ServiceRequest.objects.filter(pk=pk).first()
        if not sr:
            return Response({'error': 'Service request not found'}, status=status.HTTP_404_NOT_FOUND)
        if sr.user_id != request.user.id and request.user.role != UserRole.SUPER_ADMIN:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        sr.archived = True
        sr.archived_at = timezone.now()
        sr.archived_by = request.user
        sr.save(update_fields=['archived', 'archived_at', 'archived_by', 'updated_at'])
        return Response({'message': 'Service request archived'})


class AdminUserListView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        q = (request.query_params.get('q') or '').strip()
        qs = User.objects.filter(role=UserRole.CUSTOMER)
        if q:
            qs = qs.filter(Q(full_name__icontains=q) | Q(email__icontains=q) | Q(mobile__icontains=q))
        qs = qs.order_by('-created_at')[:200]
        return Response({'users': UserPublicSerializer(qs, many=True).data})


class AdminUserDetailView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request, pk):
        user = User.objects.filter(pk=pk).first()
        if not user:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        srs = ServiceRequest.objects.filter(user=user, archived=False).order_by('-created_at')
        return Response({
            'user': UserPublicSerializer(user).data,
            'serviceRequests': ServiceRequestListSerializer(srs, many=True).data,
        })

    def delete(self, request, pk):
        user = User.objects.filter(pk=pk).first()
        if not user:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        if user.pk == request.user.pk:
            return Response({'error': 'You cannot delete your own account'}, status=status.HTTP_400_BAD_REQUEST)
        if user.role != UserRole.CUSTOMER:
            return Response({'error': 'Only customer accounts can be deleted here'}, status=status.HTTP_400_BAD_REQUEST)
        email = user.email
        name = user.full_name
        user.delete()
        return Response({'message': f'Customer {name} ({email}) deleted'})


class AdminUserContactsView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request, pk):
        user = User.objects.filter(pk=pk).first()
        if not user:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        contacts = Contact.objects.filter(email__iexact=user.email).order_by('-created_at')
        return Response({'contacts': ContactSerializer(contacts, many=True).data})


class AdminServiceRequestListView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        qs = ServiceRequest.objects.all()
        status_filter = (request.query_params.get('status') or '').strip()
        if status_filter:
            qs = qs.filter(status=status_filter)

        include_archived = (request.query_params.get('includeArchived') or '').lower() == 'true'
        if not include_archived:
            qs = qs.filter(archived=False)

        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except ValueError:
            page = 1
        try:
            limit = max(1, min(200, int(request.query_params.get('limit', 20))))
        except ValueError:
            limit = 20

        total = qs.count()
        pages = max(1, (total + limit - 1) // limit)
        skip = (page - 1) * limit
        items = qs.annotate(priority_rank=PRIORITY_ORDER).order_by('priority_rank', '-created_at')[skip:skip + limit]
        return Response({
            'serviceRequests': ServiceRequestSerializer(items, many=True).data,
            'total': total,
            'page': page,
            'pages': pages,
        })

    def delete(self, request):
        ServiceRequest.objects.all().delete()
        return Response({'message': 'All service requests deleted'})


class AdminServiceRequestDetailView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request, pk):
        sr = ServiceRequest.objects.select_related('user').filter(pk=pk).first()
        if not sr:
            return Response({'error': 'Service request not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'serviceRequest': ServiceRequestSerializer(sr).data})

    def delete(self, request, pk):
        sr = ServiceRequest.objects.filter(pk=pk).first()
        if not sr:
            return Response({'error': 'Service request not found'}, status=status.HTTP_404_NOT_FOUND)
        sr.archived = True
        sr.archived_at = timezone.now()
        sr.archived_by = request.user
        sr.save(update_fields=['archived', 'archived_at', 'archived_by', 'updated_at'])
        return Response({'message': 'Service request archived'})


class AdminServiceRequestStatusView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def patch(self, request, pk):
        new_status = request.data.get('status')
        if new_status not in ServiceRequestStatus.values:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        sr = ServiceRequest.objects.select_related('user').filter(pk=pk).first()
        if not sr:
            return Response({'error': 'Service request not found'}, status=status.HTTP_404_NOT_FOUND)
        prev = sr.status
        sr.status = new_status
        sr.save(update_fields=['status', 'updated_at'])
        if sr.user and sr.user.email:
            send_status_email(sr.user.email, sr.user.full_name, sr, new_status)
        return Response({'serviceRequest': ServiceRequestSerializer(sr).data, 'prevStatus': prev})
