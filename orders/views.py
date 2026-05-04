import re
import json
import time
from decimal import Decimal
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.http import HttpResponse
from django.template.loader import get_template
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.conf import settings
from django.db.models import Sum, Count

import midtransclient
from xhtml2pdf import pisa

from services.models import Service
from .models import Order, LaundryItem, Promo
from django.contrib.auth import get_user_model
from django.db.models import Avg

User = get_user_model()

# ===============================
# 🔹 Helper Functions
# ===============================
def cleanup_cancelled_orders():
    """Hapus order yang statusnya 'cancelled' lebih dari 2 hari."""
    two_days_ago = timezone.now() - timedelta(days=2)
    Order.objects.filter(order_status='cancelled', created_at__lte=two_days_ago).delete()


def admin_required(user):
    """Hanya admin/staff yang bisa mengakses."""
    return user.is_staff


# ===============================
# 🔹 Views Pelanggan
# ===============================
from decimal import Decimal
from .models import Promo, Order
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
import time
from .models import Order, LaundryItem
from services.models import Service
from django.contrib.auth import get_user_model

User = get_user_model()

import requests

def get_address(lat, lng):
    url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json"
    try:
        r = requests.get(url, headers={'User-Agent': 'MyLaundryApp'})
        data = r.json()
        return data.get('display_name', '')
    except Exception as e:
        print("Geocoding error:", e)
        return f"Lat: {lat}, Lng: {lng}"


# from decimal import Decimal
# from .models import Promo, Order, OrderItem, LaundryItem
# import json

# @login_required
# def create_order(request):
#     services = Service.objects.all()
#     laundry_items = LaundryItem.objects.all()
#     customers = User.objects.all() if request.user.is_staff else None

#     if request.method == "POST":
#         print("=" * 50)
#         print("POST DATA RECEIVED:")
#         for key, value in request.POST.items():
#             print(f"{key}: {value}")
#         print("=" * 50)
        
#         # ===== Pilih customer =====
#         if request.user.is_staff:
#             customer_id = request.POST.get("customer")
#             if not customer_id:
#                 messages.error(request, "Pilih pelanggan terlebih dahulu.")
#                 return redirect("orders:order")
#             customer = get_object_or_404(User, id=customer_id)
#         else:
#             customer = request.user

#         # ===== Pilih service =====
#         service_id = request.POST.get("service")
#         if not service_id:
#             messages.error(request, "Pilih layanan terlebih dahulu.")
#             return redirect("orders:order")
#         service = get_object_or_404(Service, id=service_id)

#         # ===== Ambil data form =====
#         payment_method = request.POST.get("payment_method")
#         scheduled_pickup = request.POST.get("scheduled_pickup")
#         weight = request.POST.get("weight", None)
        
#         # ===== AMBIL DATA PICKUP DAN DELIVERY METHOD =====
#         pickup_method = request.POST.get("pickup_method", "pickup")
#         delivery_method = request.POST.get("delivery_method", "delivery")
#         total_shipping_cost = Decimal(request.POST.get("total_shipping_cost", 0) or 0)
        
#         # ===== Ambil shipping_cost dari input hidden (base ongkir) =====
#         base_shipping_cost = Decimal(request.POST.get("shipping_cost", 0) or 0)

#         # ===== Ambil lokasi pickup =====
#         latitude = request.POST.get("latitude")
#         longitude = request.POST.get("longitude")
#         pickup_address_input = request.POST.get("address")

#         if not latitude or not longitude:
#             messages.error(request, "Pilih lokasi pickup di peta terlebih dahulu!")
#             return redirect("orders:order")

#         lat = float(latitude)
#         lng = float(longitude)

#         # Prioritas: input user → fallback ke map
#         if pickup_address_input:
#             pickup_address = pickup_address_input
#         else:
#             pickup_address = get_address(lat, lng)

#         # ===== Ambil items jika per-item =====
#         service_ids = request.POST.getlist("service_id[]")
#         weights = request.POST.getlist("weight[]")
#         item_names = request.POST.getlist("item_name[]")
#         item_qtys = request.POST.getlist("item_qty[]")
        
#         # Process items data
#         items_data = []
#         for name, qty in zip(item_names, item_qtys):
#             if name and qty:
#                 items_data.append({
#                     "name": name,
#                     "quantity": int(qty)
#                 })
        
#         print(f"[DEBUG] Service type: {service.type}")
#         print(f"[DEBUG] Pickup Method: {pickup_method}")
#         print(f"[DEBUG] Delivery Method: {delivery_method}")
#         print(f"[DEBUG] Total Shipping Cost: {total_shipping_cost}")
#         print(f"[DEBUG] Service IDs: {service_ids}")
#         print(f"[DEBUG] Weights: {weights}")
#         print(f"[DEBUG] Item names: {item_names}")
#         print(f"[DEBUG] Item qtys: {item_qtys}")
#         print(f"[DEBUG] Items data: {items_data}")

#         # ===== Hitung total =====
#         total_price = Decimal(0)
        
#         # Data untuk disimpan ke OrderItem
#         order_items_to_create = []
        
#         # Hitung dari service_ids dan weights (untuk per_kilo)
#         for i, s_id in enumerate(service_ids):
#             try:
#                 srv = Service.objects.get(id=s_id)
#                 if srv.type == "per_kilo" and i < len(weights) and weights[i]:
#                     weight_val = Decimal(weights[i])
#                     item_subtotal = weight_val * srv.price
#                     total_price += item_subtotal
#                     print(f"[DEBUG] Added per_kilo: {weight_val} kg x {srv.price} = {item_subtotal}")
                    
#                     # Simpan ke OrderItem nanti
#                     order_items_to_create.append({
#                         'service': srv,
#                         'laundry_item': None,
#                         'quantity': None,
#                         'weight': weight_val,
#                         'price': srv.price,
#                         'subtotal': item_subtotal
#                     })
#             except Service.DoesNotExist:
#                 pass
        
#         # Hitung dari items (untuk per_item)
#         for item_data in items_data:
#             item_obj = LaundryItem.objects.filter(name=item_data["name"]).first()
#             if item_obj:
#                 item_price = Decimal(item_obj.price) * Decimal(item_data["quantity"])
#                 total_price += item_price
#                 print(f"[DEBUG] Item '{item_data['name']}' qty {item_data['quantity']}: +{item_price}")
                
#                 # Simpan ke OrderItem nanti
#                 order_items_to_create.append({
#                     'service': None,
#                     'laundry_item': item_obj,
#                     'quantity': item_data["quantity"],
#                     'weight': None,
#                     'price': item_obj.price,
#                     'subtotal': item_price
#                 })
        
#         # Tambahkan harga service itu sendiri jika per_item
#         if service.type == "per_item":
#             total_price += service.price
#             print(f"[DEBUG] Service price added: {service.price}")
            
#             # Simpan service sebagai OrderItem juga
#             order_items_to_create.append({
#                 'service': service,
#                 'laundry_item': None,
#                 'quantity': 1,
#                 'weight': None,
#                 'price': service.price,
#                 'subtotal': service.price
#             })
        
#         # ===== TAMBAHKAN TOTAL SHIPPING COST (sudah termasuk 1x atau 2x ongkir) =====
#         total_price += total_shipping_cost
        
#         print(f"[DEBUG] Total price before discount: {total_price}")
#         print(f"[DEBUG] Breakdown: Subtotal items: {total_price - total_shipping_cost}, Shipping: {total_shipping_cost}")
        
#         # Validasi total_price
#         if total_price <= 0:
#             messages.error(request, "Total harga harus lebih dari 0. Pastikan sudah memilih layanan dan item.")
#             return redirect("orders:order")

#         # ================= PROMO (USER PROMO) =================
#         selected_promo_id = request.POST.get("selected_promo")
        
#         discount_percent = None
#         discount_amount_value = Decimal(0)
#         total_price_after_discount = total_price
#         applied_promo = None

#         if selected_promo_id:
#             user_promo = UserPromo.objects.filter(
#                 user=customer,
#                 promo_id=selected_promo_id,
#                 is_used=False,
#                 promo__is_active=True,
#                 promo__min_transaction__lte=total_price
#             ).select_related("promo").first()

#             if user_promo:
#                 discount_amount_value = Decimal(user_promo.promo.discount_amount)
#                 total_price_after_discount = total_price - discount_amount_value

#                 applied_promo = user_promo

#                 # tandai promo sudah dipakai
#                 user_promo.is_used = True
#                 user_promo.save()
                
#                 print(f"[DEBUG] Promo applied: {user_promo.promo.title}, discount: {discount_amount_value}")
        
#         # ===== Simpan order dengan field baru =====
#         order = Order.objects.create(
#             customer=customer,
#             service=service,
#             weight=weight if weight else None,
#             price_total=total_price_after_discount,
#             discount_percent=discount_percent,
#             discount_amount=discount_amount_value,  # Simpan nominal diskon jika ada field
#             scheduled_pickup=scheduled_pickup,
#             payment_method=payment_method,
#             order_status="pending",
#             payment_status="unpaid",
#             latitude=latitude,
#             longitude=longitude,
#             pickup_address=pickup_address,
#             # Field baru untuk layanan antar-jemput
#             pickup_method=pickup_method,      # Simpan metode pengambilan (pickup/dropoff)
#             delivery_method=delivery_method,   # Simpan metode pengiriman (delivery/pickup)
#             shipping_cost=total_shipping_cost  # Simpan total ongkir (bisa 1x atau 2x)
#         )
        
#         # ===== Simpan OrderItems =====
#         for item_data in order_items_to_create:
#             OrderItem.objects.create(
#                 order=order,
#                 service=item_data['service'],
#                 laundry_item=item_data['laundry_item'],
#                 quantity=item_data['quantity'],
#                 weight=item_data['weight'],
#                 price=item_data['price'],
#                 subtotal=item_data['subtotal']
#             )
        
#         print(f"[DEBUG] Order created with ID: {order.id}")
#         print(f"[DEBUG] Total OrderItems created: {len(order_items_to_create)}")
#         print(f"[DEBUG] Final price: {total_price_after_discount}")
#         print(f"[DEBUG] Pickup method: {pickup_method}, Delivery method: {delivery_method}")

#         # ===== Midtrans jika QRIS =====
#         if payment_method == "qris":
#             import midtransclient
#             from django.conf import settings
#             import time

#             snap = midtransclient.Snap(
#                 is_production=settings.MIDTRANS["IS_PRODUCTION"],
#                 server_key=settings.MIDTRANS["SERVER_KEY"]
#             )
#             unique_order_id = f"ORDER-{order.id}-{int(time.time())}"
#             finish_url = request.build_absolute_uri(reverse("orders:payment_success"))

#             transaction_params = {
#                 "transaction_details": {
#                     "order_id": unique_order_id,
#                     "gross_amount": int(total_price_after_discount),
#                 },
#                 "customer_details": {
#                     "first_name": customer.username,
#                     "phone": customer.phone,
#                 },
#                 "enabled_payments": ["gopay", "qris", "bank_transfer"],
#                 "callbacks": {"finish": finish_url},
#             }

#             try:
#                 transaction = snap.create_transaction(transaction_params)
#                 snap_token = transaction.get("token")
#                 order.snap_token = snap_token
#                 order.transaction_id = unique_order_id
#                 order.save()
#                 return redirect("orders:payment", order_id=order.id)
#             except Exception as e:
#                 messages.error(request, f"Gagal membuat transaksi Midtrans: {e}")
#                 return redirect("orders:order")

#         messages.success(request, f"Pesanan #{order.id} berhasil dibuat.")
#         return redirect("orders:order_list")

#     # ===== Ambil promo yang tersedia untuk user =====
#     available_promos = UserPromo.objects.filter(
#         user=request.user,
#         is_used=False,
#         promo__is_active=True
#     ).select_related("promo")

#     return render(request, "orders/order.html", {
#         "services": services,
#         "laundry_items": laundry_items,
#         "customers": customers,
#         "available_promos": available_promos
#     })

from decimal import Decimal
from .models import Promo, Order, OrderItem, LaundryItem
import json

@login_required
def create_order(request):
    services = Service.objects.all()
    laundry_items = LaundryItem.objects.all()
    customers = User.objects.all() if request.user.is_staff else None

    if request.method == "POST":
        print("=" * 50)
        print("POST DATA RECEIVED:")
        for key, value in request.POST.items():
            print(f"{key}: {value}")
        print("=" * 50)
        
        # ===== Pilih customer =====
        if request.user.is_staff:
            customer_id = request.POST.get("customer")
            if not customer_id:
                messages.error(request, "Pilih pelanggan terlebih dahulu.")
                return redirect("orders:order")
            customer = get_object_or_404(User, id=customer_id)
        else:
            customer = request.user

        # ===== Pilih service =====
        service_id = request.POST.get("service")
        if not service_id:
            messages.error(request, "Pilih layanan terlebih dahulu.")
            return redirect("orders:order")
        service = get_object_or_404(Service, id=service_id)

        # ===== Ambil data form =====
        payment_method = request.POST.get("payment_method")
        scheduled_pickup = request.POST.get("scheduled_pickup")
        
        # AMBIL pickup_method dan delivery_method
        pickup_method = request.POST.get("pickup_method", "pickup")
        delivery_method = request.POST.get("delivery_method", "delivery")
        total_shipping_cost = Decimal(request.POST.get("total_shipping_cost", 0) or 0)
        base_shipping_cost = Decimal(request.POST.get("shipping_cost", 0) or 0)

        # ===== Ambil lokasi pickup =====
        latitude = request.POST.get("latitude")
        longitude = request.POST.get("longitude")
        pickup_address_input = request.POST.get("address")

        if not latitude or not longitude:
            messages.error(request, "Pilih lokasi pickup di peta terlebih dahulu!")
            return redirect("orders:order")

        lat = float(latitude)
        lng = float(longitude)

        if pickup_address_input:
            pickup_address = pickup_address_input
        else:
            pickup_address = get_address(lat, lng)

        # ===== Ambil items =====
        service_ids = request.POST.getlist("service_id[]")
        weights = request.POST.getlist("weight[]")
        item_names = request.POST.getlist("item_name[]")
        item_qtys = request.POST.getlist("item_qty[]")
        
        # Process items data
        items_data = []
        for name, qty in zip(item_names, item_qtys):
            if name and qty:
                items_data.append({
                    "name": name,
                    "quantity": int(qty)
                })
        
        print(f"[DEBUG] Service type: {service.type}")
        print(f"[DEBUG] Service IDs: {service_ids}")
        print(f"[DEBUG] Weights: {weights}")

        # ===== Hitung total =====
        total_price = Decimal(0)
        total_weight = Decimal(0)  # ← PERBAIKAN: hitung total berat
        order_items_to_create = []
        
        # ===== 1. Hitung dari service_ids (multiple per_kilo) =====
        for i, s_id in enumerate(service_ids):
            try:
                srv = Service.objects.get(id=s_id)
                if srv.type == "per_kilo" and i < len(weights) and weights[i]:
                    weight_val = Decimal(weights[i])
                    item_subtotal = weight_val * srv.price
                    total_price += item_subtotal
                    total_weight += weight_val  # ← PERBAIKAN: tambah ke total berat
                    
                    order_items_to_create.append({
                        'service': srv,
                        'laundry_item': None,
                        'quantity': None,
                        'weight': weight_val,
                        'price': srv.price,
                        'subtotal': item_subtotal
                    })
            except Service.DoesNotExist:
                pass
        
        # ===== 2. Hitung dari items (per_item) =====
        for item_data in items_data:
            item_obj = LaundryItem.objects.filter(name=item_data["name"]).first()
            if item_obj:
                item_price = Decimal(item_obj.price) * Decimal(item_data["quantity"])
                total_price += item_price
                
                order_items_to_create.append({
                    'service': None,
                    'laundry_item': item_obj,
                    'quantity': item_data["quantity"],
                    'weight': None,
                    'price': item_obj.price,
                    'subtotal': item_price
                })
        
        # ===== 3. Tambahkan harga service itu sendiri jika per_item =====
        if service.type == "per_item":
            total_price += service.price
            
            order_items_to_create.append({
                'service': service,
                'laundry_item': None,
                'quantity': 1,
                'weight': None,
                'price': service.price,
                'subtotal': service.price
            })
        
        # ===== 4. PERBAIKAN: Jika single service per_kilo tanpa items =====
        if service.type == "per_kilo" and not service_ids and not items_data:
            # Ambil berat dari input weight (single input)
            single_weight = request.POST.get("weight", None)
            if single_weight:
                weight_val = Decimal(single_weight)
                item_subtotal = weight_val * service.price
                total_price += item_subtotal
                total_weight += weight_val
                
                order_items_to_create.append({
                    'service': service,
                    'laundry_item': None,
                    'quantity': None,
                    'weight': weight_val,
                    'price': service.price,
                    'subtotal': item_subtotal
                })
        
        # ===== Tambahkan shipping cost =====
        total_price += total_shipping_cost
        
        print(f"[DEBUG] Total price: {total_price}, Total weight: {total_weight}")
        
        # Validasi
        if total_price <= 0:
            messages.error(request, "Total harga harus lebih dari 0.")
            return redirect("orders:order")

        # ===== PROMO =====
        selected_promo_id = request.POST.get("selected_promo")
        discount_percent = None
        discount_amount_value = Decimal(0)
        total_price_after_discount = total_price

        if selected_promo_id:
            user_promo = UserPromo.objects.filter(
                user=customer,
                promo_id=selected_promo_id,
                is_used=False,
                promo__is_active=True,
                promo__min_transaction__lte=total_price
            ).select_related("promo").first()

            if user_promo:
                discount_amount_value = Decimal(user_promo.promo.discount_amount)
                total_price_after_discount = total_price - discount_amount_value
                user_promo.is_used = True
                user_promo.save()

        # ===== PERBAIKAN: Simpan order dengan total_weight =====
        order = Order.objects.create(
            customer=customer,
            service=service,
            weight=total_weight if total_weight > 0 else None,  # ← PERBAIKAN
            price_total=total_price_after_discount,
            discount_percent=discount_percent,
            discount_amount=discount_amount_value,
            scheduled_pickup=scheduled_pickup,
            payment_method=payment_method,
            order_status="pending",
            payment_status="unpaid",
            latitude=latitude,
            longitude=longitude,
            pickup_address=pickup_address,
            pickup_method=pickup_method,
            delivery_method=delivery_method,
            shipping_cost=total_shipping_cost
        )
        
        # ===== Simpan OrderItems =====
        for item_data in order_items_to_create:
            OrderItem.objects.create(
                order=order,
                service=item_data['service'],
                laundry_item=item_data['laundry_item'],
                quantity=item_data['quantity'],
                weight=item_data['weight'],  # ← PASTIKAN WEIGHT TERSIMPAN
                price=item_data['price'],
                subtotal=item_data['subtotal']
            )
        
        print(f"[DEBUG] Order created: #{order.id}, Total weight: {order.weight}")

        # ===== Midtrans jika QRIS =====
        if payment_method == "qris":
            import midtransclient
            from django.conf import settings
            import time

            snap = midtransclient.Snap(
                is_production=settings.MIDTRANS["IS_PRODUCTION"],
                server_key=settings.MIDTRANS["SERVER_KEY"]
            )
            unique_order_id = f"ORDER-{order.id}-{int(time.time())}"
            finish_url = request.build_absolute_uri(reverse("orders:payment_success"))

            transaction_params = {
                "transaction_details": {
                    "order_id": unique_order_id,
                    "gross_amount": int(total_price_after_discount),
                },
                "customer_details": {
                    "first_name": customer.username,
                    "phone": customer.phone,
                },
                "enabled_payments": ["gopay", "qris", "bank_transfer"],
                "callbacks": {"finish": finish_url},
            }

            try:
                transaction = snap.create_transaction(transaction_params)
                snap_token = transaction.get("token")
                order.snap_token = snap_token
                order.transaction_id = unique_order_id
                order.save()
                return redirect("orders:payment", order_id=order.id)
            except Exception as e:
                messages.error(request, f"Gagal membuat transaksi Midtrans: {e}")
                return redirect("orders:order")

        messages.success(request, f"Pesanan #{order.id} berhasil dibuat.")
        return redirect("orders:order_list")

    # ===== GET request =====
    available_promos = UserPromo.objects.filter(
        user=request.user,
        is_used=False,
        promo__is_active=True
    ).select_related("promo")

    return render(request, "orders/order.html", {
        "services": services,
        "laundry_items": laundry_items,
        "customers": customers,
        "available_promos": available_promos
    })

@login_required
def payment(request, order_id):
    """Halaman pembayaran untuk order"""
    # Admin bisa melihat semua pesanan, customer hanya pesanannya sendiri
    if request.user.is_staff:
        order = get_object_or_404(Order, id=order_id)
    else:
        order = get_object_or_404(Order, id=order_id, customer=request.user)
    
    # Pastikan order status masih pending
    if order.order_status != 'pending':
        messages.error(request, "Order ini sudah diproses atau dibayar.")
        return redirect('orders:order_list')
    
    # Pastikan snap_token ada
    if not order.snap_token:
        messages.error(request, "Token pembayaran tidak ditemukan.")
        return redirect('orders:order_list')
    
    context = {
        'order': order,
        'snap_token': order.snap_token,
        'client_key': settings.MIDTRANS.get('CLIENT_KEY', ''),
    }
    
    return render(request, 'orders/payment.html', context)

@login_required
def payment_success(request):
    """Redirect setelah pembayaran Midtrans selesai"""
    midtrans_order_id = request.GET.get("order_id")
    transaction_status = request.GET.get("transaction_status")

    if midtrans_order_id and transaction_status:
        try:
            real_id = int(midtrans_order_id.split("-")[1])
            order = Order.objects.get(id=real_id)
            if transaction_status in ["capture", "settlement"]:
                order.payment_status = "paid"
                order.save()
                messages.success(request, f"✅ Pembayaran untuk pesanan #{order.id} berhasil!")
            elif transaction_status in ["cancel", "deny", "expire"]:
                order.payment_status = "unpaid"
                messages.warning(request, f"⚠️ Pembayaran untuk pesanan #{order.id} gagal/dibatalkan.")
            else:
                order.payment_status = transaction_status
                order.save()
        except Exception as e:
            print("Payment success update error:", e)
            messages.error(request, "Terjadi kesalahan saat memproses pembayaran.")
    else:
        messages.info(request, "Menunggu konfirmasi pembayaran.")

    return redirect("orders:order_list")

@csrf_exempt
def callback_midtrans(request):
    """Webhook Midtrans untuk update status pembayaran"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            order_id = data.get("order_id")
            transaction_status = data.get("transaction_status")
            if order_id:
                real_id = int(order_id.split("-")[1])
                order = Order.objects.get(id=real_id)
                if transaction_status in ["capture", "settlement"]:
                    order.payment_status = "paid"
                    order.save()

                elif transaction_status in ["cancel", "deny", "expire"]:
                    order.payment_status = "unpaid"
                else:
                    order.payment_status = transaction_status
                order.save()
            return HttpResponse("OK")
        except Exception as e:
            print("Callback error:", e)
            return HttpResponse("Error", status=500)
    return HttpResponse("Invalid method", status=405)


@login_required
def order_list(request):
    """Menampilkan daftar pesanan user dengan pagination."""
    # Ambil semua order milik user
    orders_query = Order.objects.filter(customer=request.user).order_by('-created_at')

    # Statistik
    total_orders = orders_query.count()
    success_orders = orders_query.filter(order_status='delivered').count()
    pending_orders = orders_query.filter(order_status='pending').count()
    cancelled_orders = orders_query.filter(order_status='cancelled').count()

    # Total transaksi yang sudah dibayar
    total_paid_value = orders_query.filter(
        payment_status__in=['paid', 'settlement']
    ).aggregate(total=Sum('price_total'))['total'] or 0

    # Layanan yang sering digunakan
    frequent_services = (
        orders_query.values('service')
        .annotate(count=Count('service'))
        .order_by('-count')[:5]
    )

    # Ambil objek Service lengkap
    for fs in frequent_services:
        fs['service'] = Service.objects.get(pk=fs['service'])

    # Pagination
    paginator = Paginator(orders_query, 10)
    page_number = request.GET.get('page')
    orders = paginator.get_page(page_number)

    context = {
        'orders': orders,
        'total_orders': total_orders,
        'success_orders': success_orders,
        'pending_orders': pending_orders,
        'cancelled_orders': cancelled_orders,
        'total_paid_value': total_paid_value,
        'frequent_services': frequent_services,
    }

    return render(request, 'orders/order_list.html', context)


@login_required
def cancel_order(request, order_id):
    """User membatalkan pesanan"""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    if order.order_status == 'pending' and order.payment_status in ['unpaid', 'pending']:
        order.order_status = 'cancelled'
        order.save()
        messages.success(request, "Pesanan berhasil dibatalkan.")
    else:
        messages.error(request, "Pesanan tidak bisa dibatalkan.")
    return redirect('orders:order_list')


# ===============================
# 🔹 Views Admin
# ===============================
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from orders.models import Order

@login_required
@user_passes_test(admin_required)
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Simpan halaman saat ini untuk redirect kembali
    current_page = request.GET.get('orders_page', 1)
    
    if request.method == "POST":
        new_status = request.POST.get("order_status")
        if new_status in dict(Order.ORDER_STATUS_CHOICES):
            order.order_status = new_status
            order.save()

            trigger_n8n_webhook(order, "order_status_updated")

            messages.success(request, f"Status pesanan #{order.id} diperbarui menjadi {order.get_order_status_display()}.")
        else:
            messages.error(request, "Status yang dipilih tidak valid.")
            
    
    # Redirect ke dashboard dengan parameter tab=orders dan halaman yang sama
    return redirect(f"{reverse('accounts:admin_dashboard')}?tab=orders&orders_page={current_page}")

@login_required
@user_passes_test(admin_required)
def update_payment_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    current_page = request.GET.get('orders_page', 1)

    if request.method == "POST":
        new_status = request.POST.get("payment_status")

        if new_status in dict(Order.PAYMENT_STATUS_CHOICES):
            old_status = order.payment_status  # simpan status lama
            order.payment_status = new_status
            order.save()

            trigger_n8n_webhook(order, "payment_status_updated")

            messages.success(
                request,
                f"Status pembayaran pesanan #{order.id} diperbarui menjadi {order.get_payment_status_display()}."
            )

    return redirect(f"{reverse('accounts:admin_dashboard')}?tab=orders&orders_page={current_page}")

from decimal import Decimal
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from .models import Order, OrderItem

@login_required
@user_passes_test(lambda u: u.is_staff)
def update_order_weight(request, order_id):
    """Admin mengubah berat laundry pesanan"""
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == "POST":
        new_weight = request.POST.get('new_weight')
        
        if new_weight:
            try:
                new_weight = Decimal(new_weight)
                
                # Validasi berat
                if new_weight < 0.1:
                    messages.error(request, "❌ Berat minimal 0.1 kg")
                    return redirect(request.META.get('HTTP_REFERER', reverse('accounts:admin_dashboard')))
                elif new_weight > 50:
                    messages.error(request, "❌ Berat maksimal 50 kg")
                    return redirect(request.META.get('HTTP_REFERER', reverse('accounts:admin_dashboard')))
                
                # Simpan berat lama untuk notifikasi
                old_weight = order.weight or Decimal(0)
                
                # ===== UPDATE BERAT DI ORDER =====
                order.weight = new_weight
                
                # ===== UPDATE TOTAL HARGA =====
                # Cek apakah order memiliki layanan per_kilo
                order_items_kilo = order.order_items.filter(service__type='per_kilo')
                
                if order_items_kilo.exists():
                    # Hitung ulang total dari semua OrderItem
                    total_price = Decimal(0)
                    
                    for item in order_items_kilo:
                        # Update berat dan subtotal untuk item kilo
                        item.weight = new_weight
                        item.subtotal = new_weight * item.price
                        item.save()
                        total_price += item.subtotal
                    
                    # Tambahkan subtotal dari item satuan (laundry_item)
                    order_items_satuan = order.order_items.filter(laundry_item__isnull=False)
                    for item in order_items_satuan:
                        total_price += item.subtotal
                    
                    # Tambahkan service price jika ada service per_item
                    service_items = order.order_items.filter(service__type='per_item', laundry_item__isnull=True)
                    for item in service_items:
                        total_price += item.subtotal
                    
                    # Update total harga order
                    order.price_total = total_price
                    
                elif order.service and order.service.type == 'per_kilo':
                    # Jika hanya single service per_kilo tanpa OrderItem
                    order.price_total = new_weight * order.service.price
                
                order.save()
                
                messages.success(
                    request, 
                    f"✅ Berat pesanan #{order.id} berhasil diubah dari {old_weight} kg menjadi {new_weight} kg. Total harga telah diperbarui."
                )
                
            except (ValueError, TypeError) as e:
                messages.error(request, f"❌ Format berat tidak valid: {str(e)}")
        else:
            messages.error(request, "❌ Masukkan berat yang valid")
    
    # Redirect kembali ke halaman sebelumnya
    next_url = request.GET.get('next', f"{reverse('accounts:admin_dashboard')}?tab=orders&orders_page={request.GET.get('orders_page', 1)}")
    return redirect(next_url)

@login_required
@user_passes_test(lambda u: u.is_staff)
def update_order_item_weight(request, item_id):
    """Admin mengubah berat laundry pada OrderItem"""
    from decimal import Decimal
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages
    from django.urls import reverse
    from .models import OrderItem, Order
    
    item = get_object_or_404(OrderItem, id=item_id)
    order = item.order
    
    if request.method == "POST":
        new_weight = request.POST.get('new_weight')
        
        if new_weight:
            try:
                new_weight = Decimal(new_weight)
                
                if new_weight < 0.1:
                    messages.error(request, "❌ Berat minimal 0.1 kg")
                elif new_weight > 50:
                    messages.error(request, "❌ Berat maksimal 50 kg")
                else:
                    old_weight = item.weight or Decimal(0)
                    item.weight = new_weight
                    item.subtotal = new_weight * item.price
                    item.save()
                    
                    # Update total harga order
                    total_price = Decimal(0)
                    for i in order.order_items.all():
                        total_price += i.subtotal
                    total_price += order.shipping_cost or 0
                    
                    # Apply discount jika ada
                    if order.discount_amount:
                        total_price -= order.discount_amount
                    
                    order.price_total = total_price
                    order.weight = new_weight
                    order.save()
                    
                    messages.success(request, f"✅ Berat pesanan #{order.id} berhasil diubah dari {old_weight} kg menjadi {new_weight} kg")
                    
            except (ValueError, TypeError):
                messages.error(request, "❌ Format berat tidak valid")
        else:
            messages.error(request, "❌ Masukkan berat yang valid")
    
    next_url = request.GET.get('next', f"{reverse('accounts:admin_dashboard')}?tab=orders&orders_page={request.GET.get('orders_page', 1)}")
    return redirect(next_url)

@login_required
@user_passes_test(admin_required)
def assign_courier(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Simpan halaman saat ini untuk redirect kembali
    current_page = request.GET.get('orders_page', 1)
    
    if request.method == "POST":
        courier_id = request.POST.get("courier")
        if not courier_id:
            order.assigned_courier = None
            order.save()
            trigger_n8n_webhook(order, "courier_removed")
            messages.info(request, f"Kurir untuk pesanan #{order.id} telah dihapus.")
        else:
            try:
                courier = User.objects.get(id=courier_id, is_courier=True)
                order.assigned_courier = courier
                order.save()
                trigger_n8n_webhook(order, "courier_assigned")

                messages.success(request, f"Kurir '{courier.username}' telah ditugaskan ke pesanan #{order.id}.")
            except User.DoesNotExist:
                messages.error(request, "Kurir yang dipilih tidak valid.")
    
    # Redirect ke dashboard dengan parameter tab=orders dan halaman yang sama
    return redirect(f"{reverse('accounts:admin_dashboard')}?tab=orders&orders_page={current_page}")

@login_required
@user_passes_test(admin_required)
def delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Simpan halaman saat ini untuk redirect kembali
    current_page = request.GET.get('orders_page', 1)
    
    if request.method == "POST":
        order.delete()
        messages.success(request, f"Pesanan #{order.id} berhasil dihapus.")
    
    # Redirect ke dashboard dengan parameter tab=orders dan halaman yang sama
    return redirect(f"{reverse('accounts:admin_dashboard')}?tab=orders&orders_page={current_page}")


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .models import Promo, UserPromo
from .forms import AssignPromoForm, PromoForm
from django.contrib.auth import get_user_model

User = get_user_model()

@staff_member_required
def assign_promo(request):
    promos = Promo.objects.filter(is_active=True).order_by('-created_at')
    user_promos = UserPromo.objects.select_related('user', 'promo').order_by('-assigned_at')

    if request.method == 'POST':
        form = AssignPromoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('orders:promo_assign')
    else:
        form = AssignPromoForm()

    return render(request, 'orders/assign_promo.html', {
        'form': form,
        'promos': promos,
        'user_promos': user_promos
    })


@staff_member_required
def add_promo(request):
    if request.method == 'POST':
        form = PromoForm(request.POST, request.FILES)
        if form.is_valid():
            promo = form.save()
            messages.success(request, f"Promo '{promo.title}' berhasil ditambahkan")
            return redirect('orders:promo_assign')
    else:
        form = PromoForm()
    
    return render(request, 'orders/promo_add.html', {'form': form})


@staff_member_required
def edit_promo(request, promo_id):
    promo = get_object_or_404(Promo, id=promo_id)
    
    if request.method == 'POST':
        form = PromoForm(request.POST, request.FILES, instance=promo)
        if form.is_valid():
            form.save()
            messages.success(request, f"Promo '{promo.title}' berhasil diperbarui")
            return redirect('orders:promo_assign')
    else:
        form = PromoForm(instance=promo)
    
    return render(request, 'orders/promo_edit.html', {'form': form, 'promo': promo})

@staff_member_required
def delete_promo(request, promo_id):
    """Hapus promo - langsung redirect tanpa template"""
    promo = get_object_or_404(Promo, id=promo_id)
    promo_title = promo.title
    
    if request.method == 'POST':
        # Hapus juga UserPromo yang terkait
        UserPromo.objects.filter(promo=promo).delete()
        if promo.image:
            promo.image.delete(save=False)
        promo.delete()
        messages.success(request, f"Promo '{promo_title}' berhasil dihapus")
        return redirect('orders:promo_assign')
    
    # Jika bukan POST, redirect ke halaman assign (tidak pakai template konfirmasi)
    return redirect('orders:promo_assign')


@staff_member_required
def user_promo_delete(request, pk):
    """Hapus user promo - langsung redirect tanpa template"""
    user_promo = get_object_or_404(UserPromo, id=pk)
    user_name = user_promo.user.username
    promo_title = user_promo.promo.title
    
    if request.method == 'POST':
        user_promo.delete()
        messages.success(request, f"Promo '{promo_title}' untuk {user_name} berhasil dihapus")
        return redirect('orders:promo_assign')
    
    # Jika bukan POST, redirect ke halaman assign (tidak pakai template konfirmasi)
    return redirect('orders:promo_assign')


# ===============================
# 🔹 Manajemen Laundry Item
# ===============================
@login_required
@user_passes_test(admin_required)
def add_laundry_item(request):
    if request.method == "POST":
        name = request.POST.get("name")
        price = request.POST.get("price")
        image = request.FILES.get('image')
        if name and price:
            LaundryItem.objects.create(name=name, price=price, image=image)
            messages.success(request, f"Item '{name}' berhasil ditambahkan.")
            return redirect('orders:add_laundry_item')

    laundry_items = LaundryItem.objects.all()
    return render(request, "orders/add_laundry_item.html", {"laundry_items": laundry_items})

@login_required
def edit_laundry_item(request, item_id):
    item = get_object_or_404(LaundryItem, id=item_id)

    if request.method == 'POST':
        item.name = request.POST['name']
        item.price = request.POST['price']
        if 'image' in request.FILES:
            item.image = request.FILES['image']
        item.save()
        messages.success(request, f"Item '{item.name}' berhasil diperbarui.")
        return redirect('orders:add_laundry_item')

    return render(request, 'orders/edit_laundry_item.html', {'item': item})


@login_required
@user_passes_test(admin_required)
def delete_laundry_item(request, item_id):
    item = get_object_or_404(LaundryItem, id=item_id)
    item.delete()
    messages.success(request, f"Item '{item.name}' berhasil dihapus.")
    return redirect('orders:add_laundry_item')


# ===============================
# 🔹 Invoice / Nota
# ===============================
@login_required
def order_invoice(request, order_id):
    """Tampilkan invoice setelah pembayaran"""
    order = get_object_or_404(Order, id=order_id)
    if not request.user.is_staff:
        order = get_object_or_404(Order, id=order_id, customer=request.user)

    if order.payment_status not in ["paid", "settlement"]:
        messages.error(request, "Pesanan belum dibayar, nota belum tersedia.")
        return redirect("orders:order_list")

    return render(request, "orders/order_invoice.html", {"order": order})


@login_required
def download_invoice(request, order_id):
    """Download invoice sebagai PDF"""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    template_path = 'orders/order_invoice.html'
    context = {'order': order}

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.pdf"'

    template = get_template(template_path)
    html = template.render(context)

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Terjadi kesalahan saat membuat PDF <pre>' + html + '</pre>')

    return response


from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .models import Order

@login_required
def get_order_notifications(request):
    count = Order.objects.filter(customer=request.user, notified_customer=False).count()
    return JsonResponse({'count': count})

@csrf_exempt  # sementara, untuk menghindari error CSRF saat fetch
@login_required
def mark_notifications_as_read(request):
    if request.method == 'POST':
        updated = Order.objects.filter(customer=request.user, notified_customer=False).update(notified_customer=True)
        return JsonResponse({'status': 'ok', 'updated': updated})
    return JsonResponse({'error': 'Invalid request'}, status=400)


from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from .models import Order
import json
import re

User = get_user_model()

@csrf_exempt
def get_order_status(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            message = data.get("message", "").lower().strip()
            phone = data.get("phone", "")

            phone = phone.replace("@c.us", "").replace("@lid", "")

            user = User.objects.filter(username=phone).first()

            match = re.search(r"\d+", message)

            # =========================
            # CASE 1: ADA ORDER ID
            # =========================
            if match:
                order_id = int(match.group())
                order = Order.objects.filter(id=order_id).select_related("customer", "service").first()

                if order:
                    return JsonResponse({
                        "reply": (
                            f"📦 *Status Order #{order.id}*\n"
                            f"Halo Kak {order.customer.username} 😊\n"
                            f"🧺 Layanan: {order.service.name if order.service else '-'}\n"
                            f"💰 Total: Rp{order.price_total:,.0f}\n"
                            f"🚚 Status: {order.get_order_status_display()}\n"
                            f"💵 Pembayaran: {order.get_payment_status_display()}\n"
                            f"📅 Tanggal: {order.created_at.strftime('%d-%m-%Y %H:%M')}"
                        ),
                        "status": "success"
                    })
                else:
                    return JsonResponse({
                        "reply": f"Maaf kak, order #{order_id} tidak ditemukan 🥺",
                        "status": "not_found"
                    })

            # =========================
            # CASE 2: CHAT BIASA
            # =========================
            name = user.username if user else "kak"

            return JsonResponse({
                "reply": f"Halo {name} 😊 Ada yang bisa dibantu?",
                "status": "greeting"
            })

        except Exception as e:
            return JsonResponse({
                "reply": f"Terjadi error: {str(e)}",
                "status": "error"
            }, status=500)

    return JsonResponse({"error": "Gunakan POST method"}, status=405)

    
# import requests

# def trigger_n8n_webhook(order, event_type):
#     webhook_url = "https://subcorymbosely-nonmythologic-marcelina.ngrok-free.dev/webhook/order-update"

#     # =========================
#     # DATA CUSTOMER
#     # =========================
#     customer_payload = {
#         "event": event_type,
#         "target": "customer",
#         "order_id": order.id,
#         "user": order.customer.username if order.customer else None,
#         "phone": order.customer.username if order.customer else None,
#         "order_status": order.get_order_status_display(),
#         "payment_status": order.get_payment_status_display(),
#         "courier": order.assigned_courier.username if order.assigned_courier else None,
#     }

#     try:
#         requests.post(webhook_url, json=customer_payload, timeout=5)
#     except:
#         pass

#     # =========================
#     # DATA COURIER (JIKA ADA)
#     # =========================
#     if order.assigned_courier:
#         courier_payload = {
#             "event": event_type,
#             "target": "courier",
#             "order_id": order.id,
#             "user": order.assigned_courier.username,
#             "phone": order.assigned_courier.username,
#             "customer_name": order.customer.username if order.customer else None,
#             "order_status": order.get_order_status_display(),
#         }

#         try:
#             requests.post(webhook_url, json=courier_payload, timeout=5)
#         except:
#             pass

import requests

def format_phone(phone):
    if not phone:
        return None
    if phone.startswith("08"):
        return "628" + phone[2:]
    if phone.startswith("+62"):
        return phone[1:]
    return phone

def trigger_n8n_webhook(order, event_type):
    webhook_url = "https://subcorymbosely-nonmythologic-marcelina.ngrok-free.dev/webhook/order-update"

    # =========================
    # CUSTOMER
    # =========================
    customer_phone = format_phone(order.customer.phone) if order.customer else None

    customer_payload = {
        "event": event_type,
        "target": "customer",
        "order_id": order.id,
        "user": order.customer.username if order.customer else None,
        "phone": customer_phone,
        "order_status": order.get_order_status_display(),
        "payment_status": order.get_payment_status_display(),
        "courier": order.assigned_courier.username if order.assigned_courier else None,
    }

    try:
        requests.post(webhook_url, json=customer_payload, timeout=5)
    except:
        pass

    # =========================
    # COURIER
    # =========================
    if order.assigned_courier:
        courier_phone = format_phone(order.assigned_courier.phone)

        courier_payload = {
            "event": event_type,
            "target": "courier",
            "order_id": order.id,
            "user": order.assigned_courier.username,
            "phone": courier_phone,
            "customer_name": order.customer.username if order.customer else None,
            "customer_phone": order.customer.phone if order.customer else None,
            "order_status": order.get_order_status_display(),
            "pickup_address": order.pickup_address if order.pickup_address else None,
            "customer_address": order.customer.address if order.customer and order.customer.address else None,
            "latitude": order.latitude,
            "longitude": order.longitude, 
        }

        try:
            requests.post(webhook_url, json=courier_payload, timeout=5)
        except:
            pass