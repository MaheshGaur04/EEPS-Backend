from django.urls import path

from accounts.views import AdminUserMessageView
from contacts.views import (
    AdminContactDetailView,
    AdminContactListView,
    AdminContactReplyView,
    AdminContactReviewView,
)

from .views import (
    AdminServiceRequestDetailView,
    AdminServiceRequestListView,
    AdminServiceRequestStatusView,
    AdminUserContactsView,
    AdminUserDetailView,
    AdminUserListView,
)

urlpatterns = [
    path('contacts', AdminContactListView.as_view()),
    path('contacts/<int:pk>', AdminContactDetailView.as_view()),
    path('contacts/<int:pk>/review', AdminContactReviewView.as_view()),
    path('contacts/<int:pk>/reply', AdminContactReplyView.as_view()),
    path('users', AdminUserListView.as_view()),
    path('users/<int:pk>', AdminUserDetailView.as_view()),
    path('users/<int:pk>/contacts', AdminUserContactsView.as_view()),
    path('users/<int:pk>/messages', AdminUserMessageView.as_view()),
    path('service-requests', AdminServiceRequestListView.as_view()),
    path('service-requests/<int:pk>', AdminServiceRequestDetailView.as_view()),
    path('service-requests/<int:pk>/status', AdminServiceRequestStatusView.as_view()),
]
