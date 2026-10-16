from rest_framework import authentication, exceptions

from .models import User
from .tokens import TokenError, decode_access_token


class AccessTokenAuthentication(authentication.BaseAuthentication):
    """Bearer access JWT verified with ACCESS_TOKEN_SECRET."""

    keyword = 'Bearer'
    www_authenticate_realm = 'api'

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).decode('utf-8')
        if not header:
            return None

        parts = header.split()
        if len(parts) != 2 or parts[0] != self.keyword:
            return None

        try:
            payload = decode_access_token(parts[1])
        except TokenError as exc:
            raise exceptions.AuthenticationFailed(str(exc)) from exc

        user = User.objects.filter(pk=payload['userId'], is_active=True).first()
        if not user:
            raise exceptions.AuthenticationFailed('User not found or inactive')

        return user, payload

    def authenticate_header(self, request):
        # Required so DRF returns 401 (not 403) for missing/expired tokens,
        # which lets the frontend refresh interceptor run.
        return f'{self.keyword} realm="{self.www_authenticate_realm}"'
