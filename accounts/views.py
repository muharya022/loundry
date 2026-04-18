from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.contrib.auth.forms import PasswordChangeForm 
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Sum
from django.utils.timezone import now
from datetime import timedelta
from django.http import HttpResponse
import random
import time

from orders.models import Order, Promo
from services.models import Service
from .forms import CustomPasswordChangeForm, ProfileForm, CustomUserCreationForm
from .models import PasswordResetOTP
from .waha_service import WAHAHandler

User = get_user_model()


def register(request):
    """Registrasi akun baru dengan verifikasi WhatsApp"""
    
    # DEBUG: Cetak method request
    print(f"=== REGISTER VIEW ===")
    print(f"Method: {request.method}")
    
    # Handle POST request
    if request.method == 'POST':
        print("Processing POST request...")
        
        # Cek apakah ini step verifikasi OTP
        if request.POST.get('step') == 'verify_otp':
            print("Step: verify_otp")
            return verify_registration_otp(request)
        
        # Proses registrasi normal
        print("Processing registration...")
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        username = request.POST.get('username', '').strip()
        phone = request.POST.get('phone', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        
        # Validasi
        if not first_name:
            messages.error(request, "Nama depan wajib diisi!")
            return redirect('accounts:register')
        
        if not username:
            messages.error(request, "Username wajib diisi!")
            return redirect('accounts:register')
        
        if not phone:
            messages.error(request, "Nomor HP wajib diisi!")
            return redirect('accounts:register')
        
        if password1 != password2:
            messages.error(request, "Password tidak cocok!")
            return redirect('accounts:register')
        
        if len(password1) < 8:
            messages.error(request, "Password minimal 8 karakter!")
            return redirect('accounts:register')
        
        # Cek username
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username sudah digunakan!")
            return redirect('accounts:register')
        
        # Format nomor HP
        phone = ''.join(filter(str.isdigit, phone))
        if phone.startswith('0'):
            phone = '62' + phone[1:]
        
        if not phone.startswith('62'):
            messages.error(request, "Nomor HP harus dimulai dengan 62 atau 0")
            return redirect('accounts:register')
        
        # Cek nomor HP
        if User.objects.filter(phone=phone).exists():
            messages.error(request, "Nomor HP sudah terdaftar!")
            return redirect('accounts:register')
        
        # Untuk sementara, langsung buat akun (bypass WAHA)
        try:
            user = User.objects.create_user(
                username=username,
                password=password1,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                is_active=True  # Langsung aktif
            )
            
            messages.success(request, "Akun berhasil dibuat! Silakan login.")
            return redirect('accounts:login')
            
        except Exception as e:
            print(f"Error creating user: {e}")
            messages.error(request, "Terjadi kesalahan saat membuat akun.")
            return redirect('accounts:register')
    
    # Handle GET request - Tampilkan form registrasi
    print("Showing registration form (GET request)")
    return render(request, 'accounts/register.html')


def verify_registration_otp(request):
    """Verifikasi OTP untuk registrasi"""
    
    reg_data = request.session.get('reg_data')
    
    if not reg_data:
        messages.error(request, "Sesi registrasi tidak ditemukan. Silakan registrasi ulang.")
        return redirect('accounts:register')
    
    # Cek apakah OTP sudah kadaluarsa
    if time.time() > reg_data.get('otp_expiry', 0):
        messages.error(request, "Kode OTP sudah kadaluarsa. Silakan registrasi ulang.")
        # Hapus data session
        if 'reg_data' in request.session:
            del request.session['reg_data']
        return redirect('accounts:register')
    
    input_otp = request.POST.get('otp')
    
    if input_otp == reg_data.get('otp'):
        # =====================
        # BUAT AKUN BARU (TANPA EMAIL)
        # =====================
        try:
            user = User.objects.create_user(
                username=reg_data['username'],
                password=reg_data['password'],
                first_name=reg_data['first_name'],
                last_name=reg_data['last_name'],
                email=None  # Email dikosongkan
            )
            
            # Simpan nomor HP
            user.phone = reg_data['phone']
            user.is_active = True  # Langsung aktif karena sudah verifikasi via WA
            user.save()
            
            # Hapus data session
            if 'reg_data' in request.session:
                del request.session['reg_data']
            
            messages.success(
                request, 
                "Akun berhasil dibuat! Silakan login dengan username dan password Anda."
            )
            return redirect('accounts:login')
            
        except Exception as e:
            print(f"Error membuat akun: {e}")
            messages.error(request, "Terjadi kesalahan saat membuat akun. Silakan coba lagi.")
            return redirect('accounts:register')
    else:
        messages.error(request, "Kode OTP salah! Silakan coba lagi.")
        return render(request, 'accounts/verify_otp.html', {
            'phone': reg_data.get('phone'),
            'step': 'verify'
        })


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

@login_required
def add_courier(request):
    if not request.user.is_staff:
        return redirect('accounts:home')

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        phone = request.POST.get("phone")  # Ganti email jadi phone
        
        # Validasi username
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username sudah digunakan.")
            return redirect('accounts:add_courier')
        
        # Validasi nomor HP
        if not phone:
            messages.error(request, "Nomor HP wajib diisi!")
            return redirect('accounts:add_courier')
        
        # Format nomor HP (hapus spasi, strip, dan karakter khusus)
        phone = ''.join(filter(str.isdigit, phone))
        
        # Jika dimulai dengan 0, ganti jadi 62
        if phone.startswith('0'):
            phone = '62' + phone[1:]
        
        # Validasi nomor HP hanya angka dan panjangnya sesuai
        if not phone.isdigit():
            messages.error(request, "Nomor HP harus berupa angka!")
            return redirect('accounts:add_courier')
        
        if len(phone) < 10 or len(phone) > 15:
            messages.error(request, "Nomor HP harus antara 10-15 digit!")
            return redirect('accounts:add_courier')
        
        if not phone.startswith('62'):
            messages.error(request, "Nomor HP harus dimulai dengan 62 (contoh: 628123456789)")
            return redirect('accounts:add_courier')
        
        # Cek nomor HP sudah terdaftar
        if User.objects.filter(phone=phone).exists():
            messages.error(request, "Nomor HP sudah digunakan!")
            return redirect('accounts:add_courier')
        
        # Buat akun kurir
        try:
            courier = User.objects.create_user(
                username=username,
                password=password,
                phone=phone,
                email=None,  # Email dikosongkan
                is_courier=True,
                is_customer=False,
                is_active=True  # Langsung aktif
            )
            
            messages.success(request, f"Kurir '{courier.username}' berhasil ditambahkan!")
            
            # Opsional: Kirim notifikasi WhatsApp ke kurir
            try:
                from .waha_service import WAHAHandler
                waha = WAHAHandler()
                message = f"""🎉 *Selamat! Anda Telah Menjadi Kurir*

Halo {username}!

Anda telah ditambahkan sebagai kurir di Menara Laundry.

━━━━━━━━━━━━━━━━━━━━
📋 *Informasi Akun*
━━━━━━━━━━━━━━━━━━━━

👤 *Username:* {username}
🔑 *Password:* {password}
📱 *Nomor HP:* {phone}

━━━━━━━━━━━━━━━━━━━━
🔗 *Link Login:*
━━━━━━━━━━━━━━━━━━━━

https://www.menaralaundry.site/accounts/login/

━━━━━━━━━━━━━━━━━━━━

Segera ganti password setelah login untuk keamanan.

---
Menara Laundry"""
                
                waha.send_message(phone, message)
            except Exception as e:
                print(f"Gagal kirim notifikasi: {e}")
                
        except Exception as e:
            messages.error(request, f"Error: {e}")
            return redirect('accounts:add_courier')
        
        return redirect('accounts:manage_users')

    return render(request, 'accounts/add_courier.html')

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


@login_required
@user_passes_test(admin_required)
def add_user(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True  # langsung aktif
            user.save()
            
            # =====================
            # KIRIM NOTIFIKASI VIA WHATSAPP
            # =====================
            from .waha_service import WAHAHandler
            
            waha = WAHAHandler()
            
            # Format nomor HP
            phone = getattr(user, 'phone', None)
            
            if phone:
                # Format pesan WhatsApp (bukan OTP)
                message = f"""🎉 *Selamat! Akun Anda Telah Dibuat*

Halo {user.first_name or user.username}!

Akun Menara Laundry Anda telah berhasil dibuat oleh Admin.

━━━━━━━━━━━━━━━━━━━━
📋 *Informasi Akun*
━━━━━━━━━━━━━━━━━━━━

👤 *Username:* {user.username}
🔑 *Password:* (Password yang Anda daftarkan)
📱 *Nomor HP:* {phone}

━━━━━━━━━━━━━━━━━━━━
🔗 *Link Login:*
━━━━━━━━━━━━━━━━━━━━

https://www.menaralaundry.site/accounts/login/

━━━━━━━━━━━━━━━━━━━━
💡 *Tips:*
━━━━━━━━━━━━━━━━━━━━

1. Simpan username dan password Anda dengan aman
2. Jangan berikan informasi akun kepada siapapun
3. Segera ganti password setelah login untuk keamanan

Jika ada kendala, silakan hubungi admin.

---
Menara Laundry - Solusi Laundry Praktis & Terpercaya"""
                
                # 🔥 PERBAIKAN: Gunakan send_message, BUKAN send_otp
                try:
                    success = waha.send_message(phone, message)  # ✅ Gunakan send_message
                    
                    if success:
                        messages.success(
                            request, 
                            f"User '{user.username}' berhasil ditambahkan. Notifikasi telah dikirim ke WhatsApp {phone}."
                        )
                    else:
                        messages.warning(
                            request, 
                            f"User '{user.username}' berhasil ditambahkan, tapi gagal mengirim notifikasi WhatsApp."
                        )
                except Exception as e:
                    print(f"Error kirim WA: {e}")
                    messages.warning(
                        request, 
                        f"User '{user.username}' berhasil ditambahkan, tapi notifikasi WhatsApp gagal dikirim."
                    )
            else:
                messages.success(
                    request, 
                    f"User '{user.username}' berhasil ditambahkan (tanpa notifikasi karena nomor HP tidak tersedia)."
                )
            
            return redirect('accounts:manage_users')
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

# views.py - Password reset dengan nomor HP
def password_reset_otp(request):
    if request.method == "POST":
        step = request.POST.get("step")

        # =====================
        # STEP 1: KIRIM OTP VIA WHATSAPP
        # =====================
        if step == "send_otp":
            phone = request.POST.get("phone")
            
            # Format nomor HP
            phone = ''.join(filter(str.isdigit, phone))
            if phone.startswith('0'):
                phone = '62' + phone[1:]
            
            user = User.objects.filter(phone=phone).first()

            if user:
                # Hapus OTP lama
                PasswordResetOTP.objects.filter(user=user).delete()

                # Generate OTP
                otp = str(random.randint(100000, 999999))
                PasswordResetOTP.objects.create(user=user, otp=otp)

                # Kirim via WAHA
                from .waha_service import WAHAHandler
                waha = WAHAHandler()
                
                message = f"""🔐 *Reset Password Menara Laundry*

Halo {user.first_name or user.username}!

Kami menerima permintaan reset password.

━━━━━━━━━━━━━━━━━━━━
🔑 *Kode OTP Anda:*
*{otp}*
━━━━━━━━━━━━━━━━━━━━

⏰ Kode ini berlaku *5 menit*

Jika Anda tidak meminta reset password, abaikan pesan ini.

---
Menara Laundry"""
                
                success = waha.send_message(phone, message)
                
                if success:
                    messages.success(
                        request,
                        f"Kode OTP telah dikirim ke WhatsApp {phone}"
                    )
                else:
                    messages.warning(
                        request,
                        "Gagal mengirim OTP. Silakan coba lagi."
                    )
                    return redirect("accounts:password_reset_otp")
            else:
                # Tetap tampilkan pesan sukses untuk keamanan
                messages.success(
                    request,
                    "Jika nomor HP terdaftar, OTP akan dikirim."
                )
                return redirect("accounts:password_reset_otp")

            return render(
                request,
                "accounts/password_reset_otp.html",
                {"step": "verify", "phone": phone}
            )

        # =====================
        # STEP 2: VERIFIKASI OTP
        # =====================
        if step == "verify_otp":
            otp = request.POST.get("otp")
            password = request.POST.get("password")
            confirm_password = request.POST.get("confirm_password")

            # Validasi password
            if not password or not confirm_password:
                messages.error(request, "Password harus diisi!")
                return redirect("accounts:password_reset_otp")
            
            if password != confirm_password:
                messages.error(request, "Password dan konfirmasi tidak cocok!")
                return redirect("accounts:password_reset_otp")
            
            if len(password) < 8:
                messages.error(request, "Password minimal 8 karakter!")
                return redirect("accounts:password_reset_otp")

            # Cek OTP
            record = PasswordResetOTP.objects.filter(otp=otp).first()

            if not record or record.is_expired():
                messages.error(request, "OTP tidak valid atau sudah kadaluarsa.")
                return redirect("accounts:password_reset_otp")

            # Reset password
            user = record.user
            user.set_password(password)
            user.save()
            record.delete()

            messages.success(
                request,
                "Password berhasil direset. Silakan login dengan password baru."
            )
            return redirect("accounts:login")

    # GET request - tampilkan form input nomor HP
    return render(request, "accounts/password_reset_otp.html", {"step": "email"})