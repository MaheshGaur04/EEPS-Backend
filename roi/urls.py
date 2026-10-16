from django.urls import path

from .views import CalculateRoiView, RoiPricingConfigView

urlpatterns = [
    path('calculate', CalculateRoiView.as_view()),
    path('pricing', RoiPricingConfigView.as_view()),
]
