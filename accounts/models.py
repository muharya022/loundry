# models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from django.conf import settings

class User(AbstractUser):
    # Role user
    is_customer = models.BooleanField(default=True, verbose_name="Pelanggan")
    is_courier = models.BooleanField(default=False, verbose_name="Kurir")
    is_staff_member = models.BooleanField(default=False, verbose_name="Staff")
    
    # Kontak (Email jadi opsional)
    email = models.EmailField(blank=True, null=True, verbose_name="Email")  # Email tidak wajib
    phone = models.CharField(
        max_length=15,  # Maksimal 15 digit untuk nomor HP Indonesia
        unique=True,  # Nomor HP harus unik
        validators=[
            RegexValidator(
                regex=r'^[0-9]{10,15}$',
                message='Nomor HP harus berupa angka dan minimal 10 digit'
            )
        ],
        verbose_name="Nomor WhatsApp"
    )
    
    # Alamat dan verifikasi
    address = models.TextField(blank=True, null=True, verbose_name="Alamat")
    is_verified = models.BooleanField(default=False, verbose_name="Terverifikasi")
    
    class Meta:
        verbose_name = "Pengguna"
        verbose_name_plural = "Pengguna"
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.username} - {self.phone}"
    
    def get_full_name(self):
        """Mengembalikan nama lengkap"""
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.username
    
    def get_role(self):
        """Mengembalikan role user"""
        if self.is_superuser:
            return "Super Admin"
        elif self.is_staff:
            return "Admin"
        elif self.is_courier:
            return "Kurir"
        elif self.is_customer:
            return "Pelanggan"
        return "Unknown"
    
    def save(self, *args, **kwargs):
        # Auto-set username jika kosong (gunakan nomor HP)
        if not self.username:
            self.username = self.phone
        super().save(*args, **kwargs)


class PasswordResetOTP(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reset_otps',
        verbose_name="Pengguna"
    )
    otp = models.CharField(
        max_length=6,
        verbose_name="Kode OTP"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Waktu Dibuat"
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name="Sudah Digunakan"
    )
    
    class Meta:
        verbose_name = "Reset Password OTP"
        verbose_name_plural = "Reset Password OTP"
        ordering = ['-created_at']
    
    def is_expired(self):
        """Cek apakah OTP sudah kadaluarsa (5 menit)"""
        if self.is_used:
            return True
        expired_time = self.created_at + timezone.timedelta(minutes=5)
        return timezone.now() > expired_time
    
    def use_otp(self):
        """Tandai OTP sebagai sudah digunakan"""
        self.is_used = True
        self.save()
    
    def __str__(self):
        return f"{self.user.username} - {self.otp} - {'Expired' if self.is_expired() else 'Valid'}"