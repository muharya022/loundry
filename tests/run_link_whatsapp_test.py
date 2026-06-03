import os
import sys
import django
import json

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'laundry_project.settings')

django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from orders.models import Order

User = get_user_model()
rf = RequestFactory()

# Ensure there's a user with the phone we'll link
phone = '628222333444'
username = 'linktestuser'
user, created = User.objects.get_or_create(username=username, defaults={'phone': phone, 'is_active': True})
if created:
    user.set_password('password')
    user.save()

from accounts.views import link_whatsapp

payload = {'payload': {'from': 'WAID12345', 'body': 'LINK 628222333444'}}
req = rf.post('/accounts/link-whatsapp/', data=json.dumps(payload), content_type='application/json')
resp = link_whatsapp(req)
print('Status:', resp.status_code)
print('Content:', resp.content.decode())
