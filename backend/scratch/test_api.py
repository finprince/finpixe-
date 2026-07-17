import urllib.request
import json

try:
    url = 'http://localhost:8000/api/gst/gstr1/at/?month=July&year=2026-27'
    # Need auth headers?
    print("This will fail without auth headers. I will just check views_gst.py again.")
except Exception as e:
    print(e)
