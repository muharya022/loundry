from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth import login, get_user_model
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.contrib.auth.forms import PasswordChangeForm 
from .forms import CustomPasswordChangeForm, ProfileForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required

User = get_user_model()

# ===============================
# 🔹 REGISTER DENGAN EMAIL VERIFIKASI
# ===============================
def register(request):
    """Registrasi akun baru dengan verifikasi email"""
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        # Validasi password
        if password1 != password2:
            messages.error(request, "Password tidak cocok!")
            return redirect('accounts:register')

        # Cek username/email sudah ada
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username sudah digunakan!")
            return redirect('accounts:register')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email sudah terdaftar!")
            return redirect('accounts:register')

        # Buat user tapi belum aktif
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name,
        )

        # Tambahkan phone jika field ada
        if hasattr(user, 'phone'):
            user.phone = phone

        # Nonaktifkan akun sampai diverifikasi, kecuali admin
        if not user.is_staff and not user.is_superuser:
            user.is_active = False
        user.save()

        # Kirim email verifikasi
        current_site = get_current_site(request)
        mail_subject = 'Aktivasi Akun Anda'
        message = render_to_string('accounts/activate_email.html', {
            'user': user,
            'domain': current_site.domain,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': default_token_generator.make_token(user),
        })
        email_message = EmailMessage(mail_subject, message, to=[email])
        email_message.content_subtype = 'html'
        email_message.send()

        messages.success(request, "Akun berhasil dibuat! Silakan cek email Anda untuk aktivasi.")
        return redirect('accounts:login')

    return render(request, 'accounts/register.html')

# ===============================
# 🔹 AKTIVASI AKUN
# ===============================
def activate(request, uidb64, token):
    """Aktivasi akun dari email"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "Akun Anda telah aktif! Silakan login.")
        return redirect('accounts:login')
    else:
        messages.error(request, "Link aktivasi tidak valid atau sudah digunakan.")
        return redirect('accounts:register')


# ===============================
# 🔹 LOGIN VIEW
# ===============================
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import render, redirect

def user_login(request):
    """Login user dan arahkan berdasarkan role"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            messages.success(request, f"Login berhasil! Selamat datang, {user.first_name or user.username} 😊")

            if user.is_staff or user.is_superuser:
                # Admin
                return redirect('accounts:admin_dashboard')
            elif getattr(user, 'is_courier', False):
                # Kurir
                return redirect('courier:courier_dashboard')
            else:
                # Member biasa
                return redirect('accounts:home')
        else:
            messages.error(request, "Username atau password salah!")

    return render(request, 'accounts/login.html')

from orders.models import Promo

def home(request):
    promos = Promo.objects.filter(is_active=True).order_by('-created_at')
    return render(request, 'home.html', {
        'promos': promos
    })

# ===============================
# 🔹 PROFILE VIEW
# ===============================
@login_required
def profile_view(request):
    """Halaman profil user dan ubah password"""
    user = request.user

    # Update profil
    if request.method == 'POST' and 'update_profile' in request.POST:
        profile_form = ProfileForm(request.POST, instance=user)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Profil berhasil diperbarui!")
            return redirect('accounts:profile')
    else:
        profile_form = ProfileForm(instance=user)

    # Ganti password
    if request.method == 'POST' and 'update_password' in request.POST:
        password_form = CustomPasswordChangeForm(user=user, data=request.POST)
        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password berhasil diganti!")
            return redirect('accounts:profile')
    else:
        password_form = PasswordChangeForm(user=user)

    context = {
        'profile_form': profile_form,
        'password_form': password_form,
    }
    return render(request, 'profile.html', context)

# ===============================
# 🔹 ADMIN DASHBOARD (dengan grafik pendapatan + pagination)
# ===============================
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Sum
from django.utils.timezone import now
from datetime import timedelta
from orders.models import Order
from services.models import Service

User = get_user_model()

@login_required
def admin_dashboard(request):
    """Halaman dashboard admin"""
    if not request.user.is_staff:
        return redirect('accounts:home')

    # 🔹 Data utama
    active_tab = request.GET.get('tab', 'dashboard')
    total_users = User.objects.count()
    total_orders = Order.objects.count()
    total_services = Service.objects.count()
    couriers = User.objects.filter(is_courier=True)
    total_couriers = couriers.count()

    # 🔹 Pendapatan (hanya yang sudah dibayar)
    paid_orders = Order.objects.filter(payment_status="paid")
    total_income = paid_orders.aggregate(total=Sum("price_total"))["total"] or 0

    today = now().date()
    today_income = paid_orders.filter(created_at__date=today).aggregate(total=Sum("price_total"))["total"] or 0
    total_transactions = paid_orders.count()

    # 🔹 Pendapatan 7 hari terakhir untuk grafik
    income_chart_labels = []
    income_chart_data = []
    for i in range(6, -1, -1):  # 7 hari ke belakang
        day = today - timedelta(days=i)
        income_day = paid_orders.filter(created_at__date=day).aggregate(total=Sum("price_total"))["total"] or 0
        income_chart_labels.append(day.strftime("%d %b"))  # Contoh: "10 Okt"
        income_chart_data.append(float(income_day))

    # 🔹 Pesanan terbaru
    recent_orders_list = Order.objects.select_related(
        "customer", "service", "assigned_courier"
    ).order_by("-created_at")

    # 🔹 Transaksi terbaru
    recent_transactions_list = paid_orders.select_related("customer").order_by("-created_at")

    # Pagination
    orders_page_number = request.GET.get("orders_page", 1)
    transactions_page_number = request.GET.get("transactions_page", 1)

    orders_paginator = Paginator(recent_orders_list, 5)  # 5 item per halaman
    transactions_paginator = Paginator(recent_transactions_list, 5)

    recent_orders = orders_paginator.get_page(orders_page_number)
    recent_transactions = transactions_paginator.get_page(transactions_page_number)

    context = {
        'active_tab': active_tab,
        "total_users": total_users,
        "total_orders": total_orders,
        "total_services": total_services,
        "total_couriers": total_couriers,
        "total_income": total_income,
        "today_income": today_income,
        "total_transactions": total_transactions,
        "recent_orders": recent_orders,
        "recent_transactions": recent_transactions,
        "couriers": couriers,
        "income_chart_labels": income_chart_labels,
        "income_chart_data": income_chart_data,
        "orders_paginator": orders_paginator,
        "transactions_paginator": transactions_paginator,
    }
    if active_tab == 'orders':
        context['active_tab'] = 'orders'

    return render(request, "accounts/admin_dashboard.html", context)


from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages

User = get_user_model()

@login_required
def add_courier(request):
    if not request.user.is_staff:
        return redirect('accounts:home')

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        email = request.POST.get("email")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username sudah digunakan.")
        else:
            courier = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_courier=True,
                is_customer = False
            )
            messages.success(request, f"Kurir '{courier.username}' berhasil ditambahkan!")
            return redirect('accounts:manage_users')

    return render(request, 'accounts/add_courier.html')

from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator

User = get_user_model()

def admin_required(user):
    return user.is_staff

@login_required
@user_passes_test(admin_required)
def manage_users(request):
    users = User.objects.all()

    # Pisahkan Karyawan (Admin & Kurir) dan Member
    staff_users_list = [u for u in users if u.is_staff or getattr(u, "is_courier", False)]
    member_users_list = [u for u in users if not u.is_staff and not getattr(u, "is_courier", False)]

    # Pagination: 10 user per halaman
    staff_paginator = Paginator(staff_users_list, 10)
    member_paginator = Paginator(member_users_list, 10)

    staff_page_number = request.GET.get('staff_page', 1)
    member_page_number = request.GET.get('member_page', 1)

    staff_users = staff_paginator.get_page(staff_page_number)
    member_users = member_paginator.get_page(member_page_number)

    return render(request, 'accounts/manage_users.html', {
        'staff_users': staff_users,
        'member_users': member_users,
    })


# views.py
from .forms import CustomUserCreationForm

@login_required
@user_passes_test(admin_required)
def add_user(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True  # langsung aktif
            user.save()

            # Kirim notifikasi akun baru (bukan aktivasi)
            mail_subject = 'Akun Anda Telah Dibuat'
            message = render_to_string('accounts/account_created_email.html', {
                'user': user,
                'password': '*** (dikirim terpisah atau diset manual)',
                'domain': get_current_site(request).domain,
            })
            email_message = EmailMessage(mail_subject, message, to=[user.email])
            email_message.content_subtype = 'html'
            email_message.send()

    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/add_user.html', {'form': form})


@login_required
@user_passes_test(admin_required)
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.delete()
        messages.success(request, f"Pengguna {user.username} berhasil dihapus.")
    return redirect('accounts:manage_users')

import random
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from .models import PasswordResetOTP

User = get_user_model()

def password_reset_otp(request):
    if request.method == "POST":
        step = request.POST.get("step")

        # =====================
        # STEP 1: KIRIM OTP
        # =====================
        if step == "send_otp":
            email = request.POST.get("email")
            user = User.objects.filter(email=email).first()

            if user:
                
                PasswordResetOTP.objects.filter(user=user).delete()

                otp = str(random.randint(100000, 999999))
                PasswordResetOTP.objects.create(user=user, otp=otp)

                subject = "🔐 Reset Password Akun FreshWash"
                message = f"""
                Halo,

                Kami menerima permintaan reset password untuk akun Anda.

                Kode OTP:
                {otp}

                Kode ini berlaku selama 5 menit.
                Jika Anda tidak merasa melakukan permintaan ini, abaikan email ini.

                Terima kasih,
                FreshWash Laundry
                """

                html_message = f"""
                <div style="font-family: Arial, sans-serif; background:#f4f6f8; padding:20px;">
                <div style="max-width:500px; margin:auto; background:white;
                            border-radius:10px; padding:30px; box-shadow:0 10px 25px rgba(0,0,0,.08)">

                    <h2 style="color:#2563eb; text-align:center; margin-bottom:10px;">
                    Reset Password
                    </h2>

                    <p style="color:#374151; font-size:14px;">
                    Kami menerima permintaan untuk mereset password akun Anda.
                    </p>

                    <div style="
                    margin:25px 0;
                    text-align:center;
                    font-size:32px;
                    font-weight:bold;
                    letter-spacing:6px;
                    color:#16a34a;
                    ">
                    {otp}
                    </div>

                    <p style="color:#374151; font-size:14px;">
                    Kode OTP ini berlaku selama
                    <strong>5 menit</strong>.
                    </p>

                    <p style="color:#6b7280; font-size:13px; margin-top:20px;">
                    Jika Anda tidak melakukan permintaan ini,
                    silakan abaikan email ini.
                    </p>

                    <hr style="margin:25px 0; border:none; border-top:1px solid #e5e7eb">

                    <p style="text-align:center; color:#9ca3af; font-size:12px;">
                    © 2026 FreshWash Laundry
                    </p>

                </div>
                </div>
                """

                send_mail(
                    subject,
                    message,                 # fallback text
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    html_message=html_message
                )


            messages.success(
                request,
                "Jika email terdaftar, OTP telah dikirim."
            )
            return render(
                request,
                "accounts/password_reset_otp.html",
                {"step": "verify", "email": email}
            )

        # =====================
        # STEP 2: VERIFIKASI OTP
        # =====================
        if step == "verify_otp":
            otp = request.POST.get("otp")
            password = request.POST.get("password")

            record = PasswordResetOTP.objects.filter(otp=otp).first()

            if not record or record.is_expired():
                messages.error(request, "OTP tidak valid atau sudah kadaluarsa.")
                return redirect("accounts:password_reset_otp")

            user = record.user
            user.set_password(password)
            user.save()

            record.delete()

            messages.success(
                request,
                "Password berhasil direset. Silakan login."
            )
            return redirect("accounts:login")

    return render(request, "accounts/password_reset_otp.html", {"step": "email"})
