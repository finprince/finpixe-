from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.db import transaction, DatabaseError
from django.conf import settings
import logging
import json
import hashlib
import os
import time
from .models import InvoiceTempOCR, OCRJob, OCRTask, PipelineStatus, FinalizedSnapshot, RescanHistory
from vouchers.models import UploadSession
from .zoho_adapter import get_zoho_adapter
from .services.gst_restoration import restore_supplier_gst_values
logger = logging.getLogger(__name__)

def is_blank(val):
    return val is None or not str(val).strip() or str(val).strip() in {'None', 'null', '—', 'MISSING'}

def extract_fields(record):
    data = record.extracted_data or {}
    inv_no = record.supplier_invoice_no or data.get('invoice_no') or data.get('supplier_invoice_no') or data.get('header', {}).get('invoice_no') or data.get('header', {}).get('invoice_number') or data.get('sections', {}).get('supplier_details', {}).get('supplier_invoice_no')
    gstin = record.gstin or data.get('gstin') or data.get('header', {}).get('gstin') or data.get('header', {}).get('vendor_gstin') or data.get('sections', {}).get('supplier_details', {}).get('gstin')
    has_payload = bool(data and len(data) > 0)
    return (inv_no, gstin, has_payload)

def get_save_eligible_rows(upload_session_id, tenant_id=None):
    """
    Centralized helper for finalizing vouchers.
    Returns: list of (InvoiceTempOCR, UI_Row_Dict)
    ONLY rows where:
      - vendor_status == "ALREADY_EXIST"
      AND
      - voucher_status == "NEED_TO_SAVE"
      AND
      - item_status == "ALREADY EXIST"
    are eligible.
    """
    from vendors.vendor_validation_logic import build_session_vendor_map
    qs = InvoiceTempOCR.objects.filter(upload_session_id=upload_session_id)
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    records_list = list(qs)
    vendor_map = build_session_vendor_map(tenant_id, records_list)
    view_instance = CleanOCRStagingView()
    eligible = []
    for r in records_list:
        if not (r.is_primary or r.group_id is None):
            continue
        ui_row = view_instance._map_record_to_ui_row(r, vendor_map=vendor_map)
        effective_vendor_id = ui_row.get('vendor_id')
        ui_validation_status = ui_row.get('validationStatus')
        has_effective_match = r.vendor_status in {'EXISTS', 'FOUND', 'MATCHED', 'RESOLVED'} or effective_vendor_id
        vendor_status_badge = 'ALREADY_EXIST' if has_effective_match else 'CREATE_VENDOR'
        if ui_validation_status in {'processing', 'PENDING', 'EXTRACTING', 'PROCESSING', 'SCANNING'}:
            voucher_status_badge = 'SCANNING'
        elif ui_validation_status == 'EXTRACTION_FAILED':
            voucher_status_badge = 'FAILED'
        elif ui_validation_status == 'VOUCHER_CREATED':
            voucher_status_badge = 'SAVED'
        elif ui_validation_status in {'DUPLICATE', 'DUPLICATE_IN_BATCH', 'DUPLICATE_INVOICE'}:
            voucher_status_badge = 'ALREADY_EXIST'
        elif effective_vendor_id or ui_validation_status in {'READY', 'FOUND', 'RESOLVED', 'SUCCESS', 'NEED_VENDOR', 'NEED_TO_SAVE'}:
            voucher_status_badge = 'NEED_TO_SAVE'
        else:
            voucher_status_badge = 'WAIT'
        if vendor_status_badge == 'ALREADY_EXIST' and voucher_status_badge == 'NEED_TO_SAVE' and (ui_row.get('item_status') == 'ALREADY EXIST'):
            eligible.append((r, ui_row))
    return eligible

def get_pending_purchase_eligible_rows(upload_session_id, tenant_id=None):
    from vendors.vendor_validation_logic import build_session_vendor_map
    qs = InvoiceTempOCR.objects.filter(upload_session_id=upload_session_id)
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    records_list = list(qs)
    vendor_map = build_session_vendor_map(tenant_id, records_list)
    view_instance = CleanOCRStagingView()
    eligible = []
    for r in records_list:
        if not (r.is_primary or r.group_id is None):
            continue
        ui_row = view_instance._map_record_to_ui_row(r, vendor_map=vendor_map)
        effective_vendor_id = ui_row.get('vendor_id')
        ui_validation_status = ui_row.get('validationStatus')
        has_effective_match = r.vendor_status in {'EXISTS', 'FOUND', 'MATCHED', 'RESOLVED'} or effective_vendor_id
        vendor_status_badge = 'ALREADY_EXIST' if has_effective_match else 'CREATE_VENDOR'
        if ui_validation_status in {'processing', 'PENDING', 'EXTRACTING', 'PROCESSING', 'SCANNING'}:
            voucher_status_badge = 'SCANNING'
        elif ui_validation_status == 'EXTRACTION_FAILED':
            voucher_status_badge = 'FAILED'
        elif ui_validation_status == 'VOUCHER_CREATED':
            voucher_status_badge = 'SAVED'
        elif ui_validation_status in {'DUPLICATE', 'DUPLICATE_IN_BATCH', 'DUPLICATE_INVOICE'}:
            voucher_status_badge = 'ALREADY_EXIST'
        elif effective_vendor_id or ui_validation_status in {'READY', 'FOUND', 'RESOLVED', 'SUCCESS', 'NEED_VENDOR', 'NEED_TO_SAVE'}:
            voucher_status_badge = 'NEED_TO_SAVE'
        else:
            voucher_status_badge = 'WAIT'
        show_in_pending = False
        if vendor_status_badge == 'ALREADY_EXIST' and voucher_status_badge == 'ALREADY_EXIST' and (ui_row.get('item_status') == 'ALREADY EXIST'):
            pass
        else:
            show_in_pending = True
        if show_in_pending:
            eligible.append((r, ui_row))
    return eligible

class CleanOCRStagingView(views.APIView):
    """
    Step 3: Fix API Response.
    Isolated from legacy 'vouchers.staging_api'.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import time
        t_start_api = time.time()
        '\n        PRODUCTION-HARDENED: \n        1. Deduplicate by hash\n        2. Backpressure check\n        3. Upload to S3\n        4. Push to SQS\n        '
        print('\n' + '=' * 50)
        print(f'STAGING API: POST REQUEST RECEIVED')
        print('=' * 50 + '\n')
        queue_backend = os.getenv('QUEUE_BACKEND', 'sqs')
        from core.storage import StorageService
        from core.sqs import QueueService

        def get_list(data, key):
            if hasattr(data, 'getlist'):
                return data.getlist(key)
            val = data.get(key, [])
            return val if isinstance(val, list) else [val] if val else []
        files = request.FILES.getlist('files')
        file_paths = get_list(request.data, 'file_paths')
        voucher_type = request.data.get('voucher_type', 'PURCHASE')
        upload_type = request.data.get('upload_type', '').strip().upper() or 'UNKNOWN'
        upload_session_id = request.data.get('upload_session_id') or request.query_params.get('upload_session_id')
        tenant_id = request.user.branch_id
        logger.info(f'[SESSION_TRACE_UPLOAD] session={upload_session_id} tenant={tenant_id} voucher_type={voucher_type} file_count={len(files)}')
        from core.sqs import QueueService
        queue = QueueService()
        queue = QueueService()
        try:
            depth = queue.get_queue_depth(queue_type='ingestion')
        except Exception:
            depth = 0
        from core.observability import observability
        observability.api_metric(event='BACKPRESSURE_CHECK', queue_depth=depth)
        if depth > 1000:
            logger.warning(f'[API_BACKPRESSURE] Queue depth {depth} exceeds threshold.')
            observability.api_metric(event='BACKPRESSURE_THROTTLED', queue_depth=depth)
            return Response({'error': 'Processing queue is full. Please wait a few minutes.', 'status': 'BACKPRESSURE_THROTTLED', 'queue_depth': depth}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        session_ids = get_list(request.data, 'session_ids')
        if session_ids:
            return _handle_session_metadata_upload(request, session_ids, tenant_id)
        if not files:
            return Response({'error': 'No files uploaded'}, status=status.HTTP_400_BAD_REQUEST)
        storage = StorageService()
        from core.sqs import queue_service as queue
        job = OCRJob.objects.create(tenant_id=tenant_id, total_files=len(files), status='PENDING')
        queued_count = 0
        duplicate_count = 0
        for i, uploaded_file in enumerate(files):
            try:
                original_display_name = file_paths[i] if i < len(file_paths) else uploaded_file.name
                logger.info(f'[UPLOAD_ACCEPTED] file={original_display_name} job={job.id}')
                file_bytes = uploaded_file.read()
                file_hash = hashlib.sha256(file_bytes).hexdigest()
                existing = InvoiceTempOCR.objects.filter(file_hash=file_hash, tenant_id=tenant_id).first()
                if existing and existing.processed:
                    duplicate_count += 1
                    logger.info(f'[DUPLICATE_FOUND] Allowing pipeline to orchestrate duplicate file={original_display_name} hash={file_hash}')
                    OCRTask.objects.create(job=job, file_name=original_display_name, file_hash=file_hash, status='COMPLETED', result_id=existing.id)
                s3_key = f"ocr/{tenant_id}/{job.id}/{file_hash}_{original_display_name.replace('/', '_')}"
                safe_content_type = uploaded_file.content_type or 'application/octet-stream'
                file_url = storage.upload_file(file_bytes, s3_key, safe_content_type)
                record, created = InvoiceTempOCR.objects.get_or_create(tenant_id=tenant_id, upload_session_id=upload_session_id, file_hash=file_hash, defaults={'file_path': file_url, 'status': 'PENDING', 'voucher_type': voucher_type, 'upload_type': upload_type})
                if not created:
                    logger.warning(f'[DUPLICATE_UPLOAD] session={upload_session_id} file={original_display_name} hash={file_hash} already exists in this session. Reusing record={record.id}.')
                task = OCRTask.objects.create(job=job, file_name=original_display_name, file_url=file_url, file_hash=file_hash, status='PENDING', result_id=record.id)
                from vouchers.message_factory import message_factory
                ingestion_payload = {'record_id': record.id, 'job_id': str(job.id), 'file_url': file_url, 'file_hash': file_hash, 'voucher_type': voucher_type, 'attempt': 1}
                if not record or not record.id or (not file_url):
                    logger.error(f'[INGESTION_ABORTED] Missing critical record data for file {uploaded_file.name}')
                    continue
                from core.middleware import get_correlation_id
                msg = message_factory.create_message(task_type='INGESTION', tenant_id=tenant_id, session_id=upload_session_id, payload={**ingestion_payload, 'upload_type': upload_type}, correlation_id=get_correlation_id())
                logger.info(f'[RECORD_CREATED] id={record.id} session={upload_session_id} file={original_display_name}')
                logger.info(f"[DISTRIBUTED_PIPELINE_ACTIVE] session_id='{upload_session_id}' status='ACTIVE'")
                logger.info(f"[REDIS_COORDINATION_ACTIVE] session_id='{upload_session_id}' coordinator='redis'")
                from copy import deepcopy
                msg_copy = deepcopy(msg)
                try:
                    queue.push(msg_copy, queue_type='ingestion')
                    logger.info(f"[QUEUE_FORWARD_SUCCESS] target_queue=ingestion msg_id={msg_copy['id']}")
                    logger.info(f"[DOWNSTREAM_ENQUEUE_SUCCESS] target_queue=ingestion msg_id={msg_copy['id']}")
                except Exception as e:
                    logger.error(f'[QUEUE_FORWARD_FAILURE] target_queue=ingestion error={e}')
                    logger.error(f'[DOWNSTREAM_ENQUEUE_FAILED] target_queue=ingestion error={e}')
                    raise
                logger.info(f"[SQS_DISPATCH_SUCCESS] session_id='{upload_session_id}' msg_id='{msg.get('id')}' queue='ingestion'")
                logger.info(f"[CLUSTER_WORKER_ACTIVE] role='ingestion' status='POLLING'")
                queued_count += 1
            except Exception as e:
                logger.error(f'Failed to process file {uploaded_file.name}: {str(e)}')
                import traceback
                logger.error(traceback.format_exc())
                job.total_files -= 1
        job.save()
        if queued_count == 0 and len(files) > 0 and (duplicate_count == 0):
            logger.error(f'[BOOTSTRAP_FAILURE] session={upload_session_id} - No files queued. Marking session as FAILED.')
            try:
                from core.redis_orchestrator import orchestrator
                orchestrator.set_terminal_status(upload_session_id, 'FAILED', 'BOOTSTRAP_CRASH')
                job.status = 'FAILED'
                job.save(update_fields=['status'])
            except Exception as re:
                logger.error(f'[BOOTSTRAP_TERMINALIZATION_FAIL] {re}')
            return Response({'error': 'Internal server error during upload bootstrap.', 'status': 'FAILED'}, status=500)
        estimated_delay = depth * 2 / max(int(os.getenv('AI_GLOBAL_CONCURRENCY', '20')), 1)
        api_duration_ms = int((time.time() - t_start_api) * 1000) if 't_start_api' in locals() else 0
        from ocr_pipeline.pipeline_telemetry import PipelineStageTelemetry
        PipelineStageTelemetry.record_stage('API', {'files_received': len(files)}, {'success': True, 'queued_count': queued_count, 'duplicate_count': duplicate_count}, api_duration_ms)
        return Response({'success': True, 'job_id': str(job.id), 'status': 'PROCESSING', 'message': f'Queued {queued_count} files. {duplicate_count} skipped (deduplicated).', 'total_files': job.total_files, 'estimated_delay_seconds': round(estimated_delay, 1)}, status=status.HTTP_202_ACCEPTED)

    def _map_record_to_ui_row(self, record, norm_data=None, vendor_map=None):
        """
        CENTRALIZED HYDRATION GATE.
        PURELY READ-ONLY. NEVER validates, NEVER vendor matches, NEVER inventory matches.
        """
        r = record
        norm = norm_data or getattr(r, 'extracted_data', None) or {}
        v_status = getattr(r, 'validation_status', 'PENDING')
        v_id = getattr(r, 'vendor_id', None)
        v_status_record = getattr(r, 'status', 'PROCESSING')
        tenant_id = getattr(r, 'tenant_id', None)
        if norm and (not norm.get('canonical_vendor_gstin')):
            raw_text = norm.get('_pdf_ocr_text') or norm.get('_raw_text') or ''
            if raw_text:
                try:
                    from ocr_pipeline.gstin_classifier import GSTINOwnershipClassifier
                    extracted_data_dict = {'gstin': getattr(r, 'gstin', None) or norm.get('gstin') or '', 'vendor_gstin': norm.get('vendor_gstin') or norm.get('gstin') or '', 'buyer_gstin': norm.get('buyer_gstin') or norm.get('bill_to_gstin') or '', 'consignee_gstin': norm.get('consignee_gstin') or norm.get('ship_to_gstin') or '', 'vendor_name': getattr(r, 'vendor_name', None) or norm.get('vendor_name') or ''}
                    classification = GSTINOwnershipClassifier.classify_gstins(raw_text, extracted_data_dict, str(tenant_id or ''))
                    norm = dict(norm)
                    norm.update(classification)
                except Exception as _fe:
                    logger.warning(f"[GSTIN_ON_THE_FLY_FALLBACK_FAILED] record_id={getattr(r, 'id', None)} error={_fe}")
        db_vendor_status = getattr(r, 'vendor_status', 'PENDING')
        if not v_id and vendor_map:
            try:
                from vendors.vendor_validation_logic import normalize_branch as _nb
                gstin_key = (norm.get('canonical_vendor_gstin') or norm.get('vendor_gstin') or getattr(r, 'gstin', None) or norm.get('gstin') or '').strip().upper()
                branch_raw = getattr(r, 'branch', None) or norm.get('branch') or ''
                branch_key = _nb(branch_raw or 'Main Branch')
                if gstin_key:
                    vendor_map_result = vendor_map.get((gstin_key, branch_key))
                    if vendor_map_result and vendor_map_result.get('status') == 'EXISTING_VENDOR':
                        v_id = vendor_map_result.get('vendor_id')
                        logger.info(f"[VENDOR_VALIDATION_RESULT] gstin={gstin_key} matched_vendor_id={v_id} assigned_status=EXISTING_VENDOR record_id={getattr(r, 'id', None)}")
            except Exception as _vme:
                logger.warning(f"[HYDRATION_VENDOR_MAP_LOOKUP_FAILED] record_id={getattr(r, 'id', None)} error={_vme}")
        logger.info(f"[HYDRATION_READONLY] Entering read-only hydration for record_id={getattr(r, 'id', None)} tenant_id={tenant_id} vendor_id={v_id} validation_status={v_status} db_vendor_status={db_vendor_status}")
        logger.info(f"[HYDRATION_REVALIDATION_BLOCKED] Bypassed validation run for record_id={getattr(r, 'id', None)}")
        sections = norm.get('sections', {})
        supplier = sections.get('supplier_details', {})
        header = norm.get('header', {})
        from .normalize import fix_encoding_corruption
        vendor_name_val = fix_encoding_corruption(header.get('vendor_name') or supplier.get('vendor_name') or norm.get('vendor_name') or '')
        is_finalized = v_status_record in {'FINALIZED', 'VOUCHER_CREATED', 'COMPLETED', 'EXTRACTED'} or getattr(r, 'processed', False)
        is_failed = v_status_record in {'FAILED', 'ERROR'}
        if is_finalized:
            logger.info(f"[IMMUTABLE_FINALIZED_DTO] Read-only snapshot mapped for finalized record_id={getattr(r, 'id', None)}")
        if not is_finalized and (not is_failed):
            has_extracted_data = False
            if norm:
                useful_keys = [k for k in norm if k not in ['_page_role', 'page_role', 'file_hash', 'file_path', 'session_id', 'tenant_id']]
                if useful_keys:
                    has_extracted_data = True
            if not has_extracted_data:
                return {'processing': True, 'id': getattr(r, 'id', None), 'file_path': getattr(r, 'file_path', '') or '', 'file_hash': getattr(r, 'file_hash', '') or '', 'invoice': {}, 'items': [], 'status': 'PROCESSING', 'validationStatus': 'PROCESSING'}
        ui_status = v_status or 'PENDING'
        if v_status in {'DUPLICATE', 'DUPLICATE_IN_BATCH', 'DUPLICATE_INVOICE'}:
            ui_status = 'DUPLICATE'
        elif is_failed:
            ui_status = 'EXTRACTION_FAILED'
        elif is_finalized:
            if v_status == 'VOUCHER_CREATED' or v_status_record == 'VOUCHER_CREATED':
                ui_status = 'VOUCHER_CREATED'
            elif v_status == 'NEED_TO_SAVE':
                ui_status = 'NEED_TO_SAVE'
            elif (v_status in {'READY', 'FOUND', 'RESOLVED', 'SUCCESS'} or v_id) and v_status != 'PENDING_PURCHASE':
                ui_status = 'NEED_TO_SAVE'
            elif v_status in {'GSTIN_CONFLICT', 'PENDING_PURCHASE'}:
                ui_status = v_status
            else:
                ui_status = 'NEED_VENDOR'
        final_status = 'PROCESSING'
        if is_finalized:
            final_status = 'FINALIZED'
        elif is_failed:
            final_status = 'FAILED'
        branch = fix_encoding_corruption(str(getattr(r, 'branch', None) or header.get('branch') or supplier.get('branch') or norm.get('branch') or '—'))
        bill_from = fix_encoding_corruption(norm.get('bill_from', ''))
        bill_to = fix_encoding_corruption(norm.get('header', {}).get('billing_address', '') or norm.get('header', {}).get('bill_to', '') or norm.get('bill_to', '') or norm.get('billing_address', ''))
        if not bill_to:
            _ocr_text = norm.get('_pdf_ocr_text') or norm.get('_raw_text') or ''
            if _ocr_text:
                try:
                    import re as _re
                    _start = '(?:Buyer\\s*\\(Bill\\s*to\\)|Details\\s*of\\s*Receiver\\s*\\(Billed\\s*to\\)|Details\\s*of\\s*Receiver|Billed\\s*to|Dtails\\s*oi\\s*Rocolvor\\s*Dlcd\\s*to|Dlcd\\s*to|Bill\\s*to)'
                    _stop = '(?:Place\\s*of\\s*Supply|Puce\\s*ol\\s*Supply|Dated|Delivery\\s*Note|Invoice\\s*No|Voucher\\s*No|Total|Description|Sl\\s*No|E-Way|E\\s*WAY)'
                    _m = _re.search(f'{_start}(.*?){_stop}', _ocr_text, _re.DOTALL | _re.IGNORECASE)
                    if not _m:
                        _m = _re.search(f'{_start}(.{{1,500}}?)', _ocr_text, _re.DOTALL | _re.IGNORECASE)
                    if _m:
                        from .normalize import _clean_bill_to_ocr_extract
                        _raw_to = _clean_bill_to_ocr_extract(_m.group(1).strip())
                        bill_to = fix_encoding_corruption(_raw_to)
                        logger.info(f"[BILL_TO_UI_FALLBACK_HIT] record_id={getattr(r, 'id', None)} value={repr(bill_to[:80])}")
                except Exception as _bte:
                    logger.warning(f"[BILL_TO_UI_FALLBACK_FAILED] record_id={getattr(r, 'id', None)} err={_bte}")
        if bill_to and '|' in bill_to:
            try:
                from .normalize import _clean_bill_to_ocr_extract
                _cleaned = fix_encoding_corruption(_clean_bill_to_ocr_extract(bill_to))
                if _cleaned:
                    logger.info(f"[BILL_TO_PIPE_CLEANUP] record_id={getattr(r, 'id', None)} before={repr(bill_to[:60])} after={repr(_cleaned[:60])}")
                    bill_to = _cleaned
            except Exception as _bte:
                logger.warning(f"[BILL_TO_PIPE_CLEANUP_FAILED] record_id={getattr(r, 'id', None)} err={_bte}")
        inv_no = getattr(r, 'supplier_invoice_no', None) or header.get('invoice_no') or norm.get('invoice_no') or norm.get('invoice_number') or norm.get('supplier_invoice_no') or supplier.get('supplier_invoice_no') or ''
        item_status_raw = norm.get('item_status')
        if not item_status_raw:
            _ae = norm.get('assembled_exports') or []
            if _ae and isinstance(_ae, list) and _ae[0]:
                item_status_raw = _ae[0].get('item_status')
        item_status = item_status_raw or None
        missing_items = norm.get('missing_items') or []
        items_val = norm.get('items') or []
        if not items_val:
            _ae = norm.get('assembled_exports') or []
            if _ae and isinstance(_ae, list) and _ae[0]:
                items_val = _ae[0].get('items') or []

        # Dynamic check against master inventory items
        if items_val:
            try:
                from ocr_pipeline.inventory_validation import InventoryItemValidationService
                _tenant = tenant_id or getattr(r, 'tenant_id', None)
                if _tenant:
                    _val_res = InventoryItemValidationService.validate_inventory_items(_tenant, items_val)
                    if _val_res and _val_res.get('item_status'):
                        item_status = _val_res.get('item_status')
                        items_val = _val_res.get('items', items_val)
                        missing_items = _val_res.get('missing_items', missing_items)
            except Exception as _ite:
                logger.warning(f'[ITEM_DYNAMIC_VALIDATION_FAILED] error={_ite}')

        if not item_status and items_val:
            child_statuses = [itm.get('item_status') or itm.get('validation_status') for itm in items_val if isinstance(itm, dict)]
            child_statuses = [s for s in child_statuses if s]
            if child_statuses:
                has_create = any((s in ('CREATE ITEM', 'CREATE_ITEM') for s in child_statuses))
                if has_create:
                    item_status = 'CREATE ITEM'
                else:
                    item_status = 'ALREADY EXIST'
                logger.info(f'[ITEM_AGGREGATE_DERIVED] record_id={getattr(r, "id", None)} child_count={len(child_statuses)} child_statuses={child_statuses} derived_aggregate={item_status}')
        if ui_status == 'DUPLICATE':
            item_status = 'ALREADY EXIST'
        logger.critical('[FORENSIC_ITEMS_STRUCTURE]\n%s', json.dumps(items_val, indent=2, default=str))
        logger.critical('[FORENSIC_ITEMS_LIFECYCLE] [AFTER_HYDRATION] record_id=%s invoice_no=%s item_count=%d item_status=%s payload_keys=%s', getattr(r, 'id', None), inv_no, len(items_val), item_status, list(norm.keys()))
        try:
            from ocr_pipeline.pipeline import trace_item_checkpoint
            snapshot_count_temp = len(norm.get('items', []))
            if not norm.get('items'):
                _ae_temp = norm.get('assembled_exports') or []
                if _ae_temp and isinstance(_ae_temp, list) and _ae_temp[0]:
                    snapshot_count_temp = len(_ae_temp[0].get('items', []))
            trace_item_checkpoint(record_id=str(getattr(r, 'id', None)), invoice_no=inv_no, page_number=norm.get('_page_no') or norm.get('page_no') or getattr(r, 'page_no', None), stage='ITEM_TRACE_AFTER_HYDRATION', item_count=len(items_val), item_status=item_status, snapshot_item_count=snapshot_count_temp)
        except Exception as trace_err:
            logger.error(f'[TRACE_ERR] ITEM_TRACE_AFTER_HYDRATION: {trace_err}')
        snapshot_count = len(norm.get('items', []))
        if not norm.get('items'):
            _ae = norm.get('assembled_exports') or []
            if _ae and isinstance(_ae, list) and _ae[0]:
                snapshot_count = len(_ae[0].get('items', []))
        logger.critical('[HYDRATION_ITEM_VERIFY] record_id=%s snapshot_item_count=%d hydrated_item_count=%d item_status=%s', getattr(r, 'id', None), snapshot_count, len(items_val), item_status)
        if snapshot_count != len(items_val):
            logger.critical('[CRITICAL_HYDRATION_MISMATCH] record_id=%s snapshot_item_count=%d hydrated_item_count=%d', getattr(r, 'id', None), snapshot_count, len(items_val))
            from ocr_pipeline.pipeline import CriticalPipelineError
            raise CriticalPipelineError('Hydration lost canonical items')
        if snapshot_count > 0 and len(items_val) == 0:
            from ocr_pipeline.pipeline import CriticalPipelineError
            raise CriticalPipelineError('Hydration lost canonical items')
        snapshot_items = None
        _ae = norm.get('assembled_exports') or []
        if _ae and isinstance(_ae, list) and _ae[0]:
            snapshot_items = _ae[0].get('items') or []
        if not snapshot_items:
            snapshot_items = norm.get('items') or []
        if snapshot_items:
            snapshot_items_map = {itm.get('line_index'): itm for itm in snapshot_items if isinstance(itm, dict) and itm.get('line_index') is not None}
            for itm in items_val:
                l_idx = itm.get('line_index')
                if l_idx in snapshot_items_map:
                    snap_itm = snapshot_items_map[l_idx]
                    if itm.get('inventory_match_strategy') != snap_itm.get('inventory_match_strategy'):
                        logger.critical(f"[STRATEGY_CHANGED_AFTER_FREEZE] line={l_idx} before={snap_itm.get('inventory_match_strategy')} after={itm.get('inventory_match_strategy')}")
                        from ocr_pipeline.pipeline import CriticalPipelineError
                        raise CriticalPipelineError('match strategy changes after freeze')
                    if itm.get('inventory_item_id') != snap_itm.get('inventory_item_id'):
                        logger.critical(f"[HYDRATED_ITEM_MISMATCH] line={l_idx} key=inventory_item_id before={snap_itm.get('inventory_item_id')} after={itm.get('inventory_item_id')}")
                        from ocr_pipeline.pipeline import CriticalPipelineError
                        raise CriticalPipelineError('hydrated item differs from snapshot frozen item')
        logger.info(f"[DTO_VALIDATION_STATE] record_id={getattr(r, 'id', None)} vendor_id={v_id} vendor_status={('EXISTS' if v_id or db_vendor_status in {'EXISTS', 'FOUND', 'MATCHED', 'RESOLVED'} else 'NEW')} validation_status={v_status} item_status={item_status}")
        buyer_name = norm.get('buyer_name') or norm.get('customer_name') or norm.get('header', {}).get('buyer_name') or norm.get('header', {}).get('customer_name') or ''
        from ocr_pipeline.normalize import extract_buyer_name_from_ocr_text, extract_buyer_name_from_bill_to, is_address_token
        if not buyer_name or is_address_token(buyer_name):
            raw_ocr = str(norm.get('_raw_text') or norm.get('_pdf_ocr_text') or getattr(r, '_raw_text', '') or '')
            rec_name = extract_buyer_name_from_ocr_text(raw_ocr)
            if not rec_name and bill_to:
                rec_name = extract_buyer_name_from_bill_to(str(bill_to))
            if rec_name and not is_address_token(rec_name):
                buyer_name = rec_name
                logger.info(f"[BUYER_NAME_UI_RESOLVED] record_id={getattr(r, 'id', None)} value='{buyer_name}'")

        buyer_gstin_val = norm.get('canonical_buyer_gstin') or norm.get('buyer_gstin') or norm.get('bill_to_gstin') or ''

        # Perform dedicated customer validation against tenant
        from ocr_pipeline.customer_validation import validate_customer_against_tenant
        cust_val = validate_customer_against_tenant(
            tenant_or_id=tenant_id or getattr(r, 'tenant_id', None),
            buyer_name=buyer_name,
            buyer_gstin=buyer_gstin_val,
            record_id=getattr(r, 'id', None),
            invoice_no=inv_no,
            bill_to=bill_to
        )

        res = {'id': getattr(r, 'id', None), 'file_hash': getattr(r, 'file_hash', None) or norm.get('file_hash', None), 'buyer_name': cust_val['buyer_name'] or buyer_name, 'customer_name': cust_val['customer_name'] or buyer_name, 'raw_buyer_name': norm.get('raw_buyer_name') or buyer_name, 'canonical_buyer_name': cust_val['canonical_buyer_name'] or buyer_name, 'file_path': getattr(r, 'file_path', None) or norm.get('file_path', None), 'tenant_id': getattr(r, 'tenant_id', None), 'invoice_no': inv_no, 'page_no': norm.get('_page_no') or norm.get('page_no') or getattr(r, 'page_no', None), 'invoice_status': norm.get('invoice_status') or ('MISSING' if not inv_no else 'FOUND'), 'invoice_date': norm.get('invoice_date') or header.get('invoice_date') or supplier.get('invoice_date') or '—', 'total_amount': norm.get('total_invoice_value') or norm.get('invoice_total') or header.get('total_amount') or header.get('invoice_total') or norm.get('total_amount') or '0.00', 'totals': norm.get('total_invoice_value') or norm.get('invoice_total') or header.get('total_amount') or header.get('invoice_total') or norm.get('total_amount') or '0.00', 'branch': branch, 'vendor_name': vendor_name_val, 'vendor_gstin': norm.get('canonical_vendor_gstin') or norm.get('vendor_gstin') or getattr(r, 'gstin', None) or header.get('vendor_gstin') or norm.get('gstin') or supplier.get('gstin') or '—', 'gstin': norm.get('canonical_vendor_gstin') or norm.get('vendor_gstin') or getattr(r, 'gstin', None) or header.get('gstin') or norm.get('gstin') or supplier.get('gstin') or '—', 'buyer_gstin': cust_val['buyer_gstin'] or buyer_gstin_val or '—', 'customer_gstin': cust_val['customer_gstin'] or buyer_gstin_val or '—', 'consignee_gstin': norm.get('consignee_gstin') or norm.get('ship_to_gstin') or '—', 'ship_to_gstin': norm.get('ship_to_gstin') or norm.get('consignee_gstin') or '—', 'bill_to_gstin': norm.get('bill_to_gstin') or buyer_gstin_val or '—', 'raw_vendor_gstin': norm.get('raw_vendor_gstin') or getattr(r, 'gstin', None) or norm.get('gstin') or '—', 'raw_buyer_gstin': norm.get('raw_buyer_gstin') or '—', 'raw_consignee_gstin': norm.get('raw_consignee_gstin') or '—', 'raw_bill_to_gstin': norm.get('raw_bill_to_gstin') or '—', 'raw_ship_to_gstin': norm.get('raw_ship_to_gstin') or '—', 'canonical_vendor_gstin': norm.get('canonical_vendor_gstin') or getattr(r, 'gstin', None) or norm.get('gstin') or '—', 'canonical_buyer_gstin': cust_val['canonical_buyer_gstin'] or buyer_gstin_val or '—', 'customer_status': cust_val['customer_status'], 'company_match_detected': cust_val['company_match_detected'], 'company_match_decision': cust_val['company_match_decision'], 'vendor_id': v_id, 'status': final_status, 'validationStatus': ui_status, 'validation_status': ui_status, 'vendor_status': 'EXISTS' if v_id or db_vendor_status in ('EXISTS', 'FOUND', 'MATCHED', 'RESOLVED') else 'NEW', 'item_status': item_status, 'missing_items': missing_items, 'processed': getattr(r, 'processed', False), 'bill_from': bill_from, 'bill_to': bill_to, 'items': items_val, 'line_items': items_val, 'irn': getattr(r, 'irn', None) or norm.get('irn'), 'ack_no': getattr(r, 'ack_no', None) or norm.get('ack_no'), 'ack_date': getattr(r, 'ack_date', None) or norm.get('ack_date'), 'hsn_sac': norm.get('hsn_sac', ''), 'place_of_supply': norm.get('place_of_supply') or supplier.get('place_of_supply') or '—', 'total_taxable_value': norm.get('total_taxable_value') or supplier.get('total_taxable_value') or norm.get('taxable_value') or '0.00', 'total_igst': norm.get('total_igst') or supplier.get('total_igst') or norm.get('igst') or '0.00', 'total_cgst': norm.get('total_cgst') or supplier.get('total_cgst') or norm.get('cgst') or '0.00', 'total_sgst': norm.get('total_sgst') or supplier.get('total_sgst') or norm.get('sgst') or '0.00', 'total_cess': norm.get('total_cess') or supplier.get('total_cess') or norm.get('cess') or '0.00', 'round_off': norm.get('round_off') or supplier.get('round_off') or '0.00', 'total_invoice_value': norm.get('total_invoice_value') or norm.get('invoice_total') or supplier.get('total_invoice_value') or '0.00'}
        is_degraded = (not inv_no or str(inv_no).upper() == 'MISSING') and (not items_val)
        if getattr(r, 'status', None) == 'partial_extraction' or norm.get('status') == 'partial_extraction':
            is_degraded = True
        if is_degraded:
            res['invoice_no'] = 'N/A'
            res['vendor_name'] = 'OCR FAILED'
            res['validationStatus'] = 'Needs Review'
            res['validation_status'] = 'Needs Review'
            res['status'] = final_status
            res['vendor_status'] = 'EXISTS' if v_id or db_vendor_status in ('EXISTS', 'FOUND', 'MATCHED', 'RESOLVED') else 'NEW'
            ui_status = 'Needs Review'
        ext_dict = getattr(r, 'extracted_data', {}) if isinstance(getattr(r, 'extracted_data', None), dict) else {}
        user_saved_decision = ext_dict.get('company_match_decision')

        if user_saved_decision in ('PROCEED', 'NOT_PROCEED'):
            final_company_decision = user_saved_decision
            final_company_detected = (user_saved_decision != 'PROCEED')
            final_customer_status = 'SELF_COMPANY' if user_saved_decision == 'PROCEED' else cust_val['customer_status']
        else:
            final_company_decision = cust_val['company_match_decision']
            final_company_detected = cust_val['company_match_detected']
            final_customer_status = cust_val['customer_status']

        res['company_match_detected'] = final_company_detected
        res['company_match_decision'] = final_company_decision
        res['customer_status'] = final_customer_status
        res['extracted_data'] = {'sections': sections, 'bill_from': bill_from, 'billing_address': bill_to, 'items': items_val, 'line_items': items_val, 'item_status': item_status, 'missing_items': missing_items, **norm, **ext_dict}
        res['extracted_data']['company_match_decision'] = final_company_decision
        res['extracted_data']['company_match_detected'] = final_company_detected
        res['created_at'] = getattr(r, 'created_at', None)
        res['voucher_type'] = getattr(r, 'voucher_type', 'PURCHASE')
        is_vendor_exists = res['vendor_status'] == 'EXISTS'
        is_voucher_exists = res['validationStatus'] in {'DUPLICATE', 'VOUCHER_CREATED', 'DUPLICATE_IN_BATCH', 'DUPLICATE_INVOICE', 'PENDING_PURCHASE'}
        res['is_resume_pending'] = not (is_vendor_exists and is_voucher_exists)
        if is_voucher_exists:
            res['is_saved'] = True
            res['processing_state'] = 'COMPLETED'
        else:
            res['is_saved'] = False
            res['processing_state'] = res['status']
        if not is_vendor_exists and (not is_voucher_exists):
            res['resume_reason'] = 'Vendor + Voucher Pending'
        elif is_vendor_exists and (not is_voucher_exists):
            res['resume_reason'] = 'Voucher Pending'
        elif not is_vendor_exists and is_voucher_exists:
            res['resume_reason'] = 'Vendor Pending'
        else:
            res['resume_reason'] = None
        logger.info(f"[API_RESPONSE_STATE] record_id={getattr(r, 'id', None)} vendor_status={res['vendor_status']} voucher_status={res['validationStatus']} item_status={res['item_status']} vendor_id={v_id} gstin={res.get('gstin')}")
        logger.info(f"[READONLY_HYDRATION_CONFIRMED] Completed readonly hydration for record_id={getattr(r, 'id', None)} validation_status={ui_status}")
        logger.info(f"[GSTIN_HYDRATION] upload_session_id={getattr(r, 'upload_session_id', None)} record_id={getattr(r, 'id', None)} gstin={res.get('gstin')} status={res.get('status')}")
        logger.info(f"[GSTIN_API_RESPONSE] upload_session_id={getattr(r, 'upload_session_id', None)} record_id={getattr(r, 'id', None)} gstin={res.get('gstin')} status={res.get('status')}")
        return res

    def _log_final_api_response_rows(self, data, source):
        if not isinstance(data, list):
            return
        for row in data:
            if isinstance(row, dict):
                logger.info(f"[FORENSIC_API_ROW] source={source} invoice_no={row.get('invoice_no')} vendor_id={row.get('vendor_id')} vendor_status={row.get('vendor_status')} validation_status={row.get('validation_status')} gstin={row.get('gstin')} branch={row.get('branch')}")

    def get(self, request, file_hash=None):
        t_poll_start = time.time()
        session_id = request.query_params.get('upload_session_id')
        tenant_id = getattr(request.user, 'branch_id', None) or getattr(request.user, 'tenant_id', None) or '88fe4389-58a9-4244-9878-8a4e646898bd'
        resume = request.query_params.get('resume') == 'true'
        if not resume and (not file_hash) and (session_id in {'None', 'null', 'undefined', '', None}):
            logger.warning(f"[ORPHAN_POLL_BLOCKED] Rejected staging poll with session_id='{session_id}'")
            return Response({'status': 'EMPTY_SESSION_TERMINAL', 'data': [], 'progress_percent': 100, 'hydration_pending': False})
        prim_rec = None
        if session_id:
            prim_rec = InvoiceTempOCR.objects.filter(upload_session_id=session_id).order_by('id').first()
        elif file_hash:
            if str(file_hash).isdigit():
                prim_rec = InvoiceTempOCR.objects.filter(id=int(file_hash)).first()
            else:
                prim_rec = InvoiceTempOCR.objects.filter(Q(file_hash=file_hash) | Q(upload_session_id=file_hash)).first()
        if not prim_rec:
            return Response({'status': 'PROCESSING', 'data': [], 'pipeline_status': 'processing', 'terminal': False, 'hydration_pending': True, 'completed': False, 'failed': False, 'progress_percent': 0.0, 'poll_latency': round(time.time() - t_poll_start, 3)})
        if not session_id and file_hash:
            logger.info(f'[SINGLE_RECORD_FETCH] record_id={prim_rec.id} file_hash={prim_rec.file_hash}')
            from vendors.vendor_validation_logic import build_session_vendor_map
            rec_tenant_id = prim_rec.tenant_id or tenant_id
            _vendor_map = {}
            try:
                _vendor_map = build_session_vendor_map(rec_tenant_id, [prim_rec])
            except Exception as _vme:
                logger.warning(f'[SINGLE_RECORD_VENDOR_MAP_FAILED] error={_vme}')
            mapped = self._map_record_to_ui_row(prim_rec, norm_data=prim_rec.extracted_data, vendor_map=_vendor_map)
            return Response({'status': 'FINALIZED', 'data': [mapped], 'pipeline_status': 'completed', 'terminal': True, 'hydration_pending': False, 'completed': True, 'failed': False, 'progress_percent': 100.0, 'poll_latency': round(time.time() - t_poll_start, 3)})
        from ocr_pipeline.models import SessionFinalizationState, FinalizedSnapshot
        barrier_state = SessionFinalizationState.objects.filter(id=str(prim_rec.id)).first()
        if not barrier_state:
            return Response({'status': 'PROCESSING', 'data': [], 'pipeline_status': 'processing', 'terminal': False, 'hydration_pending': True, 'completed': False, 'failed': False, 'progress_percent': 0.0, 'poll_latency': round(time.time() - t_poll_start, 3)})
        expected = barrier_state.expected_pages or 1
        completed = (barrier_state.completed_pages or 0) + (barrier_state.failed_pages or 0)
        progress_percent = min(99.0, completed / expected * 100.0)
        if barrier_state.status == 'FAILED' or (barrier_state.status == 'FINALIZED' and barrier_state.failed_pages > 0 and (not barrier_state.terminal_consistency)):
            logger.info(f'[LIFECYCLE_TERMINAL_STATE] session={session_id} tenant_id={tenant_id} state=failed — attempting recovery hydration')
            snapshots = FinalizedSnapshot.objects.filter(session_id=session_id).order_by('created_at', 'id')
            if not snapshots.exists():
                snapshots = FinalizedSnapshot.objects.filter(session_id=prim_rec.upload_session_id).order_by('created_at', 'id')
            mapped_data = []
            _snap_vendor_map = {}
            try:
                all_db_records = list(InvoiceTempOCR.objects.filter(upload_session_id=session_id))
                if not all_db_records:
                    all_db_records = list(InvoiceTempOCR.objects.filter(upload_session_id=prim_rec.upload_session_id))
                if all_db_records:
                    from vendors.vendor_validation_logic import build_session_vendor_map
                    _snap_vendor_map = build_session_vendor_map(tenant_id, all_db_records)
            except Exception as _vme:
                logger.warning(f'[SNAPSHOT_VENDOR_MAP_FAILED] session={session_id} error={_vme}')
            if snapshots.exists():
                for snapshot in snapshots:
                    snapshot_data = self._get_snapshot_data(snapshot)
                    raw_rows = snapshot_data.get('data', [])
                    for row in raw_rows:
                        inv_no = row.get('invoice_no')
                        db_record = None
                        if row.get('file_hash'):
                            db_record = InvoiceTempOCR.objects.filter(upload_session_id=session_id, file_hash=row.get('file_hash')).first()
                        if not db_record and inv_no:
                            db_record = InvoiceTempOCR.objects.filter(upload_session_id=session_id, supplier_invoice_no__iexact=inv_no).first()
                        if not db_record and row.get('id'):
                            db_record = InvoiceTempOCR.objects.filter(id=row.get('id')).first()
                        if db_record:
                            norm_source = db_record.extracted_data or row
                            dummy = db_record
                        else:
                            norm_source = row
                            from types import SimpleNamespace
                            dummy = SimpleNamespace(**{'id': row.get('id'), 'tenant_id': tenant_id, 'status': 'FAILED', 'processed': False, 'validation_status': 'EXTRACTION_FAILED', 'vendor_id': row.get('vendor_id'), 'vendor_status': 'PENDING', 'supplier_invoice_no': inv_no, 'gstin': row.get('gstin'), 'irn': row.get('irn'), 'ack_no': row.get('ack_no'), 'ack_date': row.get('ack_date'), 'created_at': row.get('created_at'), 'voucher_type': row.get('voucher_type'), 'branch': row.get('branch')})
                        mapped = self._map_record_to_ui_row(dummy, norm_data=norm_source, vendor_map=_snap_vendor_map)
                        mapped_data.append(mapped)
            else:
                all_db_records = list(InvoiceTempOCR.objects.filter(upload_session_id=session_id))
                if not all_db_records:
                    all_db_records = list(InvoiceTempOCR.objects.filter(upload_session_id=prim_rec.upload_session_id))
                for db_record in all_db_records:
                    mapped = self._map_record_to_ui_row(db_record, norm_data=db_record.extracted_data, vendor_map=_snap_vendor_map)
                    mapped_data.append(mapped)
            return Response({'status': 'FAILED', 'data': mapped_data, 'pipeline_status': 'failed', 'terminal': True, 'hydration_pending': False, 'completed': True, 'failed': True, 'progress_percent': 100.0, 'poll_latency': round(time.time() - t_poll_start, 3)})
        if barrier_state.terminal_consistency:
            snapshots = FinalizedSnapshot.objects.filter(session_id=session_id).order_by('created_at', 'id')
            if not snapshots.exists():
                snapshots = FinalizedSnapshot.objects.filter(session_id=prim_rec.upload_session_id).order_by('created_at', 'id')
            mapped_data = []
            _snap_vendor_map = {}
            try:
                all_db_records = list(InvoiceTempOCR.objects.filter(upload_session_id=session_id))
                if not all_db_records:
                    all_db_records = list(InvoiceTempOCR.objects.filter(upload_session_id=prim_rec.upload_session_id))
                if all_db_records:
                    from vendors.vendor_validation_logic import build_session_vendor_map
                    _snap_vendor_map = build_session_vendor_map(tenant_id, all_db_records)
                    logger.info(f'[SNAPSHOT_HYDRATION_STATE] session={session_id} vendor_map_pairs={len(_snap_vendor_map)} db_records={len(all_db_records)}')
            except Exception as _vme:
                logger.warning(f'[SNAPSHOT_VENDOR_MAP_FAILED] session={session_id} error={_vme}')
            for snapshot in snapshots:
                snapshot_data = self._get_snapshot_data(snapshot)
                raw_rows = snapshot_data.get('data', [])
                for row in raw_rows:
                    inv_no = row.get('invoice_no')
                    gstin_val = row.get('gstin')
                    db_record = None
                    if row.get('file_hash'):
                        db_record = InvoiceTempOCR.objects.filter(upload_session_id=session_id, file_hash=row.get('file_hash')).first()
                    if not db_record and inv_no:
                        db_record = InvoiceTempOCR.objects.filter(upload_session_id=session_id, supplier_invoice_no__iexact=inv_no).first()
                    if not db_record and row.get('id'):
                        db_record = InvoiceTempOCR.objects.filter(id=row.get('id')).first()
                    if not db_record and inv_no:
                        for candidate in InvoiceTempOCR.objects.filter(upload_session_id=session_id):
                            ed = candidate.extracted_data or {}
                            if str(ed.get('invoice_no', '')).strip().lower() == str(inv_no).strip().lower():
                                db_record = candidate
                                break
                    if db_record:
                        if not getattr(db_record, 'tenant_id', None) and tenant_id:
                            db_record.tenant_id = tenant_id
                        if not getattr(db_record, 'vendor_id', None) and _snap_vendor_map:
                            try:
                                from vendors.vendor_validation_logic import normalize_branch as _nb
                                db_norm = getattr(db_record, 'extracted_data', {}) or {}
                                gstin_key = (db_norm.get('canonical_vendor_gstin') or db_norm.get('vendor_gstin') or getattr(db_record, 'gstin', None) or '').strip().upper()
                                branch_key = _nb(getattr(db_record, 'branch', None) or 'Main Branch')
                                vmap_result = _snap_vendor_map.get((gstin_key, branch_key))
                                if vmap_result and vmap_result.get('status') == 'EXISTING_VENDOR':
                                    db_record.vendor_id = vmap_result.get('vendor_id')
                                    if getattr(db_record, 'vendor_status', 'PENDING') == 'PENDING':
                                        db_record.vendor_status = 'EXISTS'
                                    logger.info(f'[VENDOR_VALIDATION_RESULT] gstin={gstin_key} matched_vendor_id={db_record.vendor_id} assigned_status=EXISTING_VENDOR record_id={db_record.id} source=snapshot_hydration')
                            except Exception as _ve:
                                logger.warning(f'[HYDRATION_ENRICH_FAILED] record_id={db_record.id} error={_ve}')
                        norm_source = db_record.extracted_data or row
                        dummy = db_record
                        logger.info(f"[SNAPSHOT_HYDRATION_STATE] record_id={db_record.id} vendor_status={getattr(db_record, 'vendor_status', 'PENDING')} vendor_id={getattr(db_record, 'vendor_id', None)} validation_status={getattr(db_record, 'validation_status', 'PENDING')} item_status={(db_record.extracted_data or {}).get('item_status', 'NOT_SET')}")
                    else:
                        resolved_vendor_id = row.get('vendor_id')
                        resolved_vendor_status = 'PENDING'
                        if not resolved_vendor_id and _snap_vendor_map and gstin_val:
                            try:
                                from vendors.vendor_validation_logic import normalize_branch as _nb
                                gstin_key = gstin_val.strip().upper()
                                branch_key = _nb(row.get('branch') or 'Main Branch')
                                vmap_result = _snap_vendor_map.get((gstin_key, branch_key))
                                if vmap_result and vmap_result.get('status') == 'EXISTING_VENDOR':
                                    resolved_vendor_id = vmap_result.get('vendor_id')
                                    resolved_vendor_status = 'EXISTS'
                                    logger.info(f'[VENDOR_VALIDATION_RESULT] gstin={gstin_key} matched_vendor_id={resolved_vendor_id} assigned_status=EXISTING_VENDOR source=snapshot_row_fallback')
                            except Exception as _ve2:
                                logger.warning(f'[HYDRATION_SNAP_VENDOR_FAILED] inv_no={inv_no} error={_ve2}')
                        norm_source = row
                        from types import SimpleNamespace
                        _snap_val_status = row.get('validation_status')
                        if not _snap_val_status:
                            _snap_val_status = 'NEED_TO_SAVE' if resolved_vendor_id else 'NEED_VENDOR'
                        dummy = SimpleNamespace(**{'id': row.get('id'), 'tenant_id': tenant_id, 'status': 'FINALIZED', 'processed': True, 'validation_status': _snap_val_status, 'vendor_id': resolved_vendor_id, 'vendor_status': resolved_vendor_status, 'supplier_invoice_no': inv_no, 'gstin': gstin_val, 'irn': row.get('irn'), 'ack_no': row.get('ack_no'), 'ack_date': row.get('ack_date'), 'created_at': row.get('created_at'), 'voucher_type': row.get('voucher_type'), 'branch': row.get('branch'), 'file_hash': row.get('file_hash'), 'file_path': row.get('file_path')})
                        logger.info(f"[SNAPSHOT_HYDRATION_STATE] record_id={row.get('id')} inv_no={inv_no} vendor_status={resolved_vendor_status} vendor_id={resolved_vendor_id} validation_status={_snap_val_status} item_status={row.get('item_status', 'NOT_SET')} source=snapshot_fallback")
                    mapped = self._map_record_to_ui_row(dummy, norm_data=norm_source, vendor_map=_snap_vendor_map)
                    if resume:
                        if mapped.get('is_saved') or mapped.get('validationStatus') in {'VOUCHER_CREATED', 'DUPLICATE', 'DUPLICATE_IN_BATCH', 'DUPLICATE_INVOICE'} or mapped.get('processed'):
                            continue
                    mapped_data.append(mapped)
            logger.info(f'[STAGING_POLL] session={session_id} records={len(mapped_data)} terminal=True pipeline_status=completed hydration_pending=False')
            # [ROOT_CAUSE_FIX] If snapshot was empty (snapshot_json=[]), fall back to live DB records
            # to prevent returning FINALIZED with zero rows when data is in InvoiceTempOCR table.
            if not mapped_data and all_db_records:
                logger.warning(f'[SNAPSHOT_EMPTY_FALLBACK] session={session_id} — snapshot had no rows, falling back to {len(all_db_records)} live DB records')
                for db_record in all_db_records:
                    if not getattr(db_record, 'tenant_id', None) and tenant_id:
                        db_record.tenant_id = tenant_id
                    mapped = self._map_record_to_ui_row(db_record, norm_data=db_record.extracted_data, vendor_map=_snap_vendor_map)
                    if resume:
                        if mapped.get('is_saved') or mapped.get('validationStatus') in {'VOUCHER_CREATED', 'DUPLICATE', 'DUPLICATE_IN_BATCH', 'DUPLICATE_INVOICE'} or mapped.get('processed'):
                            continue
                    mapped_data.append(mapped)
                logger.info(f'[SNAPSHOT_EMPTY_FALLBACK] session={session_id} fallback produced {len(mapped_data)} rows')
            for row in mapped_data:
                logger.critical('[FORENSIC_ITEMS_STRUCTURE]\n%s', json.dumps(row.get('items'), indent=2, default=str))
                logger.critical('[FORENSIC_ITEMS_LIFECYCLE] [BEFORE_API_RESPONSE] record_id=%s invoice_no=%s item_count=%d item_status=%s payload_keys=%s', row.get('id'), row.get('invoice_no'), len(row.get('items', [])), row.get('item_status'), list(row.keys()))
            self._log_final_api_response_rows(mapped_data, 'snapshot')
            return Response({'status': 'FINALIZED', 'data': mapped_data, 'pipeline_status': 'completed', 'terminal': True, 'hydration_pending': False, 'completed': True, 'failed': False, 'progress_percent': 100.0, 'poll_latency': round(time.time() - t_poll_start, 3)})
        logger.info(f'[STAGING_POLL] session={session_id} records=0 terminal=False pipeline_status=processing hydration_pending=True')
        return Response({'status': 'PROCESSING', 'data': [], 'pipeline_status': 'processing', 'terminal': False, 'hydration_pending': True, 'completed': False, 'failed': False, 'progress_percent': progress_percent, 'poll_latency': round(time.time() - t_poll_start, 3)})

    def patch(self, request, file_hash=None):
        """
        Step 3: Fix normalization on manual edits.
        """
        from .normalize import get_canonical_export_record
        from .grouping import run_grouping_logic
        if not file_hash:
            return Response({'error': 'Id or file_hash required'}, status=400)
        record = None
        if str(file_hash).startswith('snap_'):
            session_id = str(file_hash).replace('snap_', '')
            updated_data = request.data.get('extracted_data', {})
            sections = updated_data.get('sections', {})
            inv_no = sections.get('supplier_details', {}).get('supplier_invoice_no') or updated_data.get('supplier_invoice_no') or updated_data.get('invoice_no')
            gstin_val = sections.get('supplier_details', {}).get('gstin') or updated_data.get('gstin')
            query = InvoiceTempOCR.objects.filter(upload_session_id=session_id, tenant_id=request.user.branch_id)
            if inv_no:
                query = query.filter(supplier_invoice_no__iexact=inv_no)
            if gstin_val:
                query = query.filter(gstin__iexact=gstin_val)
            record = query.first()
            if not record:
                record = InvoiceTempOCR.objects.filter(upload_session_id=session_id, tenant_id=request.user.branch_id).first()
        else:
            record = InvoiceTempOCR.objects.filter(file_hash=file_hash, tenant_id=request.user.branch_id).first()
            if not record:
                record = InvoiceTempOCR.objects.filter(id=int(file_hash) if str(file_hash).isdigit() else None).first()
        if not record:
            return Response({'error': 'File not found'}, status=404)
        
        company_match_decision = request.data.get('company_match_decision')
        if company_match_decision:
            if not isinstance(record.extracted_data, dict):
                record.extracted_data = {}
            record.extracted_data['company_match_decision'] = company_match_decision
            record.extracted_data['company_match_detected'] = (company_match_decision != 'PROCEED')
            if company_match_decision == 'NOT_PROCEED':
                record.validation_status = 'REJECTED'
            record.save(update_fields=['extracted_data', 'validation_status'])
            from pending_purchases.models import PendingPurchase
            PendingPurchase.objects.filter(source_scan_row_id=record.id).update(
                company_match_decision=company_match_decision,
                company_match_detected=(company_match_decision != 'PROCEED'),
                pending_purchase_status='REJECTED' if company_match_decision == 'NOT_PROCEED' else 'PENDING'
            )
            return Response({'status': 'SUCCESS', 'id': record.id, 'company_match_decision': company_match_decision, 'company_match_detected': (company_match_decision != 'PROCEED')})

        updated_data = request.data.get('extracted_data')
        if not updated_data:
            status_val = request.data.get('status')
            voucher_id_val = request.data.get('voucher_id')
            if status_val:
                record.validation_status = status_val
                if status_val == 'VOUCHER_CREATED':
                    record.processed = True
                    record.status = 'FINALIZED'
                if voucher_id_val:
                    record.voucher_id = voucher_id_val
                record.save()
                return Response({'success': True})
            return Response({'error': 'extracted_data required'}, status=400)
        try:
            sections = updated_data.get('sections', {})
            raw_target = {**{k: v for k, v in updated_data.items() if k != 'sections'}, **sections.get('supplier_details', {}), **sections.get('supply_details', {}), **sections.get('due_details', {}), **sections.get('transit_details', {}), 'line_items': sections.get('items', [])}
            db_status = record.status
            db_processed = record.processed
            old_supplier_invoice_no = record.supplier_invoice_no
            InvoiceTempOCR.objects.filter(id=record.id).update(processed=False, status='FINALIZED', validation_status='PENDING')
            record = InvoiceTempOCR.objects.get(id=record.id)
            normalized_patch = get_canonical_export_record(updated_data, tenant_id=record.tenant_id)
            if isinstance(normalized_patch, dict):
                normalized_patch['sections'] = sections
            record.extracted_data = normalized_patch
            record.status = PipelineStatus.FINALIZED
            record.supplier_invoice_no = sections.get('supplier_details', {}).get('supplier_invoice_no') or raw_target.get('supplier_invoice_no') or raw_target.get('invoice_no')
            record.gstin = sections.get('supplier_details', {}).get('gstin') or raw_target.get('gstin')
            record.branch = sections.get('supplier_details', {}).get('branch') or raw_target.get('branch') or ''
            from .pipeline import sync_record_flattened_fields
            sync_record_flattened_fields(record, record.extracted_data, commit=False)
            record.save()
            from .pipeline import validate_and_process
            v_res = validate_and_process(record, user=request.user)
            try:
                from .models import FinalizedSnapshot
                snapshots = FinalizedSnapshot.objects.filter(session_id=record.upload_session_id)
                for snap in snapshots:
                    snap_data = self._get_snapshot_data(snap) if hasattr(self, '_get_snapshot_data') else snap.snapshot_json or {}
                    if not snap_data:
                        continue
                    rows = snap_data.get('data', [])
                    updated_any = False
                    new_vendor_name = record.extracted_data.get('vendor_name') or sections.get('supplier_details', {}).get('vendor_name') or updated_data.get('vendor_name')
                    new_invoice_no = record.extracted_data.get('invoice_no') or record.supplier_invoice_no or sections.get('supplier_details', {}).get('supplier_invoice_no') or updated_data.get('invoice_no')
                    for r_idx, r_dict in enumerate(rows):
                        matches_id = r_dict.get('id') == record.id or r_dict.get('file_hash') == record.file_hash
                        matches_inv = old_supplier_invoice_no and r_dict.get('invoice_no') and (str(r_dict.get('invoice_no')).strip().lower() == str(old_supplier_invoice_no).strip().lower())
                        if matches_id or matches_inv:
                            r_dict['vendor_name'] = new_vendor_name or r_dict.get('vendor_name')
                            r_dict['invoice_no'] = new_invoice_no or r_dict.get('invoice_no')
                            r_dict['gstin'] = record.gstin or r_dict.get('gstin')
                            r_dict['branch'] = record.branch or r_dict.get('branch')
                            r_dict['total_amount'] = updated_data.get('total_amount') or r_dict.get('total_amount')
                            if r_dict.get('id') is None and record.id:
                                r_dict['id'] = record.id
                            if r_dict.get('file_hash') is None and record.file_hash:
                                r_dict['file_hash'] = record.file_hash
                            updated_any = True
                    if updated_any:
                        if snap.s3_key:
                            from core.storage import StorageService
                            import json
                            import gzip
                            try:
                                json_bytes = json.dumps(snap_data).encode('utf-8')
                                if snap.s3_key.endswith('.gz'):
                                    json_bytes = gzip.compress(json_bytes)
                                StorageService().upload_file(file_bytes=json_bytes, key=snap.s3_key, content_type='application/json')
                            except Exception as s3_err:
                                import logging
                                logging.getLogger(__name__).warning(f'[S3_SYNC_ERR] {s3_err}')
                        else:
                            snap.snapshot_json = snap_data
                            snap.save(update_fields=['snapshot_json'])
            except Exception as e:
                import traceback
                import logging
                logging.getLogger(__name__).warning(f'[SNAPSHOT_SYNC_FAILED] {e}\n{traceback.format_exc()}')
            if isinstance(v_res, dict) and v_res.get('status') == 'LOCK_HELD':
                return Response({'error': 'Record is currently being processed by another background task. Please try again in a few seconds.'}, status=409)
            if db_processed:
                InvoiceTempOCR.objects.filter(id=record.id).update(processed=True, status=db_status)
            try:
                run_grouping_logic(record.tenant_id, record.upload_session_id)
            except Exception as ge:
                logger.error(f'Post-patch grouping failed: {str(ge)}')
            record.refresh_from_db()
            from vendors.vendor_validation_logic import build_session_vendor_map
            _vendor_map_raw = build_session_vendor_map(record.tenant_id, [record])
            mapped = self._map_record_to_ui_row(record, vendor_map=_vendor_map_raw)
            return Response({'success': True, 'status': mapped.get('validationStatus') or record.validation_status, 'vendor_id': mapped.get('vendor_id') or record.vendor_id, 'vendor_name': mapped.get('vendor_name') or (sections.get('supplier_details', {}).get('vendor_name') or updated_data.get('vendor_name') or ''), 'vendor_status': mapped.get('vendor_status') or ('EXISTS' if record.vendor_id else 'NEW'), 'item_status': mapped.get('item_status') or 'ALREADY EXIST', 'missing_items': mapped.get('missing_items') or [], 'items': mapped.get('items') or [], 'extracted_data': mapped.get('extracted_data') or {'sections': record.extracted_data.get('sections', {}) if isinstance(record.extracted_data, dict) else {}, **(record.extracted_data if isinstance(record.extracted_data, dict) else {})}})
        except Exception as e:
            logger.error(f'PATCH failure: {str(e)}')
            return Response({'error': str(e)}, status=400)

    def _get_snapshot_data(self, snapshot):
        """Helper to retrieve snapshot JSON from S3 or DB (Phase 5C)."""
        if snapshot.s3_key:
            from core.storage import StorageService
            try:
                logger.debug(f'[S3_SNAPSHOT_FETCH] session={snapshot.session_id} key={snapshot.s3_key}')
                data = StorageService().get_file(snapshot.s3_key)
                if snapshot.s3_key.endswith('.gz'):
                    import gzip
                    data = gzip.decompress(data)
                return json.loads(data)
            except Exception as e:
                logger.error(f'[S3_FETCH_FAILED] {e}')
                return snapshot.snapshot_json or {}
        return snapshot.snapshot_json or {}

    def delete(self, request, file_hash=None):
        if not file_hash:
            return Response({'error': 'Id or file_hash required'}, status=400)
        if str(file_hash).isdigit():
            deleted, _ = InvoiceTempOCR.objects.filter(id=int(file_hash), tenant_id=request.user.branch_id).delete()
        else:
            deleted, _ = InvoiceTempOCR.objects.filter(file_hash=file_hash, tenant_id=request.user.branch_id).delete()
        return Response({'success': bool(deleted)})

class OCRStagingMatchItemView(views.APIView):
    """
    Direct Inventory Match Endpoint — NO vendor required.

    POST /api/ocr-staging/<file_hash>/match-item/
    Body: {
        "inventory_item_id": <int>,
        "item_name": "<canonical master item name>",
        "line_index": <int>          # 0-based index of the line item in extracted_data.items[]
    }

    Sets match_source='MANUAL_MATCH', item_status='ALREADY EXIST' on the targeted line item
    and immediately persists. Does NOT create any vendor product mapping.
    Returns the updated UI row so the frontend can refresh without a full poll cycle.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, file_hash=None):
        if not file_hash:
            return Response({'error': 'file_hash or id required'}, status=400)
        tenant_id = getattr(request.user, 'branch_id', None) or getattr(request.user, 'tenant_id', None)
        if str(file_hash).isdigit():
            record = InvoiceTempOCR.objects.filter(id=int(file_hash), tenant_id=tenant_id).first()
        else:
            record = InvoiceTempOCR.objects.filter(file_hash=file_hash, tenant_id=tenant_id).first()
        if not record:
            return Response({'error': f'Staging record not found for identifier: {file_hash}'}, status=404)
        inventory_item_id = request.data.get('inventory_item_id')
        matched_item_name = request.data.get('item_name', '')
        line_index = request.data.get('line_index')
        if not inventory_item_id:
            return Response({'error': 'inventory_item_id is required'}, status=400)
        try:
            from inventory.models import InventoryItem
            inv_item = InventoryItem.objects.filter(id=int(inventory_item_id), tenant_id=tenant_id).first()
            if not inv_item:
                return Response({'error': f'Inventory item {inventory_item_id} not found for this tenant.'}, status=404)
            canonical_name = inv_item.item_name or matched_item_name
        except Exception as e:
            logger.error(f'[MATCH_ITEM_INV_LOOKUP_FAILED] id={inventory_item_id} error={e}')
            return Response({'error': f'Failed to verify inventory item: {e}'}, status=400)
        try:
            data = record.extracted_data or {}
            if not isinstance(data, dict):
                data = {}
            items = data.get('items') or []
            if not items and 'sections' in data:
                items = data.get('sections', {}).get('items', [])
            if not isinstance(items, list):
                items = []
            patched = False
            for i, item in enumerate(items):
                target = line_index is not None and int(line_index) == i or (line_index is None and i == 0)
                if target:
                    item['inventory_item_id'] = inv_item.id
                    item['matched_item_name'] = canonical_name
                    item['canonical_name'] = canonical_name
                    item['match_source'] = 'MANUAL_MATCH'
                    item['item_status'] = 'ALREADY EXIST'
                    item['inventory_match_level'] = 'MANUAL_MATCH'
                    item['inventory_match_strategy'] = 'MANUAL_MATCH'
                    item['inventory_match_confidence'] = 100.0
                    patched = True
                    logger.info(f"[MANUAL_MATCH_APPLIED] record={record.id} line_index={i} inventory_item_id={inv_item.id} name='{canonical_name}'")
            if not patched:
                return Response({'error': f'Line item at index {line_index} not found in staging record.'}, status=404)
            if 'sections' in data and 'items' not in data:
                data['sections']['items'] = items
            else:
                data['items'] = items
            has_create = any((itm.get('item_status') in ('CREATE ITEM', 'CREATE_ITEM') for itm in items))
            if has_create:
                overall_item_status = 'CREATE ITEM'
            else:
                overall_item_status = 'ALREADY EXIST'
            data['item_status'] = overall_item_status
            data['missing_items'] = [itm for itm in items if itm.get('item_status') in ('CREATE ITEM', 'CREATE_ITEM')]
            if 'assembled_exports' in data and data['assembled_exports']:
                data['assembled_exports'][0]['items'] = items
                data['assembled_exports'][0]['item_status'] = overall_item_status
                data['assembled_exports'][0]['missing_items'] = data['missing_items']
            record.extracted_data = data
            InvoiceTempOCR.objects.filter(id=record.id).update(extracted_data=data)
            logger.info(f'[MANUAL_MATCH_PERSISTED] record={record.id} overall_item_status={overall_item_status} tenant={tenant_id}')
        except Exception as e:
            logger.error(f'[MATCH_ITEM_PATCH_FAILED] record={record.id} error={e}', exc_info=True)
            return Response({'error': f'Failed to apply match: {e}'}, status=500)
        try:
            record.refresh_from_db()
            from vendors.vendor_validation_logic import build_session_vendor_map
            _vendor_map = {}
            try:
                _vendor_map = build_session_vendor_map(tenant_id, [record])
            except Exception:
                pass
            view_instance = CleanOCRStagingView()
            view_instance.request = request
            mapped = view_instance._map_record_to_ui_row(record, vendor_map=_vendor_map)
        except Exception as e:
            logger.warning(f'[MATCH_ITEM_UI_ROW_BUILD_FAILED] record={record.id} error={e}')
            mapped = {}
        return Response({'success': True, 'inventory_item_id': inv_item.id, 'matched_item_name': canonical_name, 'item_status': overall_item_status, 'row': mapped}, status=status.HTTP_200_OK)

def _handle_session_metadata_upload(request, session_ids, tenant_id):
    """Processes metadata for files already uploaded to S3 via pre-signed URLs."""
    from core.sqs import QueueService
    queue = QueueService()
    voucher_type = request.data.get('voucher_type', 'PURCHASE')
    upload_type = request.data.get('upload_type', '').strip().upper() or 'UNKNOWN'
    upload_session_id = request.data.get('upload_session_id')
    depth = queue.get_queue_depth(queue_type='ingestion')
    from core.observability import observability
    observability.api_metric(event='BACKPRESSURE_CHECK', queue_depth=depth)
    if depth > 1000:
        logger.warning(f'[API_BACKPRESSURE] Queue depth {depth} exceeds threshold.')
        observability.api_metric(event='BACKPRESSURE_THROTTLED', queue_depth=depth)
        return Response({'error': 'Processing queue is full. Please wait a few minutes.', 'status': 'BACKPRESSURE_THROTTLED', 'queue_depth': depth}, status=status.HTTP_429_TOO_MANY_REQUESTS)
    sessions = UploadSession.objects.filter(id__in=session_ids, tenant_id=tenant_id)
    if not sessions.exists():
        return Response({'error': 'Invalid session_ids'}, status=400)
    job = OCRJob.objects.create(tenant_id=tenant_id, total_files=sessions.count(), status='PENDING', upload_type=upload_type)
    queued_count = 0
    for session in sessions:
        task = OCRTask.objects.create(job=job, file_name=session.file_name, file_url=f's3://{session.s3_key}', status='PENDING')
        from vouchers.message_factory import message_factory
        from core.middleware import get_correlation_id
        ingestion_payload = {'record_id': task.id, 'job_id': str(job.id), 'file_key': session.s3_key, 'voucher_type': voucher_type, 'upload_type': upload_type, 'upload_session_id': upload_session_id or str(session.id)}
        msg = message_factory.create_message(task_type='INGESTION', tenant_id=tenant_id, session_id=upload_session_id or str(session.id), payload=ingestion_payload, correlation_id=get_correlation_id())
        logger.info(f"[DISTRIBUTED_PIPELINE_ACTIVE] session_id='{upload_session_id or str(session.id)}' status='ACTIVE'")
        from copy import deepcopy
        msg_copy = deepcopy(msg)
        try:
            queue.push(msg_copy, queue_type='ingestion')
            logger.info(f"[QUEUE_FORWARD_SUCCESS] target_queue=ingestion msg_id={msg_copy['id']}")
        except Exception as e:
            logger.error(f'[QUEUE_FORWARD_FAILURE] target_queue=ingestion error={e}')
            raise
        logger.info(f"[SQS_DISPATCH_SUCCESS] session_id='{upload_session_id or str(session.id)}' msg_id='{msg.get('id')}' queue='ingestion'")
        session.status = 'COMPLETED'
        session.save()
        queued_count += 1
    from core.observability import observability as _obs
    _obs.api_metric(event='BULK_UPLOAD_METADATA', count=queued_count, session_id=upload_session_id)
    return Response({'success': True, 'job_id': str(job.id), 'status': 'PROCESSING', 'message': f'Enqueued {queued_count} direct S3 tasks.'}, status=status.HTTP_202_ACCEPTED)

class PipelineStatusSSEView(views.APIView):
    """
    PHASE 5B: SSE INFRASTRUCTURE.
    Replaces polling with push-based terminal state signaling.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        tenant_id = request.user.branch_id
        from core.observability import observability, metrics

        def event_stream():
            observability.info(event='SSE_CONNECTED', session_id=session_id, user_id=request.user.id)
            metrics.increment_counter('sse:connections_total')
            try:
                from core.redis_orchestrator import orchestrator
                from .models import FinalizedSnapshot, PipelineStatus, InvoiceTempOCR
                while True:
                    records = InvoiceTempOCR.objects.filter(upload_session_id=session_id)
                    is_processing = records.filter(status__in=['PENDING', 'INGESTED', 'INGESTING', PipelineStatus.QUEUED, PipelineStatus.PROCESSING, PipelineStatus.EXTRACTING, PipelineStatus.ASSEMBLING, PipelineStatus.FINALIZING]).exists() if records.exists() else True
                    auth_state = orchestrator.get_authoritative_session_state(session_id)
                    if auth_state and auth_state.get('terminal', False):
                        terminal_reason = auth_state.get('terminal_reason', 'FAILED')
                        logger.info(f'[SSE_AUTHORITATIVE_TERMINAL] session={session_id} reason={terminal_reason}')
                        if terminal_reason in {'FAILED', 'FAILED_DUPLICATE', 'ERROR'}:
                            yield f"data: {json.dumps({'status': 'FAILED', 'session_id': session_id, 'reason': terminal_reason})}\n\n"
                            break
                    redis_status = orchestrator.get_session_status(session_id)
                    if redis_status:
                        logger.info(f"[SSE_REDIS_HIT] session={session_id} status={redis_status['status']} progress={redis_status['progress']}")
                        if redis_status['status'] in {'COMPLETED', 'FINALIZED'}:
                            val_exists = FinalizedSnapshot.objects.filter(session_id=session_id, tenant_id=tenant_id).exists()
                            if val_exists and (not is_processing):
                                logger.info(f'[SNAPSHOT_QUERY_VALIDATED] SSE validated snapshot for session={session_id}')
                                logger.info(f'[SNAPSHOT_READY_EMIT] SSE emitting SNAPSHOT_READY for session={session_id}')
                                yield f"data: {json.dumps({'status': 'FINALIZED', 'session_id': session_id, 'progress': 100})}\n\n"
                                break
                            else:
                                logger.warning(f"[SSE_WAIT_SNAPSHOT] Redis status is {redis_status['status']} but records are still processing or snapshot not committed yet for session={session_id}")
                        if redis_status['status'] == 'FAILED' and (not is_processing):
                            yield f"data: {json.dumps({'status': 'FAILED', 'session_id': session_id})}\n\n"
                            break
                        yield f"data: {json.dumps({'status': redis_status['status'], 'session_id': session_id, 'progress': redis_status['progress']})}\n\n"
                        if redis_status['status'] == 'EXPORTED':
                            break
                    if not is_processing and records.exists():
                        snapshot = FinalizedSnapshot.objects.filter(session_id=session_id, tenant_id=tenant_id).order_by('-created_at').first()
                        if not snapshot:
                            snapshot = FinalizedSnapshot.objects.filter(session_id=session_id).order_by('-created_at').first()
                        if snapshot:
                            logger.info(f'[SESSION_FINALIZED_EVENT] session_id={session_id} event=SNAPSHOT_READY')
                            yield f"data: {json.dumps({'status': 'FINALIZED', 'snapshot_id': str(snapshot.id)})}\n\n"
                            break
                    if records.exists():
                        total = records.count()
                        failed = records.filter(status=PipelineStatus.FAILED).count()
                        if failed == total and (not is_processing):
                            logger.info(f'[SESSION_FINALIZED_EVENT] session_id={session_id} event=FAILED')
                            yield f"data: {json.dumps({'status': 'FAILED'})}\n\n"
                            break
                    time.sleep(2)
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                logger.error(f'[SSE_CRITICAL_ERROR] session={session_id} error={str(e)}\n{error_trace}')
                yield f"data: {json.dumps({'status': 'ERROR', 'message': str(e)})}\n\n"
            finally:
                metrics.increment_counter('sse:disconnections_total')
        from django.http import StreamingHttpResponse
        return StreamingHttpResponse(event_stream(), content_type='text/event-stream')

class S3UploadPolicyView(views.APIView):
    """
    PHASE 2: DIRECT S3 UPLOAD POLICY.
    Removes RAM/Bandwidth pressure from Django by allowing direct client -> S3 transfers.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file_name = request.data.get('file_name')
        tenant_id = request.user.branch_id
        if not file_name:
            return Response({'error': 'file_name required'}, status=400)
        from core.storage import StorageService
        storage = StorageService()
        import uuid
        session_id = uuid.uuid4()
        s3_key = f"uploads/{tenant_id}/{session_id}/{file_name.replace('/', '_')}"
        policy = storage.generate_presigned_post(s3_key)
        if not policy:
            return Response({'error': 'Failed to generate upload policy'}, status=500)
        UploadSession.objects.create(id=session_id, tenant_id=tenant_id, file_name=file_name, s3_key=s3_key, status='INITIATED')
        return Response({'session_id': str(session_id), 's3_key': s3_key, 'policy': policy})

class OCRJobStatusView(views.APIView):
    """
    NEW: Pollable endpoint for background job status.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        tenant_id = request.user.branch_id
        try:
            job = OCRJob.objects.get(id=job_id, tenant_id=tenant_id)
            total = job.total_files
            processed = job.processed_files
            failed = job.failed_files
            from django.db import models
            from .models import SessionFinalizationState
            record_ids = job.tasks.filter(result_id__isnull=False).values_list('result_id', flat=True)
            stats = SessionFinalizationState.objects.filter(id__in=[str(rid) for rid in record_ids]).aggregate(total_expected=models.Sum('expected_pages'), total_ai_completed=models.Sum('ai_completed_pages'))
            total_expected = stats['total_expected'] or 0
            total_ai_completed = stats['total_ai_completed'] or 0
            if total_expected > 0 and (not job.status in {'COMPLETED', 'FAILED'}):
                progress = total_ai_completed / total_expected * 100
                progress = min(progress, 98.0)
            else:
                progress = (processed + failed) / total * 100 if total > 0 else 100
            is_terminal = job.status in {'COMPLETED', 'FAILED', 'PARTIAL'}
            if is_terminal:
                progress = 100.0
            poll_after = 2
            if is_terminal:
                poll_after = 0
            elif job.status == 'PENDING':
                poll_after = 10
            elif job.status == 'QUEUED':
                poll_after = 5
            return Response({'job_id': job.id, 'status': job.status, 'progress_percent': round(progress, 2), 'processed_count': processed, 'failed_count': failed, 'total_files': total, 'is_completed': is_terminal, 'poll_after_seconds': poll_after, 'created_at': job.created_at, 'updated_at': job.updated_at})
        except OCRJob.DoesNotExist:
            return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)

class OCRStagingFinalizeView(views.APIView):
    """
    Finalize staged invoices into real Vouchers.
    Handles two paths:
      A) Automated: records already processed by finalize_worker (processed=True) → return persisted counts.
      B) Manual: records still pending → run validate_and_process(auto_save=True) for each.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tenant_id = request.user.branch_id
        upload_session_id = request.data.get('upload_session_id')
        logger.info(f'[FINALIZE_ENQUEUE_START] session={upload_session_id} tenant={tenant_id} source=API')
        logger.info(f'[FINALIZE_START] session={upload_session_id} tenant={tenant_id}')
        if not upload_session_id:
            return Response({'error': 'upload_session_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        from core.redis_orchestrator import orchestrator
        auth_state = orchestrator.get_authoritative_session_state(upload_session_id)

        def _to_int(val) -> int:
            try:
                return int(val) if val is not None else 0
            except (ValueError, TypeError):
                return 0

        def _to_bool(val) -> bool:
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                return val.lower() in ('true', '1', 'yes')
            return bool(val)
        expected = _to_int(auth_state.get('expected_pages', 0))
        completed = _to_int(auth_state.get('completed_pages', 0))
        failed = _to_int(auth_state.get('failed_pages', 0))
        snapshot_complete = _to_bool(auth_state.get('snapshot_complete', False))
        materialization_complete = _to_bool(auth_state.get('materialization_complete', False))
        is_converged = expected > 0 and completed + failed == expected and snapshot_complete and materialization_complete
        if not is_converged:
            logger.warning(f'[FINALIZE_BLOCKED_BARRIER] session={upload_session_id} expected={expected} completed={completed} failed={failed} snapshot_complete={snapshot_complete} materialization_complete={materialization_complete}')
            return Response({'error': 'Finalize blocked: orchestration barrier incomplete.', 'status': 'BLOCKED', 'details': auth_state}, status=status.HTTP_400_BAD_REQUEST)
        summary = {'success': True, 'total': 0, 'created': 0, 'skipped': 0, 'duplicate_skipped': 0, 'pending_skipped': 0, 'failed': 0, 'errors': []}
        all_records = list(InvoiceTempOCR.objects.filter(tenant_id=tenant_id, upload_session_id=upload_session_id))
        if not all_records:
            all_records = list(InvoiceTempOCR.objects.filter(upload_session_id=upload_session_id))
        summary['total'] = len(all_records)
        logger.info(f'[SESSION_ROW_SCOPE] session={upload_session_id} tenant={tenant_id} total_rows={len(all_records)}')
        eligible_tuples = get_save_eligible_rows(upload_session_id, tenant_id=tenant_id)
        pending_tuples = get_pending_purchase_eligible_rows(upload_session_id, tenant_id=tenant_id)
        ready_count = len(eligible_tuples)
        pending_count = len(pending_tuples)
        logger.info(f'[READY_COUNT_RECALCULATED] session={upload_session_id} ready_count={ready_count} pending_count={pending_count}')
        global_unresolved_count = InvoiceTempOCR.objects.filter(tenant_id=tenant_id, processed=False).count()
        logger.info(f'[FINALIZE_SESSION_ISOLATION_CHECK] session={upload_session_id} tenant={tenant_id} session_total_rows={len(all_records)} session_ready_count={ready_count} session_pending_count={pending_count} global_unresolved_count={global_unresolved_count}')
        seen_candidate_ids: set = set()
        candidates = []
        for r, ui_row in eligible_tuples:
            if r.id not in seen_candidate_ids:
                seen_candidate_ids.add(r.id)
                candidates.append(r)
                logger.info(f'[FINALIZE_CANDIDATE_ACCEPTED] record_id={r.id} source=save_eligible')
            else:
                logger.warning(f'[FINALIZE_DUPLICATE_CANDIDATE] record_id={r.id} source=save_eligible reason=already_added_from_same_list')
        for r, ui_row in pending_tuples:
            if r.id not in seen_candidate_ids:
                seen_candidate_ids.add(r.id)
                candidates.append(r)
                logger.info(f'[FINALIZE_CANDIDATE_ACCEPTED] record_id={r.id} source=pending_eligible')
            else:
                logger.warning(f'[FINALIZE_DUPLICATE_CANDIDATE] record_id={r.id} source=pending_eligible reason=already_in_save_eligible_list')
        duplicate_count = len(eligible_tuples) + len(pending_tuples) - len(candidates)
        logger.info(f'[FINALIZE_CANDIDATE_SUMMARY] session={upload_session_id} save_eligible={len(eligible_tuples)} pending_eligible={len(pending_tuples)} duplicates_removed={duplicate_count} final_unique_candidates={len(candidates)}')
        eligible_id_set: set = {t[0].id for t in eligible_tuples} | {t[0].id for t in pending_tuples}
        logger.info(f'[FINALIZE_ELIGIBILITY_CACHE_BUILT] session={upload_session_id} eligible_id_set_size={len(eligible_id_set)} (computed once — no per-iteration DB scans)')
        import time as _time
        _finalize_t0 = _time.time()
        logger.info(f'[SAVE_PIPELINE_START] session={upload_session_id} candidates_count={len(candidates)}')
        if len(candidates) > 0:
            from .pipeline import validate_and_process
            for record in candidates:
                db_rec = InvoiceTempOCR.objects.filter(id=record.id).first()
                if not db_rec:
                    continue
                if db_rec.id not in eligible_id_set:
                    logger.warning(f'[SAVE_ELIGIBILITY_FAILED] record_id={db_rec.id} no longer eligible (re-checked against pre-built set)')
                    continue
                logger.info(f'[PURCHASE_DB_INSERT_START] record={db_rec.id} vendor_id={db_rec.vendor_id} validation_status={db_rec.validation_status}')
                try:
                    with transaction.atomic():
                        logger.info(f'[SAVE_ELIGIBLE_ROW] Starting processing for record_id={db_rec.id}')
                        if db_rec.processed or db_rec.status == 'COMPLETED':
                            InvoiceTempOCR.objects.filter(id=db_rec.id).update(processed=False, status='FINALIZED', validation_status='NEED_TO_SAVE')
                            db_rec.refresh_from_db()
                        res = validate_and_process(db_rec, auto_save=True)
                        save_status = res.get('status') if isinstance(res, dict) else None
                        if save_status == 'LOCK_HELD':
                            logger.info(f'[LOCK_HELD_DETECTED] record={db_rec.id} is being processed by another worker. Polling database for status update...')
                            import time
                            poll_start = time.time()
                            completed_status = None
                            while time.time() - poll_start < 10.0:
                                time.sleep(0.5)
                                fresh_rec = InvoiceTempOCR.objects.filter(id=db_rec.id).first()
                                if fresh_rec and fresh_rec.processed:
                                    completed_status = fresh_rec.validation_status
                                    break
                            if completed_status:
                                save_status = completed_status
                                db_rec.refresh_from_db()
                                logger.info(f'[LOCK_HELD_RESOLVED_BY_POLLING] record={db_rec.id} resolved to status={save_status}')
                            else:
                                logger.warning(f'[LOCK_HELD_POLL_TIMEOUT] record={db_rec.id} did not finish processing in 10 seconds')
                        if save_status == 'VOUCHER_CREATED':
                            summary['created'] += 1
                            v_id = res.get('voucher_id') if isinstance(res, dict) else None
                            if not v_id:
                                v_id = getattr(db_rec, 'voucher_id', None)
                            logger.info(f'[VOUCHER_INSERT_SUCCESS] record={db_rec.id} voucher_id={v_id}')
                            db_rec.processed = True
                            db_rec.validation_status = 'VOUCHER_CREATED'
                            db_rec.status = 'COMPLETED'
                            db_rec.save(update_fields=['processed', 'validation_status', 'status'])
                            from pending_purchases.models import PendingPurchase
                            from django.utils import timezone
                            PendingPurchase.objects.filter(source_scan_row_id=db_rec.id, pending_purchase_status='PENDING').update(pending_purchase_status='RESOLVED', resolved_at=timezone.now(), review_payload={'resolved_voucher_id': v_id})
                        elif save_status in {'DUPLICATE', 'DUPLICATE_IN_BATCH', 'DUPLICATE_INVOICE'}:
                            summary['skipped'] += 1
                            summary['duplicate_skipped'] += 1
                            logger.info(f'[PURCHASE_DUPLICATE_DETECTED] record={db_rec.id} status={save_status}')
                            db_rec.validation_status = 'DUPLICATE'
                            db_rec.save(update_fields=['validation_status'])
                        elif save_status == 'PENDING_PURCHASE':
                            summary['skipped'] += 1
                            summary['pending_skipped'] += 1
                            logger.info(f'[PENDING_PURCHASE_ALREADY_QUEUED] record={db_rec.id} — skipping voucher creation')
                        else:
                            summary['failed'] += 1
                            err_msg = res.get('validation_message') if isinstance(res, dict) else 'Finalization failed'
                            if save_status == 'GST_MISMATCH':
                                err_type = 'GST_VALIDATION'
                            elif save_status in ('DUPLICATE', 'DUPLICATE_IN_BATCH', 'DUPLICATE_INVOICE'):
                                err_type = 'DUPLICATE_PROCESSING'
                            elif save_status in ('LOCK_HELD',):
                                err_type = 'SYSTEM_EXCEPTION'
                            elif save_status in ('ERROR', 'FAILED'):
                                err_type = 'BUSINESS_VALIDATION'
                            else:
                                err_type = 'BUSINESS_VALIDATION'
                            summary['errors'].append({'record_id': db_rec.id, 'invoice_number': getattr(db_rec, 'supplier_invoice_no', None), 'stage': 'FINALIZE', 'error_type': err_type, 'message': err_msg, 'error': err_msg, 'file': db_rec.file_path, 'pipeline_status': save_status})
                            logger.warning(f'[PURCHASE_SAVE_NOT_CREATED] record={db_rec.id} status={save_status} err_type={err_type} err={err_msg}')
                            transaction.set_rollback(True)
                except DatabaseError as db_e:
                    logger.error(f'[FINALIZE_DATABASE_ERROR] record={db_rec.id} error={db_e}', exc_info=True)
                    summary['failed'] += 1
                    summary['errors'].append({'record_id': db_rec.id, 'invoice_number': getattr(db_rec, 'supplier_invoice_no', None), 'stage': 'FINALIZE', 'error_type': 'DATABASE_EXCEPTION', 'message': str(db_e), 'error': str(db_e), 'file': db_rec.file_path, 'pipeline_status': 'DATABASE_ERROR'})
                except Exception as e:
                    import traceback as _tb
                    logger.error(f'[FINALIZE_RECORD_FAILED] record={db_rec.id} error={e}', exc_info=True)
                    summary['failed'] += 1
                    summary['errors'].append({'record_id': db_rec.id, 'invoice_number': getattr(db_rec, 'supplier_invoice_no', None), 'stage': 'FINALIZE', 'error_type': 'SYSTEM_EXCEPTION', 'message': str(e), 'error': str(e), 'file': db_rec.file_path, 'pipeline_status': 'EXCEPTION', 'stack_trace': _tb.format_exc()})
        if len(candidates) == 0:
            if summary['total'] > 0:
                qs_base = InvoiceTempOCR.objects.filter(tenant_id=tenant_id, upload_session_id=upload_session_id)
                summary['created'] = qs_base.filter(validation_status='VOUCHER_CREATED').count()
                summary['skipped'] = qs_base.filter(validation_status__in=['DUPLICATE', 'DUPLICATE_IN_BATCH', 'DUPLICATE_INVOICE']).count()
                summary['failed'] = qs_base.filter(processed=True, validation_status='ERROR').count()
                logger.info(f"[FINALIZE_PATH_A_FALLBACK] session={upload_session_id} created={summary['created']} skipped={summary['skipped']} failed={summary['failed']}")
        _finalize_elapsed = _time.time() - _finalize_t0
        logger.info(f"[SAVE_PIPELINE_COMPLETE] session={upload_session_id} created={summary['created']} skipped={summary['skipped']} failed={summary['failed']} elapsed={_finalize_elapsed:.3f}s candidates={len(candidates)}")
        summary['finalize_elapsed_seconds'] = round(_finalize_elapsed, 3)
        return Response(summary)

class OCRStagingCancelView(views.APIView):
    """
    Cancels an in-progress OCR session terminally.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tenant_id = request.user.branch_id
        session_id = request.data.get('session_id')
        if not session_id:
            return Response({'error': 'session_id required'}, status=400)
        from ocr_pipeline.models import OCRJob, OCRTask, InvoiceTempOCR
        logger.warning(f'[SESSION_CANCELLED] Cancelling session={session_id} tenant={tenant_id}')
        orchestrator.set_terminal_status(session_id, 'CANCELLED', reason='USER_CANCELLED')
        orchestrator.update_session_status(session_id, 'CANCELLED', progress=0.0, extra_data={'hydration_ready': True, 'fatal_error_verified': True})
        
        temp_qs = InvoiceTempOCR.objects.filter(upload_session_id=session_id)
        temp_ids = list(temp_qs.values_list('id', flat=True))
        temp_qs.update(status='CANCELLED')

        if temp_ids:
            task_qs = OCRTask.objects.filter(result_id__in=temp_ids)
            job_ids = list(task_qs.values_list('job_id', flat=True).distinct())
            task_qs.update(status='FAILED', error_message='Session cancelled by user')
            if job_ids:
                OCRJob.objects.filter(id__in=job_ids).update(status='FAILED', is_cancelled=True)
        return Response({'success': True, 'message': 'Session terminally cancelled.'})

class OCRStagingRescanView(views.APIView):
    """
    Re-trigger OCR extraction for an existing staging record.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tenant_id = request.user.branch_id
        file_hash = request.data.get('file_hash')
        if not file_hash:
            return Response({'error': 'file_hash required'}, status=400)
        record = InvoiceTempOCR.objects.filter(file_hash=file_hash, tenant_id=tenant_id).first()
        if not record:
            return Response({'error': 'Record not found'}, status=404)
        temp_file_path = os.path.join(settings.MEDIA_ROOT, 'ocr_temp', file_hash)
        if not os.path.exists(temp_file_path):
            return Response({'error': 'Source file not found for rescan. Please re-upload the file.'}, status=404)
        try:
            from vouchers.message_factory import message_factory
            rescan_payload = {'item_id': None, 'record_id': record.id, 'job_id': 'RESCAN', 'voucher_type': record.voucher_type, 'id': f'rescan_{record.id}_{int(time.time())}'}
            msg = message_factory.create_message(task_type='INGESTION', tenant_id=tenant_id, session_id=record.upload_session_id, payload=rescan_payload)
            from copy import deepcopy
            msg_copy = deepcopy(msg)
            try:
                from core.sqs import queue_service
                pushed = queue_service.push(msg_copy, queue_type='ingestion')
                if pushed:
                    logger.info(f"[QUEUE_FORWARD_SUCCESS] target_queue=ingestion msg_id={msg_copy['id']}")
                    logger.info(f"[DOWNSTREAM_ENQUEUE_SUCCESS] target_queue=ingestion msg_id={msg_copy['id']}")
                else:
                    logger.error(f'[QUEUE_FORWARD_FAILURE] target_queue=ingestion pushed is False')
                    logger.error(f'[DOWNSTREAM_ENQUEUE_FAILED] target_queue=ingestion pushed is False')
            except Exception as e:
                logger.error(f'[QUEUE_FORWARD_FAILURE] target_queue=ingestion error={e}')
                logger.error(f'[DOWNSTREAM_ENQUEUE_FAILED] target_queue=ingestion error={e}')
                raise
            if not pushed:
                return Response({'error': 'Failed to enqueue rescan task'}, status=500)
            record.status = 'OCR_QUEUED'
            record.save()
            return Response({'success': True, 'status': 'QUEUED', 'message': 'Rescan task enqueued successfully.'})
        except Exception as e:
            logger.error(f'RESCAN FAILED: {str(e)}')
            return Response({'error': f'Rescan failed: {str(e)}'}, status=500)

class OCRStagingRescanUploadView(views.APIView):
    """
    Allows uploading a missing source file for an existing record to re-trigger OCR.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tenant_id = request.user.branch_id
        old_hash = request.data.get('file_hash')
        uploaded_file = request.FILES.get('file')
        if not old_hash or not uploaded_file:
            return Response({'error': 'Original file_hash and new file required'}, status=400)
        record = InvoiceTempOCR.objects.filter(file_hash=old_hash, tenant_id=tenant_id).first()
        if not record:
            return Response({'error': 'Staging record not found'}, status=404)
        try:
            from core.sqs import queue_service
            temp_dir = os.path.join(settings.MEDIA_ROOT, 'ocr_temp')
            os.makedirs(temp_dir, exist_ok=True)
            sha256 = hashlib.sha256()
            for chunk in uploaded_file.chunks():
                sha256.update(chunk)
            new_hash = sha256.hexdigest()
            temp_file_path = os.path.join(temp_dir, new_hash)
            with open(temp_file_path, 'wb') as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
            record.file_hash = new_hash
            record.status = 'OCR_QUEUED'
            record.save()
            ocr_task = {'item_id': None, 'record_id': record.id, 'job_id': 'RESCAN_UPLOAD', 'tenant_id': tenant_id, 'voucher_type': record.voucher_type, 'upload_session_id': record.upload_session_id, 'id': f'rescan_up_{record.id}_{int(time.time())}'}
            from vouchers.message_factory import message_factory
            msg = message_factory.create_message(task_type='INGESTION', tenant_id=tenant_id, session_id=record.upload_session_id, payload=ocr_task)
            from copy import deepcopy
            msg_copy = deepcopy(msg)
            try:
                queue_service.push(msg_copy, queue_type='ingestion')
                logger.info(f"[QUEUE_FORWARD_SUCCESS] target_queue=ingestion msg_id={msg_copy['id']}")
                logger.info(f"[DOWNSTREAM_ENQUEUE_SUCCESS] target_queue=ingestion msg_id={msg_copy['id']}")
            except Exception as e:
                logger.error(f'[QUEUE_FORWARD_FAILURE] target_queue=ingestion error={e}')
                logger.error(f'[DOWNSTREAM_ENQUEUE_FAILED] target_queue=ingestion error={e}')
                raise
            return Response({'success': True, 'file_hash': new_hash, 'status': 'QUEUED', 'message': 'File uploaded and rescan task enqueued.'})
        except Exception as e:
            logger.error(f'RESCAN UPLOAD FAILED: {str(e)}')
            return Response({'error': f'Upload & Rescan failed: {str(e)}'}, status=500)

class ZohoAdapterView(views.APIView):
    """
    SEPARATE Zoho Adapter Layer.
    Consumes normalized OCR output and produces Zoho-compliant rows.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logger.info('API HIT: /api/zoho-adapter/ (ASYNC ENQUEUE)')
        data = request.data
        if not data:
            return Response({'error': 'No data provided'}, status=status.HTTP_400_BAD_REQUEST)
        tenant_id = request.user.branch_id
        session_id = data.get('session_id') or f'exp_{int(time.time())}'
        from .models import ExportTask
        task = ExportTask.objects.create(session_id=session_id, tenant_id=tenant_id, export_type='ZOHO', status='PENDING')
        from vouchers.message_factory import message_factory
        export_payload = {'export_id': str(task.id), 'data': data}
        msg = message_factory.create_message(task_type='EXPORT', tenant_id=tenant_id, session_id=session_id, payload=export_payload)
        from copy import deepcopy
        msg_copy = deepcopy(msg)
        logger.info(f"[EXPORT_TRIGGER] session_id={session_id} task_id={msg_copy['id']}")
        try:
            from core.sqs import queue_service
            queue_service.push(msg_copy, queue_type='export')
            logger.info(f"[QUEUE_FORWARD_SUCCESS] target_queue=export msg_id={msg_copy['id']}")
            logger.info(f"[DOWNSTREAM_ENQUEUE_SUCCESS] target_queue=export msg_id={msg_copy['id']}")
        except Exception as e:
            logger.error(f'[QUEUE_FORWARD_FAILURE] target_queue=export error={e}')
            logger.error(f'[DOWNSTREAM_ENQUEUE_FAILED] target_queue=export error={e}')
            raise
        logger.info(f'[EXPORT_ENQUEUED] task_id={task.id} session={session_id}')
        return Response({'success': True, 'task_id': str(task.id), 'session_id': session_id, 'status': 'QUEUED', 'message': 'Export transformation enqueued to specialized worker.'})

class ZohoReconstructView(views.APIView):
    """
    Returns reconstructed and normalized invoices (Step 1-3).
    Useful for displaying reconstructed items in the UI before export.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logger.info(f"API HIT: /api/zoho-reconstruct/ (Content-Length: {request.META.get('CONTENT_LENGTH')})")
        try:
            raw_body = request.body.decode('utf-8')
            logger.info(f'RAW_REQUEST_BODY_PRE_PARSE: {raw_body[:2000]}...')
            if not raw_body.strip():
                logger.error('CRITICAL: Empty request body received!')
        except Exception as be:
            logger.error(f'Failed to read raw request body: {be}')
        data = request.data
        if not data:
            logger.error('CRITICAL: request.data is empty after parsing!')
            return Response({'error': 'No data provided'}, status=status.HTTP_400_BAD_REQUEST)
        invoices_check = data.get('invoices', []) if isinstance(data, dict) else data if isinstance(data, list) else []
        for inv in invoices_check:
            if not inv.get('invoice_no') or not inv.get('items') or (not inv.get('bill_from')) or (not inv.get('vendor_name')):
                logger.warning(f"[RECONSTRUCT_BLOCKED_PREMATURE] Empty data detected. inv_no='{inv.get('invoice_no')}'")
                return Response({'error': 'Pipeline finalization incomplete. Premature reconstruction blocked.', 'code': 'PIPELINE_NOT_FINALIZED'}, status=status.HTTP_409_CONFLICT)
            record_id = inv.get('id')
            if record_id:
                record = InvoiceTempOCR.objects.filter(id=record_id).first()
                if record and record.status not in ['FINALIZED', 'VOUCHER_CREATED']:
                    logger.warning(f'[RECONSTRUCT_BLOCKED_PREMATURE] Record {record_id} not finalized (Status: {record.status})')
                    return Response({'error': 'Record not finalized in distributed cluster.', 'code': 'PIPELINE_NOT_FINALIZED'}, status=status.HTTP_409_CONFLICT)
        if 'invoices' not in data and isinstance(data, list):
            data = {'invoices': data}
        invoices_in = data.get('invoices', [])
        logger.info(f'FORENSIC_API_IN: Received {len(invoices_in)} invoices')
        for idx, inv in enumerate(invoices_in):
            if not isinstance(inv, dict):
                continue
            if not inv.get('items') or not inv.get('vendor_name') or (not inv.get('bill_from')):
                record_id = inv.get('id')
                if record_id:
                    try:
                        record = InvoiceTempOCR.objects.filter(id=record_id).first()
                        if record and record.extracted_data:
                            logger.info(f'FORENSIC_REHYDRATION: id={record_id} Triggered due to truncated payload')
                            db_data = record.extracted_data or {}
                            for k, v in db_data.items():
                                if k not in inv or not inv[k]:
                                    inv[k] = v
                            if not inv.get('gstin'):
                                inv['gstin'] = record.gstin
                            header = db_data.get('header', {})
                            if not inv.get('vendor_name'):
                                inv['vendor_name'] = db_data.get('vendor_name') or header.get('vendor_name') or record.vendor_name
                            if not inv.get('bill_from') or not inv.get('bill_address_from'):
                                bff = db_data.get('bill_from') or db_data.get('bill_address_from') or header.get('bill_from') or header.get('bill_address_from')
                                if not inv.get('bill_from'):
                                    inv['bill_from'] = bff
                                if not inv.get('bill_address_from'):
                                    inv['bill_address_from'] = bff
                    except Exception as re_err:
                        logger.error(f'Re-hydration failed for record {record_id}: {re_err}')
            items_in = inv.get('items', [])
            logger.info(f"FORENSIC_INV_IN[{idx}]: id={inv.get('id')} inv_no={inv.get('invoice_no')} vendor={inv.get('vendor_name')} items={len(items_in)} keys={list(inv.keys())}")
            if not inv.get('bill_from') and (not inv.get('bill_address_from')):
                logger.warning(f'FORENSIC_INV_IN[{idx}]: MISSING bill_from/bill_address_from!')
        try:
            adapter = get_zoho_adapter()
            processed_invoices = adapter.reconstruct_invoices(data)
            return Response({'invoices': processed_invoices})
        except Exception as e:
            logger.error(f'Zoho Reconstruct Failure: {str(e)}')
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OperationalDashboardView(views.APIView):
    """
    PHASE 11: REAL-TIME OPERATIONS DASHBOARD.
    Aggregates distributed metrics for live monitoring.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from core.observability import metrics
        from core.sqs import queue_service
        from core.redis_orchestrator import orchestrator
        queues = ['ingestion', 'ai', 'assembly', 'finalize', 'export']
        queue_stats = {}
        for q in queues:
            queue_stats[q] = {'depth': queue_service.get_queue_depth(q), 'visible': metrics.gauges.get(f"queue:visible:{{'queue': '{q}'}}", 0), 'invisible': metrics.gauges.get(f"queue:invisible:{{'queue': '{q}'}}", 0)}
        redis_stats = orchestrator.get_redis_metrics()
        all_metrics = metrics.get_all_metrics()
        from .models import InvoiceTempOCR, PoisonDocument
        db_summary = {'total_records': InvoiceTempOCR.objects.count(), 'failed_records': InvoiceTempOCR.objects.filter(status='FAILED').count(), 'finalized_records': InvoiceTempOCR.objects.filter(status='FINALIZED').count(), 'poison_documents': PoisonDocument.objects.count()}
        return Response({'timestamp': time.time(), 'queues': queue_stats, 'redis': redis_stats, 'metrics': all_metrics, 'db_summary': db_summary, 'slo_status': self._get_slo_status(all_metrics)})

    def _get_slo_status(self, all_metrics):
        """Phase 6: SLO Status calculation."""
        ai_latency = all_metrics.get('histograms', {}).get('worker:task_duration', {}).get('p95', 0)
        return {'ai_latency_slo': 'HEALTHY' if ai_latency < 120 else 'DEGRADED', 'queue_lag_slo': 'HEALTHY'}

def _resolve_rescan_file_path(record) -> str | None:
    """
    Resolve the actual OS path for a rescan source file.
    Handles the LOCAL:// virtual path scheme used by StorageService in local/dev deployments,
    as well as legacy MEDIA_ROOT-relative paths and bare absolute paths.
    Returns the resolved absolute path string if the file exists, otherwise None.
    """
    stored_path = record.file_path or ''
    if stored_path.startswith('LOCAL://'):
        try:
            from core.storage import StorageService
            storage = StorageService()
            key = stored_path.split('://', 1)[1]
            actual = os.path.normpath(os.path.join(storage.local_root, key.replace('/', os.sep)))
            if os.path.exists(actual):
                return actual
        except Exception:
            pass
    candidate = os.path.join(settings.MEDIA_ROOT, 'ocr_temp', record.file_hash)
    if os.path.exists(candidate):
        return candidate
    candidate = os.path.normpath(os.path.join(settings.MEDIA_ROOT, stored_path.lstrip('/')))
    if os.path.exists(candidate):
        return candidate
    if stored_path and os.path.exists(stored_path):
        return stored_path
    return None

class OCRStagingRowRescanView(views.APIView):
    """
    Exposes POST /api/ocr-staging/{id}/rescan to trigger row-level rescan.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        tenant_id = request.user.branch_id
        record = InvoiceTempOCR.objects.filter(pk=pk, tenant_id=tenant_id).first()
        if not record:
            return Response({'error': 'Record not found'}, status=status.HTTP_404_NOT_FOUND)
        resolved_path = _resolve_rescan_file_path(record)
        if not resolved_path:
            logger.error(f'[ROW_RESCAN_FILE_MISSING] record={record.id} stored_path={record.file_path}')
            return Response({'error': f"Source file not found for rescan. Stored path: {record.file_path or '(none)'}. Please re-upload the invoice to rescan it."}, status=status.HTTP_404_NOT_FOUND)
        reason = request.data.get('reason', '')
        with transaction.atomic():
            rescan_history = RescanHistory.objects.create(invoice_temp_ocr=record, rescan_type='ROW', user=str(request.user.username or request.user.email or request.user.id), reason=reason, cost_impact=0.0)
            from ocr_pipeline.models import SessionFinalizationState, InvoicePageResult
            InvoicePageResult.objects.filter(record_id=record.id).delete()
            SessionFinalizationState.objects.filter(id=str(record.id)).update(completed_pages=0, failed_pages=0, ai_completed_pages=0, total_pages_completed=0, ai_complete=False, snapshot_created=False, snapshot_complete=False, export_complete=False, materialization_complete=False, status='PROCESSING')
            from pending_purchases.models import PendingPurchase
            PendingPurchase.objects.filter(source_scan_row_id=record.id).update(pending_purchase_status='PENDING')
            record.status = 'PROCESSING'
            record.validation_status = 'PENDING'
            record.processed = False
            record.extracted_data = None
            record._bypass_immutability_guard = True
            record.save()
        try:
            from vouchers.message_factory import message_factory
            from copy import deepcopy
            from core.sqs import queue_service
            rescan_payload = {'item_id': None, 'record_id': record.id, 'job_id': f'RESCAN_{record.id}_{int(time.time())}', 'voucher_type': record.voucher_type, 'id': f'rescan_{record.id}_{int(time.time())}', 'is_rescan': True, 'rescan_history_id': rescan_history.id}
            msg = message_factory.create_message(task_type='INGESTION', tenant_id=tenant_id, session_id=record.upload_session_id, payload=rescan_payload)
            msg_copy = deepcopy(msg)
            pushed = queue_service.push(msg_copy, queue_type='ingestion')
            if pushed:
                logger.info(f"[ROW_RESCAN_ENQUEUE_SUCCESS] msg_id={msg_copy['id']} record={record.id}")
            else:
                logger.error(f'[ROW_RESCAN_ENQUEUE_FAILED] pushed is False for record={record.id}')
                return Response({'error': 'Failed to enqueue rescan task'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f'Row rescan enqueue failed: {e}')
            return Response({'error': f'Failed to trigger rescan: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'success': True, 'status': 'QUEUED', 'message': 'Row-level rescan triggered successfully.', 'rescan_history_id': rescan_history.id})

class OCRStagingSessionRescanView(views.APIView):
    """
    Exposes POST /api/ocr-staging/session/{session_id}/rescan to trigger session-level rescan.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        tenant_id = request.user.branch_id
        records = list(InvoiceTempOCR.objects.filter(upload_session_id=session_id, tenant_id=tenant_id))
        if not records:
            return Response({'error': 'No records found for session'}, status=status.HTTP_404_NOT_FOUND)
        reason = request.data.get('reason', '')
        triggered_count = 0
        with transaction.atomic():
            from ocr_pipeline.models import InvoicePageResult
            deleted_count, _ = InvoicePageResult.objects.filter(session_id=session_id).delete()
            logger.info(f'[SESSION_RESCAN_CLEANUP] Deleted {deleted_count} orphaned/page results for session={session_id}')
            for record in records:
                from ocr_pipeline.models import SessionFinalizationState
                SessionFinalizationState.objects.filter(id=str(record.id)).update(completed_pages=0, failed_pages=0, ai_completed_pages=0, total_pages_completed=0, ai_complete=False, snapshot_created=False, snapshot_complete=False, export_complete=False, materialization_complete=False, status='PROCESSING')
                from pending_purchases.models import PendingPurchase
                PendingPurchase.objects.filter(source_scan_row_id=record.id).update(pending_purchase_status='PENDING')
                record.status = 'PROCESSING'
                record.validation_status = 'PENDING'
                record.processed = False
                record.extracted_data = None
                record._bypass_immutability_guard = True
                record.save()
        unique_file_records = {}
        for record in records:
            resolved_path = _resolve_rescan_file_path(record)
            if not resolved_path:
                logger.warning(f'[SESSION_RESCAN_FILE_MISSING] Skipping enqueue for record={record.id} stored_path={record.file_path}')
                continue
            path = record.file_path
            if path in unique_file_records:
                if record.is_primary and (not unique_file_records[path].is_primary):
                    unique_file_records[path] = record
            else:
                unique_file_records[path] = record
        for record in unique_file_records.values():
            with transaction.atomic():
                rescan_history = RescanHistory.objects.create(invoice_temp_ocr=record, rescan_type='SESSION', user=str(request.user.username or request.user.email or request.user.id), reason=reason, cost_impact=0.0)
            try:
                from vouchers.message_factory import message_factory
                from copy import deepcopy
                from core.sqs import queue_service
                rescan_payload = {'item_id': None, 'record_id': record.id, 'job_id': f'RESCAN_{record.id}_{int(time.time())}', 'voucher_type': record.voucher_type, 'id': f'rescan_{record.id}_{int(time.time())}', 'is_rescan': True, 'rescan_history_id': rescan_history.id}
                msg = message_factory.create_message(task_type='INGESTION', tenant_id=tenant_id, session_id=record.upload_session_id, payload=rescan_payload)
                msg_copy = deepcopy(msg)
                pushed = queue_service.push(msg_copy, queue_type='ingestion')
                if pushed:
                    triggered_count += 1
                    logger.info(f"[SESSION_RESCAN_ENQUEUE_SUCCESS] msg_id={msg_copy['id']} record={record.id}")
                else:
                    logger.error(f'[SESSION_RESCAN_ENQUEUE_FAILED] pushed is False for record={record.id}')
            except Exception as e:
                logger.error(f'Session rescan record={record.id} enqueue failed: {e}')
        return Response({'success': True, 'status': 'QUEUED', 'message': f'Triggered rescan for {triggered_count} records in session.', 'triggered_count': triggered_count})

class OCRStagingCorrectGSTView(CleanOCRStagingView):
    """
    Exposes POST /api/ocr-staging/<pk>/correct-gst/ to correct CGST, SGST, and IGST values.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        tenant_id = request.user.branch_id
        try:
            record = InvoiceTempOCR.objects.get(id=pk, tenant_id=tenant_id)
        except InvoiceTempOCR.DoesNotExist:
            return Response({'error': 'Record not found'}, status=status.HTTP_404_NOT_FOUND)
        cgst = request.data.get('cgst')
        sgst = request.data.get('sgst')
        igst = request.data.get('igst')
        if not isinstance(record.extracted_data, dict):
            record.extracted_data = {}

        def to_float_or_zero(val):
            try:
                if val is None or str(val).strip() == '':
                    return 0.0
                return float(str(val).replace('₹', '').replace(',', '').replace(' ', '').strip())
            except ValueError:
                return 0.0
        cgst_val = to_float_or_zero(cgst)
        sgst_val = to_float_or_zero(sgst)
        igst_val = to_float_or_zero(igst)
        ext = record.extracted_data
        items_payload = request.data.get('items')
        if items_payload and isinstance(items_payload, list):
            ext['items'] = items_payload
        ext['total_cgst'] = cgst_val
        ext['cgst'] = cgst_val
        ext['total_sgst'] = sgst_val
        ext['sgst'] = sgst_val
        ext['total_igst'] = igst_val
        ext['igst'] = igst_val
        sections = ext.setdefault('sections', {})
        if isinstance(sections, dict):
            supply_details = sections.setdefault('supply_details', {})
            if isinstance(supply_details, dict):
                supply_details['total_cgst'] = cgst_val
                supply_details['cgst'] = cgst_val
                supply_details['total_sgst'] = sgst_val
                supply_details['sgst'] = sgst_val
                supply_details['total_igst'] = igst_val
                supply_details['igst'] = igst_val
        assembled = ext.get('assembled_exports') or []
        if isinstance(assembled, list) and assembled:
            ae = assembled[0]
            if isinstance(ae, dict):
                ae['total_cgst'] = cgst_val
                ae['cgst'] = cgst_val
                ae['total_sgst'] = sgst_val
                ae['sgst'] = sgst_val
                ae['total_igst'] = igst_val
                ae['igst'] = igst_val
                ae_sections = ae.setdefault('sections', {})
                if isinstance(ae_sections, dict):
                    ae_supply = ae_sections.setdefault('supply_details', {})
                    if isinstance(ae_supply, dict):
                        ae_supply['total_cgst'] = cgst_val
                        ae_supply['cgst'] = cgst_val
                        ae_supply['total_sgst'] = sgst_val
                        ae_supply['sgst'] = sgst_val
                        ae_supply['total_igst'] = igst_val
                        ae_supply['igst'] = igst_val
        if 'gst_resolution' in ext:
            ext.pop('gst_resolution', None)
        record.save(update_fields=['extracted_data'])
        from .pipeline import run_gst_validation_engine
        run_gst_validation_engine(record, user=request.user)
        record.refresh_from_db()
        audit_trail = record.extracted_data.get('gst_audit_trail', {})
        diff_val = 0.0
        if isinstance(audit_trail, dict):
            diff_val = audit_trail.get('difference_amount', 0.0)
        resolution_choice = request.data.get('resolution') or request.data.get('gst_resolution')
        if not resolution_choice:
            if diff_val <= 1.0:
                resolution_choice = 'CORRECTED'
            else:
                resolution_choice = 'SUPPLIER_VALUES_ACCEPTED'
        if resolution_choice == 'SUPPLIER_VALUES_ACCEPTED' and (not items_payload):
            restore_supplier_gst_values(record)
        record.extracted_data['gst_resolution'] = resolution_choice
        record.save(update_fields=['extracted_data'])
        run_gst_validation_engine(record, user=request.user)
        record.refresh_from_db()
        from pending_purchases.models import PendingPurchase
        PendingPurchase.objects.filter(source_scan_row_id=record.id).update(extraction_payload=record.extracted_data)
        from .pipeline import validate_and_process
        validate_and_process(record, auto_save=False, user=request.user)
        record.refresh_from_db()
        ext_total = record.extracted_data.get('total_invoice_value') or record.extracted_data.get('total_amount') or 0.0
        PendingPurchase.objects.filter(source_scan_row_id=record.id).update(extraction_payload=record.extracted_data, invoice_number=record.supplier_invoice_no, vendor_gstin=record.gstin, amount=ext_total)
        ui_payload = self._map_record_to_ui_row(record)
        return Response(ui_payload)