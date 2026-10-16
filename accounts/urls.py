from django.urls import path

from .views import (
    LoginView,
    LogoutView,
    MeView,
    NotificationDeleteView,
    NotificationListView,
    NotificationReadAllView,
    NotificationReadView,
    RefreshView,
    RegisterView,
)

urlpatterns = [
    path('register', RegisterView.as_view()),
    path('login', LoginView.as_view()),
    path('refresh', RefreshView.as_view()),
    path('logout', LogoutView.as_view()),
    path('me', MeView.as_view()),
    path('notifications', NotificationListView.as_view()),
    path('notifications/read-all', NotificationReadAllView.as_view()),
    path('notifications/<int:pk>/read', NotificationReadView.as_view()),
    path('notifications/<int:pk>', NotificationDeleteView.as_view()),
]
