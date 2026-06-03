import os
import sys
import django
import json

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
from django.contrib.auth import get_user_model

User = get_user_model()
rf = RequestFactory()

# ensure test user exists with phone
phone = '6282274186163'
user = User.objects.filter(phone=phone).first()
if not user:
    try:
        user = User.objects.create_user(username='sim_user_6282274186163', password='testpass')
        user.phone = phone
        user.save()
        print('Created test user:', user.username, user.phone)
    except Exception as e:
        print('Failed to create user:', e)
else:
    print('Found existing user:', user.username, user.phone)

print('Before linking, wa_id:', user.wa_id)

# Simulate LINK payload from WA session id
payload_link = {'payload': {'from': '13280206680099@lid', 'body': 'LINK 6282274186163'}}
req_link = rf.post('/order/get-order-status/', data=json.dumps(payload_link), content_type='application/json')
res_link = get_order_status(req_link)
print('LINK response status:', res_link.status_code)
print('LINK response content:', res_link.content.decode())

# Refresh and show wa_id
user.refresh_from_db()
print('After linking, wa_id:', user.wa_id)

# Clean up: remove wa_id for test user
user.wa_id = ''
user.save()
print('Cleaned up wa_id.')
