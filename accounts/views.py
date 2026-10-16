from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AdminMessage, User, UserRole
from .permissions import IsSuperAdmin
from .serializers import AdminMessageSerializer, LoginSerializer, RegisterSerializer, UserPublicSerializer
from .tokens import TokenError, decode_refresh_token, issue_tokens_for_user


def set_refresh_cookie(response, refresh_token: str):
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.REFRESH_COOKIE_MAX_AGE,
        httponly=settings.REFRESH_COOKIE_HTTPONLY,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
        path=settings.REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(response):
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path=settings.REFRESH_COOKIE_PATH,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
    )


def first_error_message(errors):
    if isinstance(errors, dict):
        if 'non_field_errors' in errors:
            val = errors['non_field_errors']
            return val[0] if isinstance(val, list) else val
        for val in errors.values():
            if isinstance(val, list) and val:
                return val[0]
            if isinstance(val, str):
                return val
    if isinstance(errors, list) and errors:
        return errors[0]
    return 'Invalid request'


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'status': 'success', 'message': 'Earth Solutions API is running'})


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            msg = first_error_message(serializer.errors)
            if 'already exists' in str(msg):
                return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        access, refresh = issue_tokens_for_user(user)
        response = Response(
            {
                'message': 'Registration successful',
                'user': {
                    'id': user.pk,
                    'fullName': user.full_name,
                    'email': user.email,
                    'role': user.role,
                },
                'accessToken': access,
            },
            status=status.HTTP_201_CREATED,
        )
        set_refresh_cookie(response, refresh)
        return response


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            msg = str(first_error_message(serializer.errors))
            if 'No account found' in msg:
                return Response({'error': msg}, status=status.HTTP_404_NOT_FOUND)
            if 'Invalid email/mobile' in msg or 'inactive' in msg.lower():
                return Response({'error': msg}, status=status.HTTP_401_UNAUTHORIZED)
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']
        access, refresh = issue_tokens_for_user(user)
        response = Response(
            {
                'message': 'Login successful',
                'user': {
                    'id': user.pk,
                    'fullName': user.full_name,
                    'email': user.email,
                    'role': user.role,
                },
                'accessToken': access,
            }
        )
        set_refresh_cookie(response, refresh)
        return response


class RefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not raw:
            return Response({'error': 'Refresh token missing'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            payload = decode_refresh_token(raw)
            user = User.objects.filter(pk=payload['userId'], is_active=True).first()
            if not user:
                return Response({'error': 'User no longer exists'}, status=status.HTTP_401_UNAUTHORIZED)
            access, new_refresh = issue_tokens_for_user(user)
            response = Response({'accessToken': access})
            set_refresh_cookie(response, new_refresh)
            return response
        except TokenError:
            return Response({'error': 'Invalid or expired refresh token'}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        response = Response({'message': 'Logged out successfully'})
        clear_refresh_cookie(response)
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'user': UserPublicSerializer(request.user).data})


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = AdminMessage.objects.filter(recipient=request.user).select_related('sender')[:100]
        unread = AdminMessage.objects.filter(recipient=request.user, is_read=False).count()
        return Response({
            'notifications': AdminMessageSerializer(qs, many=True).data,
            'unreadCount': unread,
        })


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        msg = AdminMessage.objects.filter(pk=pk, recipient=request.user).first()
        if not msg:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)
        if not msg.is_read:
            msg.is_read = True
            msg.save(update_fields=['is_read'])
        return Response({'notification': AdminMessageSerializer(msg).data})


class NotificationDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        msg = AdminMessage.objects.filter(pk=pk, recipient=request.user).first()
        if not msg:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)
        msg.delete()
        return Response({'message': 'Notification deleted'})


class NotificationReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        updated = AdminMessage.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({'message': 'All notifications marked as read', 'updated': updated})


class AdminUserMessageView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request, pk):
        user = User.objects.filter(pk=pk).first()
        if not user:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        if user.role != UserRole.CUSTOMER:
            return Response({'error': 'Messages can only be sent to customers'}, status=status.HTTP_400_BAD_REQUEST)
        body = (request.data.get('body') or request.data.get('message') or '').strip()
        if not body:
            return Response({'error': 'Message cannot be empty'}, status=status.HTTP_400_BAD_REQUEST)
        if len(body) > 5000:
            return Response({'error': 'Message is too long'}, status=status.HTTP_400_BAD_REQUEST)
        msg = AdminMessage.objects.create(recipient=user, sender=request.user, body=body)
        return Response(
            {'message': 'Message sent', 'notification': AdminMessageSerializer(msg).data},
            status=status.HTTP_201_CREATED,
        )
