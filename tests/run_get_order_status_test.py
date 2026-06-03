import os
import sys
import django
import json

# Tambahkan project root ke sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'laundry_project.settings')

try:
    django.setup()
except Exception as e:
    print('DJANGO SETUP ERROR:', e)
    raise

from django.test import RequestFactory
from orders.views import get_order_status

rf = RequestFactory()

# Test GET
req_get = rf.get('/orders/get-order-status/')
res_get = get_order_status(req_get)
print('GET status:', res_get.status_code)
print('GET content:', res_get.content.decode())

# Test POST with JSON payload (unlinked wa_id)
payload = {'payload': {'from': '621234567890', 'body': 'status 123'}}
req_post = rf.post('/orders/get-order-status/', data=json.dumps(payload), content_type='application/json')
res_post = get_order_status(req_post)
print('POST status:', res_post.status_code)
print('POST content:', res_post.content.decode())
