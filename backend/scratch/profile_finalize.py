"""
profile_finalize.py

Profiles the finalize loop to pinpoint the exact time spent in each function.
"""
import os
import sys
import time
import cProfile
import pstats
import io

# Ensure backend directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
django.setup()

from core.models import User
from ocr_pipeline.views import OCRStagingFinalizeView
from django.test import RequestFactory

SESSION_ID = "4387be16-f770-44f4-ba15-d663ebb2cd66"

def run_finalize():
    user = User.objects.get(username='admin')
    # Generate JWT token using rest_framework_simplejwt
    from rest_framework_simplejwt.tokens import RefreshToken
    token = RefreshToken.for_user(user)
    access_token = str(token.access_token)

    factory = RequestFactory()
    request = factory.post('/api/ocr-staging-finalize/', 
                           {'upload_session_id': SESSION_ID}, 
                           content_type='application/json',
                           HTTP_AUTHORIZATION=f"Bearer {access_token}")
    request.user = user
    
    # Mock validate_tenant_access
    from unittest.mock import patch
    with patch('core.tenant.validate_tenant_access', return_value=(True, None)):
        view = OCRStagingFinalizeView.as_view()
        response = view(request)
        print("Response status:", response.status_code)
        print("Response data:", response.data)

def main():
    print("=== PROFILING OCR FINALIZE ===")
    
    pr = cProfile.Profile()
    pr.enable()
    
    run_finalize()
    
    pr.disable()
    s = io.StringIO()
    sortby = 'cumulative'
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats(30)
    print(s.getvalue())

if __name__ == '__main__':
    main()
