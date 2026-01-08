from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone

from orders.models import Order


@login_required
def courier_dashboard(request):
    user = request.user

    # ================= ORDER AKTIF =================
    all_orders = Order.objects.filter(
        assigned_courier=user,
        order_status__in=['pending', 'pickup', 'in_progress']
    ).order_by('-created_at')

    # ================= ORDER SELESAI =================
    all_completed = Order.objects.filter(
        assigned_courier=user,
        order_status='delivered'
    ).order_by('-updated_at')

    # ================= PAGINATION =================
    orders = Paginator(all_orders, 10).get_page(
        request.GET.get('orders_page')
    )
    completed_orders = Paginator(all_completed, 10).get_page(
        request.GET.get('completed_page')
    )

    # ================= STATISTIK =================
    today = timezone.localdate()
    week_start = today - timezone.timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    daily_count = Order.objects.filter(
        assigned_courier=user,
        created_at__date=today
    ).count()

    weekly_count = Order.objects.filter(
        assigned_courier=user,
        created_at__date__gte=week_start
    ).count()

    monthly_count = Order.objects.filter(
        assigned_courier=user,
        created_at__date__gte=month_start
    ).count()

    # ================= PROGRESS =================
    DAILY_TARGET = 20  # target order per hari
    progress = min(
        int((daily_count / DAILY_TARGET) * 100), 100
    ) if DAILY_TARGET else 0

    stats = {
        'daily': daily_count,
        'weekly': weekly_count,
        'monthly': monthly_count,
        'progress': progress,
        'target': DAILY_TARGET,
    }

    return render(request, 'courier/dashboard.html', {
        'orders': orders,
        'completed_orders': completed_orders,
        'stats': stats,
    })


@login_required
def update_order_status(request, order_id, new_status):
    order = get_object_or_404(Order, id=order_id)

    # Validasi role kurir
    if not getattr(request.user, 'is_courier', False):
        messages.error(request, "Hanya kurir yang dapat mengubah status order.")
        return redirect('courier:courier_dashboard')

    order.order_status = new_status
    order.save()

    messages.success(
        request,
        f"Status order #{order.id} berhasil diubah menjadi {new_status}."
    )
    return redirect('courier:courier_dashboard')


@login_required
def mark_cod_paid(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Validasi role kurir
    if not getattr(request.user, 'is_courier', False):
        messages.error(request, "Hanya kurir yang dapat mengubah pembayaran COD.")
        return redirect('courier:courier_dashboard')

    if order.payment_method == 'cod' and order.payment_status == 'unpaid':
        order.payment_status = 'paid'
        order.save()
        messages.success(
            request,
            f"Pembayaran COD Order #{order.id} telah ditandai sebagai dibayar."
        )
    else:
        messages.warning(
            request,
            "Order ini tidak bisa ditandai sebagai dibayar."
        )

    return redirect('courier:courier_dashboard')
