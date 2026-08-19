from django.urls import path, include  # type: ignore
from rest_framework import routers  # type: ignore
from .auth_views import (
    CookieTokenObtainPairView, CookieTokenRefreshView, LogoutView, MeView,
    ForgotUserIDView, ForgotPasswordView, SwitchBranchView
)
from .views import (
    health_check, check_status, check_phone,
    AIProxyView,
    health_with_metrics, AdminPaymentsView,
    extraction_average_time, OCRCacheUpdateView,
    BranchViewSet
)
from .admin_views import AdminSubscriptionsView, AdminUserStatusView
from .direct_registration import DirectRegisterView
from .company_settings_views import CompanySettingsView
from .reports_views import (
    DayBookExcelView, LedgerExcelView, TrialBalanceExcelView, 
    StockSummaryExcelView, GSTReportExcelView,
    DaybookReportView, TrialBalanceReportView, BalanceSheetReportView,
    ProfitAndLossReportView, StockSummaryReportView,
)

from .tools_api import NoteReminderViewSet

router = routers.DefaultRouter()
router.register('branches', BranchViewSet, basename='branches')
router.register('tools/notes', NoteReminderViewSet, basename='tools-notes')

urlpatterns = [
    path('auth/me/', MeView.as_view(), name='auth-me'),
    path('auth/check-status/', check_status, name='check-status'),
    path('auth/check-phone/', check_phone, name='check-phone'),
    path('auth/forgot-userid/', ForgotUserIDView.as_view(), name='forgot-userid'),
    path('auth/forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('auth/forgot-userid/', ForgotUserIDView.as_view(), name='forgot-userid'),
    path('auth/forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('auth/switch-branch/', SwitchBranchView.as_view(), name='switch-branch'),
    path('health/', health_with_metrics, name='health'), # /api/health
    path('company-settings/', CompanySettingsView.as_view(), name='company-settings'),

    # Reports
    path('reports/daybook/excel/', DayBookExcelView.as_view(), name='report-daybook-excel'),
    path('reports/ledger/excel/', LedgerExcelView.as_view(), name='report-ledger-excel'),
    path('reports/trialbalance/excel/', TrialBalanceExcelView.as_view(), name='report-trialbalance-excel'),
    path('reports/stocksummary/excel/', StockSummaryExcelView.as_view(), name='report-stocksummary-excel'),
    path('reports/gst/excel/', GSTReportExcelView.as_view(), name='report-gst-excel'),
    # Phase 5: Additive JSON report endpoints
    path('reports/daybook/json/', DaybookReportView.as_view(), name='report-daybook-json'),
    path('reports/trialbalance/json/', TrialBalanceReportView.as_view(), name='report-trialbalance-json'),
    path('reports/pnl/json/', ProfitAndLossReportView.as_view(), name='report-pnl-json'),
    path('reports/balancesheet/json/', BalanceSheetReportView.as_view(), name='report-balancesheet-json'),
    path('reports/stocksummary/json/', StockSummaryReportView.as_view(), name='report-stocksummary-json'),

    # Admin endpoints
    path('admin/subscriptions/', AdminSubscriptionsView.as_view(), name='admin-subscriptions'),
    path('admin/user-subscription/', AdminUserStatusView.as_view(), name='admin-user-subscription'),
    path('admin/payments/', AdminPaymentsView.as_view(), name='admin-payments'),

    # AI Services
    path('ai/<str:action>/', AIProxyView.as_view(), name='ai-proxy'),
    path('kiki/', include('core.kiki.api.urls')),
    path('v2/kiki/', include('core.kiki.api.urls')),
    path('ai/ocr-cache/<int:record_id>/update/', OCRCacheUpdateView.as_view(), name='ocr-cache-update'),
    path('extraction-average-time/', extraction_average_time, name='extraction-average-time'),

    path('', include(router.urls)),
]

