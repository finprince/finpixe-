import os
import logging
logger = logging.getLogger(__name__)
from rest_framework import viewsets, status, generics, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes, authentication_classes, action
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from .models import Branch
from .serializers import UserSignupSerializer, TenantSerializer
from .mixins import BranchQuerysetMixin, IsBranchMember
from .exceptions import UsageLimitExceeded, BusinessException, ExternalServiceError

class SignupView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = UserSignupSerializer
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def health_check(request):
    return Response({'status': 'ok', 'timestamp': timezone.now().isoformat()})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_status(request):
    return Response({'isActive': True})

@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def check_phone(request):
    """Check if a phone number is already registered."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    phone = request.query_params.get('phone', '').strip()
    if not phone:
        return Response({'error': 'Phone number required'}, status=status.HTTP_400_BAD_REQUEST)
    exists = User.objects.filter(phone=phone).exists()
    return Response({'exists': exists})
from .ai_proxy import ai_service
from .processing_engine import safe_json_load



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ai_metrics(request):
    """Get AI service metrics (Redis removed)"""
    stats = ai_service.get_stats()
    return Response({**stats, 'metrics_5min': {'status': 'Redis metrics removed - check observability logs'}})

@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([])
def health_with_metrics(request):
    """Enhanced health check with basic metrics"""
    from django.db import connections
    from django.core.cache import cache
    db_status = 'ok'
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute('SELECT 1')
    except:
        db_status = 'error'
    cache_status = 'ok'
    try:
        cache.set('health_test', 'ok', 1)
        if cache.get('health_test') != 'ok':
            cache_status = 'error'
    except:
        cache_status = 'error'
    stats = ai_service.get_stats()
    ai_stats = {'total_requests': stats.get('total_requests', 0), 'cache_hits': stats.get('cache_hits', 0), 'circuit_breaker_open': stats.get('circuit_breaker_open', False), 'api_keys_unhealthy': stats.get('api_keys_unhealthy', 0)}
    return Response({'status': 'ok' if db_status == 'ok' and cache_status == 'ok' else 'error', 'timestamp': timezone.now().isoformat(), 'services': {'database': db_status, 'cache': cache_status, 'ai_service': 'ok'}, 'ai_metrics': ai_stats})

class AdminSubscriptionsView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.filter(is_superuser=False).order_by('-created_at')
        subscriptions = []
        for user in users:
            is_online = False
            if user.last_login:
                time_threshold = timezone.now() - timedelta(minutes=60)
                if user.last_login > time_threshold:
                    is_online = True
            login_status = 'Online' if is_online else 'Offline'
            subscription = {'id': user.id, 'username': user.username, 'companyName': user.company_name, 'registrationDate': user.created_at.isoformat(), 'subscriptionPlan': user.selected_plan, 'subscriptionStartDate': user.created_at.isoformat(), 'subscriptionEndDate': user.created_at.replace(year=user.created_at.year + 1).isoformat(), 'totalUploads': 1000, 'uploadsUsed': 0, 'isActive': user.is_active, 'tenantId': user.tenant_id, 'lastLogin': user.last_login.isoformat() if user.last_login else user.created_at.isoformat(), 'loginStatus': login_status}
            subscriptions.append(subscription)
        return Response(subscriptions)

    def put(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user_id = request.data.get('userId')
        is_active = request.data.get('isActive')
        if user_id is None or is_active is None:
            return Response({'error': 'userId and isActive required'}, status=400)
        try:
            user = User.objects.get(id=user_id)
            user.is_active = is_active
            user.save()
            return Response({'success': True})
        except User.DoesNotExist:
            from django.http import Http404
            raise Http404('Requested resource not found.')

class AdminPaymentsView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.all().order_by('-created_at')
        payments = []
        for user in users:
            amount = 0
            if user.selected_plan == 'Pro':
                amount = 2999
            elif user.selected_plan == 'Enterprise':
                amount = 9999
            payments.append({'id': user.id, 'username': user.username, 'companyName': user.company_name, 'totalAmountPaid': amount})
        return Response(payments)

@method_decorator(csrf_exempt, name='dispatch')
class AIProxyView(views.APIView):
    """Unified AI proxy endpoint for all AI operations"""

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        from rest_framework.exceptions import ParseError
        raise ParseError('OLD AI PROXY SHOULD NOT BE USED. Use ocr_pipeline instead.')

    def post(self, request, action):
        import time
        start_time = time.time()
        if not request.user.is_authenticated:
            return Response({'error': 'AI service busy. Please try again later.'}, status=429)
        user_id = str(request.user.id)
        tenant_id = getattr(request.user, 'tenant_id', None)
        if not tenant_id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Valid Branch context is required for AI operations.')
        tenant_id = str(tenant_id)
        if action == 'extract-invoice':
            if 'file' not in request.FILES:
                return Response({'error': 'No file provided.'}, status=400)
            file_obj = request.FILES['file']
            voucher_type = request.data.get('voucher_type', 'Purchase')
            table_name = request.data.get('table_name', voucher_type)
            extraction_mode = request.data.get('extraction_mode', 'ai_native')
            import json as _json
            columns_data = request.data.get('columns', '[]')
            try:
                columns_list = safe_json_load(columns_data)
            except Exception:
                columns_list = []
            from .ai_service import create_dynamic_voucher_extraction_request
            result = create_dynamic_voucher_extraction_request(file_obj, voucher_type=voucher_type, table_name=table_name, columns=columns_list, mime_type=file_obj.content_type, user_id=user_id, tenant_id=tenant_id)
            if result.get('status') == 'queued':
                return Response(result)
            if 'error' in result:
                raise ExternalServiceError(result.get('error', 'AI service is temporarily unavailable.'))
            is_duplicate = result.get('duplicate', False)
            if is_duplicate:
                cached_data = result.get('cached_data', {})
                return Response({'success': True, 'from_cache': True, 'duplicate': True, 'message': result.get('message', 'Invoice already scanned.'), 'cache_record_id': result.get('cache_record_id'), 'data': {'invoice': cached_data.get('invoice', {}), 'items': cached_data.get('items', [])}})
            from .usage_service import check_and_increment_usage
            plan = getattr(request.user, 'selected_plan', 'FREE') or 'FREE'
            plan = plan.upper()
            LIMITS = {'FREE': 5, 'STARTER': 100, 'PRO': float('inf')}
            limit = LIMITS.get(plan, 5)
            if limit != float('inf'):
                if not check_and_increment_usage(tenant_id, limit):
                    raise UsageLimitExceeded(f'Monthly AI extraction limit of {limit} has been reached.')
            raw_text = result.get('reply', '').strip()
            from .processing_engine import parse_and_process_ocr
            try:
                processed_data = parse_and_process_ocr(raw_text)
                invoice_data = processed_data.get('invoice', {})
                items = processed_data.get('items', [])
            except Exception as e:
                logger.error(f'Mapping Engine failed: {e}')
                return Response({'error': f'Failed to parse AI response: {str(e)}'}, status=500)
            end_time = time.time()
            from .models import ExtractionPerformance
            ExtractionPerformance.objects.create(file_count=1, processing_time_seconds=end_time - start_time)
            return Response({'success': True, 'from_cache': False, 'duplicate': False, 'cache_record_id': result.get('cache_record_id'), 'data': {'invoice': invoice_data, 'items': items}})
        elif action == 'extract-master':
            if 'file' not in request.FILES:
                return Response({'error': 'No file provided.'}, status=400)
            from .usage_service import check_and_increment_usage
            plan = getattr(request.user, 'selected_plan', 'FREE') or 'FREE'
            plan = plan.upper()
            LIMITS = {'FREE': 5, 'STARTER': 100, 'PRO': float('inf')}
            limit = LIMITS.get(plan, 5)
            if limit != float('inf'):
                if not check_and_increment_usage(tenant_id, limit):
                    raise UsageLimitExceeded(f'Monthly AI extraction limit of {limit} has been reached.')
            file_obj = request.FILES['file']
            from .ai_service import create_master_processing_request
            result = create_master_processing_request(file_obj, mime_type=file_obj.content_type, user_id=user_id, tenant_id=tenant_id)
            if 'error' in result:
                raise ExternalServiceError(result.get('error', 'AI service is temporarily unavailable.'))
            import json as _json
            raw_text = result.get('reply', '').strip()
            if raw_text.startswith('```json'):
                raw_text = raw_text[7:]
            if raw_text.startswith('```'):
                raw_text = raw_text[3:]
            if raw_text.endswith('```'):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()
            try:
                master_data = safe_json_load(raw_text)
            except Exception:
                return Response({'error': 'Failed to parse AI response as JSON.'}, status=500)
            if not isinstance(master_data, dict):
                master_data = {}
            for k, v in master_data.items():
                if v is None:
                    master_data[k] = ''
            return Response({'success': True, 'data': {'master': master_data}})
        elif action == 'agent-message':
            msg = request.data.get('message', '').strip()
            if not msg:
                raise BusinessException('Message is required.')
            request_data = {'message': msg, 'contextData': request.data.get('contextData', ''), 'useGrounding': request.data.get('useGrounding', False)}
            result = ai_service.make_request('agent', request_data, user_id, tenant_id)
        else:
            raise BusinessException('Invalid action.')
        if result.get('status') == 'queued':
            return Response(result)
        if 'error' in result:
            raise ExternalServiceError(result.get('error', 'AI service is temporarily unavailable.'))
        return Response(result)

    def get(self, request, action):
        """Get AI service stats"""
        if action == 'stats':
            if not request.user.is_staff:
                return Response({'error': 'Unauthorized'}, status=403)
            return Response(ai_service.get_stats())
        return Response({'error': 'Unknown action'}, status=400)
from rest_framework.permissions import IsAdminUser

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def extraction_average_time(request):
    from .models import ExtractionPerformance
    from django.db.models import Avg
    avg_data = ExtractionPerformance.objects.aggregate(Avg('processing_time_seconds'))
    avg_time = avg_data['processing_time_seconds__avg']
    if avg_time is None:
        avg_time = 3.85
    return Response({'average_time_per_invoice': round(float(avg_time), 2)})

@method_decorator(csrf_exempt, name='dispatch')
class OCRCacheUpdateView(views.APIView):
    """
    PATCH /api/ai/ocr-cache/<record_id>/update/

    Update the extracted_data JSON in invoice_ocr_temp when the user edits
    invoice fields after scanning.  OCR is *never* re-run.
    """

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        from rest_framework.exceptions import ParseError
        raise ParseError('OLD OCR CACHE UPDATE SHOULD NOT BE USED. Use ocr_pipeline instead.')
    permission_classes = [IsAuthenticated]

    def patch(self, request, record_id):
        import json as _json
        from django.db import connection
        tenant_id = getattr(request.user, 'tenant_id', None)
        if not tenant_id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Authentication with a valid tenant is required.')
        extracted_data = request.data.get('extracted_data')
        if not extracted_data or not isinstance(extracted_data, dict):
            return Response({'error': 'extracted_data (dict) is required in the request body.'}, status=400)
        try:
            with connection.cursor() as cursor:
                cursor.execute('\n                    SELECT id FROM invoice_ocr_temp\n                    WHERE  id = %s AND tenant_id = %s AND expires_at > NOW()\n                    ', [record_id, str(tenant_id)])
                row = cursor.fetchone()
        except Exception as exc:
            logger.error('OCRCacheUpdateView DB error: %s', exc)
            return Response({'error': 'Database error.'}, status=500)
        if not row:
            return Response({'error': 'OCR cache record not found, expired, or access denied.'}, status=404)
        from core.ocr_cache import update_ocr_cache_extracted_data
        success = update_ocr_cache_extracted_data(record_id, extracted_data)
        if success:
            return Response({'success': True})
        return Response({'error': 'Failed to update OCR cache record.'}, status=500)

class BranchViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Branches (Branch level)
    """
    queryset = Branch.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from .models import MasterUser
        queryset = Branch.objects.all()
        if isinstance(self.request.user, MasterUser):
            return queryset.order_by('name')
        return queryset.filter(id=self.request.user.tenant_id)