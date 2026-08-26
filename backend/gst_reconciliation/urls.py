from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GSTReconciliationViewSet

router = DefaultRouter()
router.register(r'reconciliation', GSTReconciliationViewSet, basename='gst-reconciliation')

# Standalone GET for raw GSTR-2B invoice listing (used by GSTR2 → GSTR-2B sub-tab)
_view = GSTReconciliationViewSet.as_view({'get': 'list_invoices'})

urlpatterns = [
    path('reconciliation/invoices/', _view, name='gst-reconciliation-invoices'),
    path('', include(router.urls)),
]
