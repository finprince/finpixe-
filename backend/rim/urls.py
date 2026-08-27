from django.urls import path
from .views import RIMProcessView, RIMHealthView

urlpatterns = [
    path('process/', RIMProcessView.as_view(), name='rim-process'),
    path('health/', RIMHealthView.as_view(), name='rim-health'),
]
