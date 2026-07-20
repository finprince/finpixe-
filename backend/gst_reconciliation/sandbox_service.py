import os
import uuid
from django.utils import timezone
import requests

class SandboxGSTService:
    """
    Service for integrating with the Sandbox API (developer.sandbox.co.in).
    """
    
    def __init__(self, api_key=None, api_secret=None):
        self.api_key = api_key or os.environ.get('SANDBOX_API_KEY')
        self.api_secret = api_secret or os.environ.get('SANDBOX_API_SECRET')
        self.base_url = "https://api.sandbox.co.in"
        self.mock_mode = True 
        
        self.headers = {
            'accept': 'application/json',
            'x-api-key': self.api_key or '',
            'x-api-version': '1.0',
            'Content-Type': 'application/json'
        }
        
    def authenticate(self):
        """Perform 2-step authentication handshake to get a Bearer Access Token"""
        if self.mock_mode:
            return {"success": True, "access_token": "sandbox_auth_not_required_for_basic_tests"}

        url = f"{self.base_url}/authenticate"
        auth_headers = {
            'accept': 'application/json',
            'x-api-key': self.api_key or '',
            'x-api-secret': self.api_secret or '',
            'x-api-version': '1.0'
        }
        try:
            res = requests.post(url, headers=auth_headers)
            if res.status_code == 200:
                token = res.json().get('access_token')
                return {"success": True, "access_token": token}
            return {"success": False, "error": f"Auth Failed: {res.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_auth_headers(self):
        auth_res = self.authenticate()
        headers = self.headers.copy()
        if auth_res.get('success') and auth_res.get('access_token'):
            headers['Authorization'] = auth_res['access_token'] # Sometimes Sandbox doesn't use Bearer, just the token
        
        # In Sandbox APIs, passing x-api-secret directly is also often supported if authenticate isn't used
        headers['x-api-secret'] = self.api_secret or ''
        return headers

    def verify_gstin(self, gstin):
        """Mock GSTIN verification"""
        if self.mock_mode:
            return {"success": True, "data": {"gstin": gstin}}
            
        url = f"{self.base_url}/gst/compliance/public/gstin/search"
        try:
            res = requests.get(url, headers=self._get_auth_headers(), params={"gstin": gstin})
            return {"success": res.status_code == 200, "data": res.json() if res.status_code == 200 else res.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def request_otp(self, gstin):
        """Simulates requesting an OTP from Sandbox API"""
        if self.mock_mode:
            return {"success": True, "message": f"OTP successfully sent to registered mobile for {gstin}"}
            
        url = f"{self.base_url}/authenticate/request-otp"
        try:
            res = requests.post(url, headers=self._get_auth_headers(), json={"gstin": gstin})
            if res.status_code == 200:
                return {"success": True, "message": "OTP sent successfully", "data": res.json()}
            else:
                return {"success": False, "error": f"Failed to request OTP: {res.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def verify_otp(self, gstin, otp):
        """Simulates verifying an OTP with Sandbox API"""
        if self.mock_mode:
            if otp == "123456": # Standard mock OTP
                return {"success": True, "auth_token": f"mock_token_{uuid.uuid4().hex}"}
            else:
                return {"success": False, "error": "Invalid OTP. Please enter 123456"}
                
        url = f"{self.base_url}/authenticate/verify-otp"
        try:
            res = requests.post(url, headers=self._get_auth_headers(), json={"gstin": gstin, "otp": otp})
            if res.status_code == 200:
                return {"success": True, "auth_token": res.json().get("auth_token", f"mock_token_{uuid.uuid4().hex}")}
            else:
                return {"success": False, "error": f"Failed to verify OTP: {res.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def file_gstr1(self, month, year, data_payload, auth_token=None):
        """Filing GSTR1 to the Sandbox API"""
        if self.mock_mode:
            return {
                "success": True,
                "reference_id": f"REF-GSTR1-{uuid.uuid4().hex[:8]}",
                "message": f"Successfully filed GSTR-1 for {month}/{year} (MOCK)",
                "timestamp": timezone.now().isoformat()
            }
            
        url = f"{self.base_url}/gst/compliance/tax-payer/gstrs/gstr-1/{year}/{month}/file"
        try:
            headers = self._get_auth_headers()
            if auth_token:
                headers['Authorization'] = auth_token
            response = requests.post(url, headers=headers, json=data_payload)
            if response.status_code in [200, 201, 202]:
                return {
                    "success": True,
                    "reference_id": response.json().get("reference_id", f"REF-{uuid.uuid4().hex[:6]}"),
                    "message": "Successfully submitted to Sandbox API",
                    "sandbox_response": response.json()
                }
            else:
                return {
                    "success": False,
                    "error": f"Sandbox API Rejected: {response.text}"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def fetch_gstr2b(self, gstin, month, year):
        """Fetching GSTR-2B data automatically from government"""
        if self.mock_mode:
            from accounting.models_voucher_purchase import VoucherPurchaseSupplierDetails
            
            mock_invoices = []
            month_map = {
                'January': 1, 'February': 2, 'March': 3, 'April': 4,
                'May': 5, 'June': 6, 'July': 7, 'August': 8,
                'September': 9, 'October': 10, 'November': 11, 'December': 12
            }
            month_num = month_map.get(month, timezone.now().month)

            # Auto-seed mock data for this specific month if empty
            if VoucherPurchaseSupplierDetails.objects.filter(date__month=month_num).exclude(gstin__isnull=True).exclude(gstin__exact='').count() < 2:
                self._seed_mock_purchase_vouchers(month_num)

            vouchers = VoucherPurchaseSupplierDetails.objects.filter(date__month=month_num).exclude(gstin__isnull=True).exclude(gstin__exact='').order_by('-id')[:2]
            
            # Exact Match (if we have a voucher)
            if len(vouchers) > 0:
                v1 = vouchers[0]
                mock_invoices.append({
                    "gstin": v1.gstin,
                    "vendor_name": "Mock Supplier 1",
                    "invoice_no": v1.supplier_invoice_no if v1.supplier_invoice_no else f"INV-{uuid.uuid4().hex[:5]}",
                    "invoice_date": v1.date.isoformat(),
                    "invoice_value": float(v1.total_amount) if hasattr(v1, 'total_amount') else 1000.0,
                    "taxable_value": 800.0,
                    "igst": 180.0,
                    "cgst": 0.0,
                    "sgst": 0.0,
                    "cess": 0.0
                })
            
            # Partial Match
            if len(vouchers) > 1:
                v2 = vouchers[1]
                mock_invoices.append({
                    "gstin": v2.gstin,
                    "vendor_name": "Mock Supplier 2",
                    "invoice_no": v2.supplier_invoice_no if v2.supplier_invoice_no else f"INV-{uuid.uuid4().hex[:5]}",
                    "invoice_date": (v2.date + timezone.timedelta(days=10)).isoformat(), # Misaligned date for partial
                    "invoice_value": float(v2.total_amount) if hasattr(v2, 'total_amount') else 1500.0,
                    "taxable_value": 1500.0,
                    "igst": 0.0,
                    "cgst": 0.0,
                    "sgst": 0.0,
                    "cess": 0.0
                })
                
            # Missing in Books (Completely random)
            mock_invoices.append({
                "gstin": "29ABCDE1234F1Z5",
                "vendor_name": "Unknown Supplier Inc",
                "invoice_no": f"MISSING-{uuid.uuid4().hex[:5]}",
                "invoice_date": timezone.now().replace(month=month_num).date().isoformat(),
                "invoice_value": 5000.0,
                "taxable_value": 4000.0,
                "igst": 1000.0,
                "cgst": 0.0,
                "sgst": 0.0,
                "cess": 0.0
            })

            return {"success": True, "data": {"b2b": mock_invoices}}
            
        url = f"{self.base_url}/gst/compliance/tax-payer/gstrs/gstr-2b/{year}/{month}/details"
        try:
            response = requests.get(url, headers=self._get_auth_headers())
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"Sandbox API Error: {response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _seed_mock_purchase_vouchers(self, month_num):
        """Seed dummy purchase vouchers so the mock reconciliation can generate exact/partial matches"""
        try:
            from vendors.models import VendorMasterBasicDetail
            from accounting.models_voucher_purchase import VoucherPurchaseSupplierDetails
            from accounting.models import MasterLedger
            
            # Need a dummy ledger to create vendor
            ledger = MasterLedger.objects.first()
            if not ledger:
                return # Can't seed without a ledger

            vendor, _ = VendorMasterBasicDetail.objects.get_or_create(
                vendor_name="Mock Seeded Vendor",
                defaults={
                    "tenant_id": "test-tenant",
                    "email": "test@example.com",
                    "contact_no": "9999999999",
                    "ledger": ledger
                }
            )

            # Create Exact Match Voucher
            VoucherPurchaseSupplierDetails.objects.create(
                date=timezone.now().replace(month=month_num).date(),
                supplier_invoice_no=f"SEED-EXACT-{uuid.uuid4().hex[:4]}",
                vendor_name=vendor.vendor_name,
                vendor_basic_detail=vendor,
                gstin="29ABCDE1111F1Z5",
                tenant_id="test-tenant"
            )

            # Create Partial Match Voucher
            VoucherPurchaseSupplierDetails.objects.create(
                date=timezone.now().replace(month=month_num).date(),
                supplier_invoice_no=f"SEED-PARTIAL-{uuid.uuid4().hex[:4]}",
                vendor_name=vendor.vendor_name,
                vendor_basic_detail=vendor,
                gstin="29ABCDE2222F1Z5",
                tenant_id="test-tenant"
            )
        except Exception as e:
            print("Failed to seed mock purchase vouchers:", e)
