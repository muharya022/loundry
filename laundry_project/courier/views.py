from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from orders.models import Order
from django.utils.timezone import now, timedelta
from django.utils import timezone
from django.core.paginator import Paginator

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from orders.models import Order
from django.utils import timezone
from django.core.paginator import Paginator

@login_required
def courier_dashboard(request):
    # Order aktif
    all_orders = Order.objects.filter(
        assigned_courier=request.user, 
        order_status__in=['pending', 'pickup', 'in_progress']
    ).order_by('-created_at')

    # Order selesai
    all_completed = Order.objects.filter(
        assigned_courier=request.user, 
        order_status='delivered'
    ).order_by('-updated_at')

    # Pagination
    orders_paginator = Paginator(all_orders, 10)
    completed_paginator = Paginator(all_completed, 10)
    orders_page_number = request.GET.get('orders_page')
    completed_page_number = request.GET.get('completed_page')
    orders = orders_paginator.get_page(orders_page_number)
    completed_orders = completed_paginator.get_page(completed_page_number)

    # Statistik termasuk order aktif + selesai
    today = timezone.now().date()
    week_start = today - timezone.timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    stats = {
        'daily': Order.objects.filter(
            assigned_courier=request.user,
            created_at__date=today
        ).count(),
        'weekly': Order.objects.filter(
            assigned_courier=request.user,
            created_at__date__gte=week_start
        ).count(),
        'monthly': Order.objects.filter(
            assigned_courier=request.user,
            created_at__date__gte=month_start
        ).count(),
    }

    return render(request, 'courier/dashboard.html', {
        'orders': orders,
        'completed_orders': completed_orders,
        'stats': stats,
    })


@login_required
def update_order_status(request, order_id, new_status):
    order = get_object_or_404(Order, id=order_id)

    # Pastikan hanya kurir yang bisa update status
    if not request.user.is_courier:
        messages.error(request, "Hanya kurir yang dapat mengubah status order.")
        return redirect('courier:courier_dashboard')

    # Update status
    order.order_status = new_status
    order.save()
    messages.success(request, f"Status order #{order.id} berhasil diubah menjadi {new_status}.")
    return redirect('courier:courier_dashboard')

@login_required
def mark_cod_paid(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Pastikan hanya kurir yang bisa update
    if not request.user.is_courier:
        messages.error(request, "Hanya kurir yang dapat mengubah pembayaran COD.")
        return redirect('courier:courier_dashboard')

    if order.payment_method == 'cod' and order.payment_status == 'unpaid':
        order.payment_status = 'paid'
        order.save()
        messages.success(request, f"Pembayaran COD Order #{order.id} telah ditandai sebagai dibayar.")
    else:
        messages.warning(request, "Order ini tidak bisa ditandai sebagai dibayar.")

    return redirect('courier:courier_dashboard')
