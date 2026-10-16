from django.urls import path

from .views import MyServiceRequestDetailView, MyServiceRequestListCreateView

urlpatterns = [
    path('', MyServiceRequestListCreateView.as_view()),
    path('<int:pk>', MyServiceRequestDetailView.as_view()),
]
