import re
import json
import time
from decimal import Decimal
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.http import HttpResponse
from django.template.loader import get_template
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.conf import settings

import midtransclient
from xhtml2pdf import pisa

from services.models import Service
from .models import Order, LaundryItem
from django.contrib.auth import get_user_model

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
from .models import Discount, Order
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
        return data.get('display_name', '')  # alamat lengkap
    except Exception as e:
        print("Geocoding error:", e)
        return f"Lat: {lat}, Lng: {lng}"  # fallback


from decimal import Decimal
from .models import Discount, Order  # pastikan import Discount

@login_required
def create_order(request):
    services = Service.objects.all()
    laundry_items = LaundryItem.objects.all()
    customers = User.objects.all() if request.user.is_staff else None

    if request.method == "POST":
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
        weight = request.POST.get("weight", None)

        # ===== Ambil lokasi pickup =====
        latitude = request.POST.get("latitude")
        longitude = request.POST.get("longitude")
        if not latitude or not longitude:
            messages.error(request, "Pilih lokasi pickup di peta terlebih dahulu!")
            return redirect("orders:order")
        lat = float(latitude)
        lng = float(longitude)
        pickup_address = get_address(lat, lng)

        # ===== Ambil items jika per-item =====
        item_names = request.POST.getlist("item_name[]")
        item_qtys = request.POST.getlist("item_qty[]")
        items_data = []
        for name, qty in zip(item_names, item_qtys):
            if name and qty:
                items_data.append({
                    "name": name,
                    "quantity": int(qty)
                })

        # ===== Hitung total =====
        total_price = Decimal(0)
        if service.type == "per_kilo" and weight:
            total_price += Decimal(weight) * service.price
        elif service.type == "per_item":
            # Tambahkan harga layanan per-item (misal fee layanan tetap)
            total_price += service.price
            # Tambahkan harga semua item
            for i, q in zip(item_names, item_qtys):
                item_obj = LaundryItem.objects.filter(name=i).first()
                if item_obj:
                    total_price += Decimal(item_obj.price) * int(q)

        # ===== Hitung diskon berbasis transaksi pelanggan =====
        total_orders = Order.objects.filter(customer=customer).count()
        discount_obj = Discount.objects.filter(active=True, min_orders__lte=total_orders).order_by('-min_orders').first()
        if discount_obj:
            discount_percent = discount_obj.percent
            total_price_after_discount = total_price - (total_price * discount_percent / 100)
        else:
            discount_percent = None
            total_price_after_discount = total_price

        # ===== Simpan order =====
        order = Order.objects.create(
            customer=customer,
            service=service,
            items=items_data if items_data else None,
            weight=weight if weight else None,
            price_total=total_price_after_discount,
            discount_percent=discount_percent,
            scheduled_pickup=scheduled_pickup,
            payment_method=payment_method,
            order_status="pending",
            latitude=latitude,
            longitude=longitude,
            pickup_address=pickup_address
        )

        # ===== Midtrans jika QRIS =====
        if payment_method == "qris":
            import midtransclient
            from django.conf import settings

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
                    "email": customer.email,
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

        messages.success(request, f"Pesanan #{order.id} berhasil dibuat. Diskon: {discount_percent if discount_percent else 0}%")
        return redirect("orders:order_list")

    return render(request, "orders/order.html", {
        "services": services,
        "laundry_items": laundry_items,
        "customers": customers
    })


@login_required
def payment(request, order_id):
    """Halaman pembayaran Midtrans"""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    if not order.snap_token:
        messages.error(request, "Transaksi tidak ditemukan.")
        return redirect("orders:order_list")

    return render(request, "orders/payment.html", {
        "order": order,
        "snap_token": order.snap_token,
        "client_key": settings.MIDTRANS["CLIENT_KEY"],
    })


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
            elif transaction_status in ["cancel", "deny", "expire"]:
                order.payment_status = "unpaid"
            else:
                order.payment_status = transaction_status
            order.save()
        except Exception as e:
            print("Payment success update error:", e)

    messages.success(request, "✅ Pembayaran berhasil!")
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

# orders/views.py
from django.shortcuts import render
from django.db.models import Count, Sum
from .models import Order
from services.models import Service

def order_list(request):
    # Ambil semua order milik user
    orders = Order.objects.filter(customer=request.user).order_by('-created_at')

    # Statistik sederhana
    total_orders = orders.count()
    success_orders = orders.filter(order_status='delivered').count()
    pending_orders = orders.filter(order_status='pending').count()
    cancelled_orders = orders.filter(order_status='cancelled').count()

    # Total transaksi yang sudah dibayar
    total_paid_value = orders.filter(payment_status__in=['paid', 'settlement']).aggregate(
        total=Sum('price_total')
    )['total'] or 0

    # 🔹 Layanan yang sering digunakan
    # Mengelompokkan berdasarkan service, hitung jumlah order
    frequent_services = (
        orders.values('service')  # ambil id service
              .annotate(count=Count('service'))
              .order_by('-count')
    )

    # Ambil objek Service lengkap untuk tiap service
    for fs in frequent_services:
        fs['service'] = Service.objects.get(pk=fs['service'])

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
@login_required
@user_passes_test(admin_required)
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == "POST":
        new_status = request.POST.get("order_status")
        if new_status in dict(Order.ORDER_STATUS_CHOICES):
            order.order_status = new_status
            order.save()
            messages.success(request, f"Status pesanan #{order.id} diperbarui menjadi {order.get_order_status_display()}.")
        else:
            messages.error(request, "Status yang dipilih tidak valid.")
    return redirect('accounts:admin_dashboard')


@login_required
@user_passes_test(admin_required)
def update_payment_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == "POST":
        new_status = request.POST.get("payment_status")
        if new_status in dict(Order.PAYMENT_STATUS_CHOICES):
            order.payment_status = new_status
            order.save()
            messages.success(request, f"Status pembayaran pesanan #{order.id} diperbarui menjadi {order.get_payment_status_display()}.")
    return redirect("accounts:admin_dashboard")


@login_required
@user_passes_test(admin_required)
def assign_courier(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == "POST":
        courier_id = request.POST.get("courier")
        if not courier_id:
            order.assigned_courier = None
            order.save()
            messages.info(request, f"Kurir untuk pesanan #{order.id} telah dihapus.")
            return redirect('accounts:admin_dashboard')

        try:
            courier = User.objects.get(id=courier_id, is_courier=True)
            order.assigned_courier = courier
            order.save()
            messages.success(request, f"Kurir '{courier.username}' telah ditugaskan ke pesanan #{order.id}.")
        except User.DoesNotExist:
            messages.error(request, "Kurir yang dipilih tidak valid.")
    return redirect('accounts:admin_dashboard')


@login_required
@user_passes_test(admin_required)
def delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == "POST":
        order.delete()
        messages.success(request, f"Pesanan #{order.id} berhasil dihapus.")
    return redirect('orders:order_list')


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


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Order
import re

@csrf_exempt
def get_order_status(request):
    """
    Endpoint untuk menerima teks dari N8N dan balas data order dalam bentuk JSON.
    """
    if request.method == "POST":
        try:
            data = request.POST or request.GET
            message = data.get("message", "").lower().strip()

            response_data = {
                "reply": "❌ Format tidak dikenali. Ketik CEK<ID> (contoh: CEK15)"
            }

            match = re.match(r"cek(\d+)", message)
            if match:
                order_id = int(match.group(1))
                order = Order.objects.filter(id=order_id).select_related("customer", "service").first()

                if order:
                    response_data = {
                        "reply": (
                            f"📦 *Status Order #{order.id}*\n"
                            f"👤 Pelanggan: {order.customer.first_name or order.customer.username}\n"
                            f"🧺 Layanan: {order.service.name}\n"
                            f"💰 Total: Rp{order.price_total:,.0f}\n"
                            f"🚚 Status: {order.get_order_status_display()}\n"
                            f"💵 Pembayaran: {order.get_payment_status_display()}\n"
                            f"📅 Tanggal: {order.created_at.strftime('%d-%m-%Y %H:%M')}"
                        )
                    }
                else:
                    response_data = {"reply": f"❌ Order dengan ID {order_id} tidak ditemukan."}

            return JsonResponse(response_data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Gunakan POST method"}, status=405)
