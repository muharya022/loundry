import os
import sys
import django
import json
from decimal import Decimal
from django.utils import timezone

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
from django.contrib.auth import get_user_model
from services.models import Service
from orders.models import Order

User = get_user_model()
rf = RequestFactory()

# Buat user test
phone = '628111222333'
wa_id = 'WA_TEST_12345'
username = 'testuser_wa'

user, created = User.objects.get_or_create(username=username, defaults={
    'phone': phone,
    'is_active': True,
})
if created:
    user.set_password('password123')
    user.wa_id = wa_id
    user.save()
else:
    user.wa_id = wa_id
    user.phone = phone
    user.save()

print('User:', user.username, 'wa_id=', user.wa_id)

# Buat service jika belum ada
service, _ = Service.objects.get_or_create(name='Test Service', defaults={'price': Decimal('10000.00'), 'type': 'per_kilo'})

# Buat order
order = Order.objects.create(
    customer=user,
    service=service,
    price_total=Decimal('15000.00'),
    discount_amount=Decimal('0'),
    pickup_address='Jl. Test No.1',
    latitude=0.0,
    longitude=0.0,
    scheduled_pickup=timezone.now(),
    shipping_cost=Decimal('0.00'),
    weight=Decimal('1.0'),
    order_status='processing',
    payment_status='unpaid',
)

print('Created order id=', order.id)

# Panggil get_order_status dengan payload yang sesuai
from orders.views import get_order_status

payload = {'payload': {'from': wa_id, 'body': f'Status {order.id}'}}
req_post = rf.post('/orders/get-order-status/', data=json.dumps(payload), content_type='application/json')
res_post = get_order_status(req_post)
print('POST status:', res_post.status_code)
print('POST content:', res_post.content.decode())
