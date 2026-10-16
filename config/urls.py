from django.contrib import admin
from django.urls import include, path

from accounts.views import HealthView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health', HealthView.as_view()),
    # Keep auth/roi/admin parents with trailing slash so nested paths resolve
    # (e.g. api/auth/ + login → api/auth/login).
    path('api/auth/', include('accounts.urls')),
    path('api/roi/', include('roi.urls')),
    path('api/weather/', include('weather.urls')),
    path('api/admin/', include('service_requests.admin_urls')),
    # List endpoints must match frontend (no trailing slash): /api/contact, /api/service-requests
    path('api/contact', include('contacts.urls')),
    path('api/contact/', include('contacts.urls')),
    path('api/service-requests', include('service_requests.urls')),
    path('api/service-requests/', include('service_requests.urls')),
]
