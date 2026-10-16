from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError, AuthenticationFailed, NotAuthenticated, PermissionDenied


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    if isinstance(exc, ValidationError):
        detail = response.data
        if isinstance(detail, dict):
            # Flatten DRF field errors to match Express/zod style where useful
            response.data = {'errors': detail}
        else:
            response.data = {'error': str(detail)}
    elif isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        response.data = {'error': response.data.get('detail', 'Authentication required')}
    elif isinstance(exc, PermissionDenied):
        response.data = {'error': response.data.get('detail', 'Permission denied')}
    elif isinstance(response.data, dict) and 'detail' in response.data and len(response.data) == 1:
        response.data = {'error': response.data['detail']}

    return response
