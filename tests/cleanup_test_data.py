import os
import sys

# Setup Django
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'laundry_project.settings')

import django
django.setup()

from django.contrib.auth import get_user_model
from orders.models import Order
from services.models import Service

User = get_user_model()

USERNAME = 'testuser_wa'
WA_ID = 'WA_TEST_12345'
SERVICE_NAME = 'Test Service'

user = None
try:
    user = User.objects.filter(username=USERNAME).first()
    if not user:
        user = User.objects.filter(wa_id=WA_ID).first()

    if user:
        orders = list(Order.objects.filter(customer=user))
        print(f'Found user: {user.username} - deleting {len(orders)} order(s)')
        for o in orders:
            print('Deleting order id=', o.id)
            o.delete()
        user.delete()
        print('User deleted')
    else:
        print('Test user not found')

    svc = Service.objects.filter(name=SERVICE_NAME).first()
    if svc:
        linked_orders = Order.objects.filter(service=svc).count()
        if linked_orders == 0:
            svc.delete()
            print('Test service deleted')
        else:
            print(f'Test service found but still linked to {linked_orders} orders; not deleted')
    else:
        print('Test service not found')

except Exception as e:
    print('Error during cleanup:', e)
    raise
