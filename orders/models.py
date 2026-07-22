# orders/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db import connection
from services.models import Service
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)


class LaundryItem(models.Model):
    """Item laundry satuan (per item)"""
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='laundry_items/%Y/%m/%d/', blank=True, null=True)
    description = models.TextField(blank=True, help_text="Deskripsi item")
    is_active = models.BooleanField(default=True, help_text="Apakah item masih aktif")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - Rp{self.price:,.0f}"

    @property
    def formatted_price(self):
        return f"Rp {self.price:,.0f}".replace(',', '.')


class Order(models.Model):
    # Status pengantaran / order
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('picked_up', 'Diambil'),
        ('processing', 'Diproses'),
        ('ready', 'Siap Diantar'),
        ('delivered', 'Selesai'),
        ('cancelled', 'Dibatalkan'),
    ]

    # Status pembayaran
    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Belum Dibayar'),
        ('waiting_confirmation', 'Menunggu Konfirmasi'),
        ('paid', 'Sudah Dibayar'),
        ('rejected', 'Ditolak'),
    ]

    # Metode pembayaran
    PAYMENT_CHOICES = [
        ('cod', 'Bayar di Tempat (COD/Tunai)'),
        ('qris', 'QRIS / Transfer Online'),
    ]

    # ===== METODE PENGAMBILAN & PENGIRIMAN =====
    PICKUP_METHOD_CHOICES = [
        ('pickup', 'Dijemput Kurir'),
        ('dropoff', 'Antar Sendiri'),
    ]

    DELIVERY_METHOD_CHOICES = [
        ('delivery', 'Diantar Kurir'),
        ('pickup', 'Ambil Sendiri'),
    ]

    # ===== FIELD =====
    order_number = models.CharField(
        max_length=50, 
        unique=True, 
        null=True,
        blank=True, 
        editable=False,
        help_text="Nomor order profesional (contoh: INV-2026/07/22-001)"
    )

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    
    payment_proof = models.ImageField(
        upload_to="payment_proofs/%Y/%m/%d/",
        null=True,
        blank=True,
        help_text="Upload bukti pembayaran (QRIS/Transfer)"
    )

    payment_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Tanggal pembayaran dikonfirmasi"
    )

    service = models.ForeignKey(
        Service, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        help_text="Layanan utama yang dipilih"
    )
    
    notified_customer = models.BooleanField(
        default=False,
        help_text="Apakah notifikasi sudah dikirim ke customer"
    )
    
    notified_courier = models.BooleanField(
        default=False,
        help_text="Apakah notifikasi sudah dikirim ke kurir"
    )

    # Untuk layanan per kilo
    weight = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Total berat dalam kg"
    )

    price_total = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Total harga setelah diskon"
    )
    
    discount_percent = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Diskon dalam persen"
    )
    
    discount_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0, 
        help_text="Nominal diskon yang didapat"
    )
    
    pickup_address = models.TextField(
        help_text="Alamat lengkap pickup"
    )
    
    latitude = models.FloatField(
        help_text="Latitude lokasi pickup"
    )
    
    longitude = models.FloatField(
        help_text="Longitude lokasi pickup"
    )
    
    scheduled_pickup = models.DateTimeField(
        help_text="Jadwal pickup yang diminta"
    )
    
    estimated_completion = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Estimasi Selesai",
        help_text="Estimasi waktu selesai laundry"
    )

    # ===== FIELD UNTUK LAYANAN ANTAR-JEMPUT =====
    pickup_method = models.CharField(
        max_length=20, 
        choices=PICKUP_METHOD_CHOICES, 
        default='pickup',
        help_text="Apakah laundry dijemput kurir atau diantar sendiri?"
    )
    
    delivery_method = models.CharField(
        max_length=20, 
        choices=DELIVERY_METHOD_CHOICES, 
        default='delivery',
        help_text="Apakah hasil laundry diantar kurir atau diambil sendiri?"
    )
    
    shipping_cost = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text="Total biaya pengiriman (bisa 1x atau 2x ongkir)"
    )

    # Status terpisah
    order_status = models.CharField(
        max_length=20, 
        choices=ORDER_STATUS_CHOICES, 
        default='pending'
    )
    
    payment_status = models.CharField(
        max_length=20, 
        choices=PAYMENT_STATUS_CHOICES, 
        default='unpaid'
    )
    
    payment_method = models.CharField(
        max_length=10, 
        choices=PAYMENT_CHOICES, 
        default='cod',
        help_text="Metode pembayaran yang dipilih"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    assigned_courier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_orders',
        help_text="Kurir yang ditugaskan untuk order ini"
    )
    
    cart_data = models.JSONField(
        null=True, 
        blank=True, 
        default=dict,
        help_text="Data keranjang saat order dibuat"
    )

    def generate_order_number(self):
        """Generate nomor order profesional format INV-YYYY/MM/DD-XXX"""
        from django.db import connection
        date_str = timezone.now().strftime('%Y/%m/%d')
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM orders_order WHERE DATE(created_at) = DATE(%s)",
                [timezone.now()]
            )
            count = cursor.fetchone()[0] + 1
        return f"INV-{date_str}-{count:03d}"
    
        max_attempts = 10
        attempt = 0
        while Order.objects.filter(order_number=order_number).exists() and attempt < max_attempts:
            attempt += 1
            order_number = f"INV-{date_str}-{count:03d}-{attempt:02d}"
        
        return order_number
    
    # ===== SAVE METHOD (HANYA SATU) =====
    def save(self, *args, **kwargs):
        """
        Override save untuk:
        1. Generate order_number jika belum ada
        2. Track perubahan status untuk notifikasi
        """
        is_new = self.pk is None
        
        # Generate order number jika belum ada
        if not self.order_number:
            self.order_number = self.generate_order_number()
        
        # Simpan dulu untuk mendapatkan ID
        super().save(*args, **kwargs)
        
        # 🔥 Kirim notifikasi hanya jika order baru atau ada perubahan
        if is_new:
            # Order baru - kirim notifikasi
            self._send_notification_async('order_created')
        else:
            # Cek perubahan status untuk order existing
            try:
                old_order = Order.objects.get(pk=self.pk)
                
                # Cek perubahan status
                status_changed = old_order.order_status != self.order_status
                payment_changed = old_order.payment_status != self.payment_status
                courier_changed = old_order.assigned_courier_id != self.assigned_courier_id
                
                # Kirim notifikasi berdasarkan perubahan
                if status_changed:
                    self._send_status_notification()
                    
                if payment_changed and self.payment_status == 'paid':
                    self._send_notification_async('payment_confirmed')
                    
                if courier_changed and self.assigned_courier:
                    self._send_notification_async('courier_assigned')
                    
            except Order.DoesNotExist:
                pass
    
    # ===== NOTIFICATION METHODS =====
    def _send_notification_async(self, event_type):
        """
        Kirim notifikasi WhatsApp via WAHA (dengan try-except agar tidak error)
        """
        try:
            from utils.order_notifications import trigger_whatsapp_notification
            # Jalankan di thread terpisah agar tidak blocking
            import threading
            thread = threading.Thread(
                target=self._send_notification_safe,
                args=(event_type,)
            )
            thread.daemon = True
            thread.start()
        except ImportError as e:
            logger.error(f"❌ Failed to import notification module: {e}")
        except Exception as e:
            logger.error(f"❌ Failed to send notification: {e}")
    
    def _send_notification_safe(self, event_type):
        """Wrapper untuk mengirim notifikasi dengan error handling"""
        try:
            from utils.order_notifications import trigger_whatsapp_notification
            result = trigger_whatsapp_notification(self, event_type)
            
            if result.get('status') == 'ok':
                logger.info(f"✅ Notification sent for Order {self.order_number} - {event_type}")
            else:
                logger.warning(f"⚠️ Notification partial: {result}")
        except Exception as e:
            logger.error(f"❌ Failed to send notification: {e}")
    
    def _send_status_notification(self):
        """
        Kirim notifikasi berdasarkan status baru
        """
        status_map = {
            'picked_up': 'order_picked_up',
            'processing': 'order_processing',
            'ready': 'order_ready',
            'delivered': 'order_delivered',
            'cancelled': 'order_cancelled',
        }
        
        event = status_map.get(self.order_status)
        if event:
            self._send_notification_async(event)
    
    # ===== STRING REPRESENTATION =====
    def __str__(self):
        return f"{self.order_number} - {self.customer.username if self.customer else 'No Customer'}"

    # ===== PROPERTIES =====
    @property
    def is_per_item(self):
        return self.service.type == 'per_item' if self.service else False
    
    @property
    def is_per_kilo(self):
        return self.service.type == 'per_kilo' if self.service else False
    
    @property
    def total_shipping(self):
        """Total biaya pengiriman"""
        return self.shipping_cost or 0
    
    @property
    def pickup_description(self):
        """Deskripsi metode pengambilan"""
        if self.pickup_method == 'pickup':
            return "🚗 Dijemput Kurir"
        return "🏪 Antar Sendiri"
    
    @property
    def delivery_description(self):
        """Deskripsi metode pengiriman"""
        if self.delivery_method == 'delivery':
            return "🚚 Diantar Kurir"
        return "🏪 Ambil Sendiri"
    
    @property
    def total_items(self):
        """Total jumlah item dalam order"""
        return self.order_items.count()
    
    @property
    def is_paid(self):
        """Cek apakah order sudah dibayar"""
        return self.payment_status == 'paid'
    
    @property
    def is_completed(self):
        """Cek apakah order sudah selesai"""
        return self.order_status == 'delivered'
    
    @property
    def can_cancel(self):
        """Cek apakah order bisa dibatalkan"""
        return self.order_status in ['pending'] and self.payment_status in ['unpaid', 'pending']
    
    @property
    def can_pay(self):
        """Cek apakah order bisa dibayar"""
        return self.order_status == 'picked_up' and self.payment_status in ['unpaid', 'pending']
    
    @property
    def days_since_created(self):
        """Jumlah hari sejak order dibuat"""
        if self.created_at:
            return (timezone.now() - self.created_at).days
        return 0
    
    @property
    def formatted_price(self):
        """Format harga dengan pemisah ribuan"""
        return f"Rp {self.price_total:,.0f}".replace(',', '.')
    
    @property
    def formatted_weight(self):
        """Format berat dengan 2 desimal"""
        return f"{self.weight:.2f} kg" if self.weight else "0 kg"
    
    @property
    def has_payment_proof(self):
        """Cek apakah ada bukti pembayaran"""
        return bool(self.payment_proof)
    
    @property
    def is_waiting_confirmation(self):
        """Cek apakah menunggu konfirmasi pembayaran"""
        return self.payment_status == 'waiting_confirmation'

    # ===== CLASS METHODS =====
    @classmethod
    def get_pending_orders(cls):
        return cls.objects.filter(order_status='pending')
    
    @classmethod
    def get_processing_orders(cls):
        return cls.objects.filter(order_status='processing')
    
    @classmethod
    def get_ready_orders(cls):
        return cls.objects.filter(order_status='ready')
    
    @classmethod
    def get_delivered_orders(cls):
        return cls.objects.filter(order_status='delivered')
    
    @classmethod
    def get_cancelled_orders(cls):
        return cls.objects.filter(order_status='cancelled')
    
    @classmethod
    def get_unpaid_orders(cls):
        return cls.objects.filter(payment_status='unpaid')
    
    @classmethod
    def get_paid_orders(cls):
        return cls.objects.filter(payment_status='paid')
    
    @classmethod
    def get_waiting_confirmation_orders(cls):
        return cls.objects.filter(payment_status='waiting_confirmation')
    
    @classmethod
    def get_today_orders(cls):
        """Get orders created today"""
        today = timezone.now().date()
        return cls.objects.filter(created_at__date=today)
    
    @classmethod
    def get_this_month_orders(cls):
        """Get orders created this month"""
        now = timezone.now()
        return cls.objects.filter(
            created_at__year=now.year,
            created_at__month=now.month
        )


class OrderItem(models.Model):
    """Item dalam order (untuk multiple services)"""
    
    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE, 
        related_name="order_items"
    )
    
    service = models.ForeignKey(
        Service, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    
    laundry_item = models.ForeignKey(
        LaundryItem, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    
    quantity = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Jumlah untuk layanan per item"
    )
    
    weight = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Berat untuk layanan per kilo"
    )
    
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Harga per unit/kg"
    )
    
    subtotal = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Total harga item ini"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        if self.service:
            return f"{self.order.order_number} - {self.service.name}"
        elif self.laundry_item:
            return f"{self.order.order_number} - {self.laundry_item.name}"
        return f"{self.order.order_number} - Item #{self.id}"
    
    def save(self, *args, **kwargs):
        """Auto-calculate subtotal jika berubah"""
        if self.service and self.service.type == 'per_kilo' and self.weight:
            self.subtotal = self.weight * self.price
        elif self.laundry_item and self.quantity:
            self.subtotal = self.quantity * self.price
        elif self.service and self.service.type == 'per_item':
            self.subtotal = self.price * (self.quantity or 1)
        super().save(*args, **kwargs)
    
    @property
    def is_kilo_item(self):
        """Cek apakah item adalah layanan per kilo"""
        return self.service and self.service.type == 'per_kilo'
    
    @property
    def is_item_based(self):
        """Cek apakah item adalah layanan per item"""
        return bool(self.laundry_item) or (self.service and self.service.type == 'per_item')
    
    @property
    def formatted_subtotal(self):
        return f"Rp {self.subtotal:,.0f}".replace(',', '.')


class Promo(models.Model):
    """Promo/diskoun untuk order"""
    
    title = models.CharField(max_length=100, help_text="Judul promo")
    description = models.TextField(help_text="Deskripsi promo")
    discount_amount = models.PositiveIntegerField(help_text="Nominal diskon")
    min_transaction = models.PositiveIntegerField(default=0, help_text="Minimal transaksi")
    image = models.ImageField(upload_to='promo/%Y/%m/%d/', blank=True, null=True)
    is_active = models.BooleanField(default=True, help_text="Apakah promo aktif")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    @property
    def formatted_discount(self):
        return f"Rp {self.discount_amount:,.0f}".replace(',', '.')
    
    @property
    def formatted_min_transaction(self):
        return f"Rp {self.min_transaction:,.0f}".replace(',', '.')


class UserPromo(models.Model):
    """Promo yang dimiliki oleh user"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_promos'
    )
    promo = models.ForeignKey(
        Promo, 
        on_delete=models.CASCADE,
        related_name='user_promos'
    )
    is_used = models.BooleanField(
        default=False,
        help_text="Apakah promo sudah digunakan"
    )
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Tanggal promo diberikan"
    )
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Tanggal promo digunakan"
    )

    class Meta:
        unique_together = ('user', 'promo')
        ordering = ['-assigned_at']

    def __str__(self):
        return f"{self.user} - {self.promo.title}"
    
    def mark_as_used(self):
        """Mark promo sebagai sudah digunakan"""
        self.is_used = True
        self.used_at = timezone.now()
        self.save()
    
    @property
    def is_expired(self):
        """Cek apakah promo sudah expired (3 bulan setelah assigned)"""
        if self.assigned_at:
            expiry = self.assigned_at + timedelta(days=90)
            return timezone.now() > expiry
        return False
    
    @property
    def can_use(self):
        """Cek apakah promo bisa digunakan"""
        return not self.is_used and not self.is_expired and self.promo.is_active


class PaymentSetting(models.Model):
    """Pengaturan pembayaran (QRIS, Bank, dll)"""
    
    bank_name = models.CharField(
        max_length=50,
        help_text="Nama bank"
    )
    account_name = models.CharField(
        max_length=100,
        help_text="Nama pemilik rekening"
    )
    account_number = models.CharField(
        max_length=50,
        help_text="Nomor rekening"
    )
    qris_image = models.ImageField(
        upload_to="qris/%Y/%m/%d/",
        help_text="QR Code QRIS"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Apakah pengaturan ini aktif"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.bank_name} - {self.account_name}"
    
    @classmethod
    def get_active(cls):
        """Get active payment setting"""
        return cls.objects.filter(is_active=True).first()


# ===== SIGNALS =====
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=Order)
def order_post_save(sender, instance, created, **kwargs):
    """Signal untuk logging setelah order disimpan"""
    if created:
        logger.info(f"📦 New order created: {instance.order_number} by {instance.customer.username}")
    else:
        logger.info(f"📦 Order updated: {instance.order_number} - Status: {instance.order_status}")


@receiver(post_delete, sender=Order)
def order_post_delete(sender, instance, **kwargs):
    """Signal untuk logging setelah order dihapus"""
    logger.warning(f"🗑️ Order deleted: {instance.order_number} by {instance.customer.username}")


@receiver(post_save, sender=PaymentSetting)
def payment_setting_post_save(sender, instance, created, **kwargs):
    """Signal untuk logging setelah payment setting diubah"""
    if created:
        logger.info(f"💰 New payment setting: {instance.bank_name}")
    else:
        logger.info(f"💰 Payment setting updated: {instance.bank_name}")


# ===== UTILITY FUNCTIONS =====
from django.db.models import Sum, Count

def get_order_statistics(user=None):
    """
    Get order statistics for a user or all users
    """
    if user:
        orders = Order.objects.filter(customer=user)
    else:
        orders = Order.objects.all()
    
    total = orders.count()
    pending = orders.filter(order_status='pending').count()
    processing = orders.filter(order_status='processing').count()
    ready = orders.filter(order_status='ready').count()
    delivered = orders.filter(order_status='delivered').count()
    cancelled = orders.filter(order_status='cancelled').count()
    
    total_paid = orders.filter(payment_status='paid').aggregate(
        total=Sum('price_total')
    )['total'] or 0
    
    return {
        'total_orders': total,
        'pending': pending,
        'processing': processing,
        'ready': ready,
        'delivered': delivered,
        'cancelled': cancelled,
        'total_paid': total_paid,
        'completion_rate': (delivered / total * 100) if total > 0 else 0,
    }


def cleanup_cancelled_orders(days=2):
    """
    Hapus order yang statusnya cancelled lebih dari X hari
    """
    cutoff = timezone.now() - timedelta(days=days)
    deleted = Order.objects.filter(
        order_status='cancelled',
        created_at__lte=cutoff
    ).delete()
    return deleted[0]  # Jumlah yang dihapus