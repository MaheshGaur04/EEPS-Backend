from django.urls import path

from .views import ContactSubmitView

urlpatterns = [
    path('', ContactSubmitView.as_view()),
]
