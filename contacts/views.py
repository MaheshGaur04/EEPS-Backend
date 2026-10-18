from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.models import AdminMessage, User, UserRole
from accounts.permissions import IsSuperAdmin
from accounts.serializers import AdminMessageSerializer

from .models import Contact
from .serializers import ContactCreateSerializer, ContactSerializer


class ContactSubmitView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'contact'

    def post(self, request):
        serializer = ContactCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        contact = serializer.save()
        return Response(
            {
                'message': 'Thanks! We will contact you shortly.',
                'contact': ContactSerializer(contact).data,
            },
            status=status.HTTP_201_CREATED,
        )


class AdminContactListView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        contacts = Contact.objects.all()[:200]
        return Response({'contacts': ContactSerializer(contacts, many=True).data})


class AdminContactDetailView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request, pk):
        contact = Contact.objects.filter(pk=pk).first()
        if not contact:
            return Response({'error': 'Contact not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'contact': ContactSerializer(contact).data})


class AdminContactReviewView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def patch(self, request, pk):
        contact = Contact.objects.filter(pk=pk).first()
        if not contact:
            return Response({'error': 'Contact not found'}, status=status.HTTP_404_NOT_FOUND)
        contact.reviewed = True
        contact.save(update_fields=['reviewed', 'updated_at'])
        return Response({'contact': ContactSerializer(contact).data})


class AdminContactReplyView(APIView):
    """Reply to a contact inquiry → notification for the matching customer account."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request, pk):
        contact = Contact.objects.filter(pk=pk).first()
        if not contact:
            return Response({'error': 'Contact not found'}, status=status.HTTP_404_NOT_FOUND)

        body = (request.data.get('body') or request.data.get('message') or '').strip()
        if not body:
            return Response({'error': 'Message cannot be empty'}, status=status.HTTP_400_BAD_REQUEST)
        if len(body) > 5000:
            return Response({'error': 'Message is too long'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email__iexact=contact.email, role=UserRole.CUSTOMER, is_active=True).first()
        if not user:
            return Response(
                {'error': 'No customer account found for this email. They must register to receive portal notifications.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        msg = AdminMessage.objects.create(recipient=user, sender=request.user, body=body)
        contact.replied = True
        contact.reviewed = True
        contact.save(update_fields=['replied', 'reviewed', 'updated_at'])
        return Response(
            {
                'message': 'Reply sent to customer notifications',
                'notification': AdminMessageSerializer(msg).data,
                'contact': ContactSerializer(contact).data,
            },
            status=status.HTTP_201_CREATED,
        )
