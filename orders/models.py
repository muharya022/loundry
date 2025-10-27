from django.db import models
from django.conf import settings
from services.models import Service

class LaundryItem(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='laundry_items/', blank=True, null=True)

    def __str__(self):
        return f"{self.name} - Rp{self.price:,.0f}"


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
        ('paid', 'Dibayar'),
        ('settlement', 'Selesai'),
    ]

    # Metode pembayaran
    PAYMENT_CHOICES = [
        ('cod', 'Bayar di Tempat (COD/Tunai)'),
        ('qris', 'QRIS / Transfer Online'),
    ]

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )

    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    notified_customer = models.BooleanField(default=False)  # ✅ Tambahan untuk notifikasi

    # Tambahan untuk layanan per item
    item_type = models.ForeignKey(LaundryItem, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField(default=0)

    # Untuk layanan per kilo
    weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # Detail item (JSON)
    items = models.JSONField(blank=True, null=True)

    price_total = models.DecimalField(max_digits=12, decimal_places=2)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    pickup_address = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    scheduled_pickup = models.DateTimeField()

    # Status terpisah
    order_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='cod')

    snap_token = models.CharField(max_length=255, blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    assigned_courier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_orders'
    )

    def save(self, *args, **kwargs):
        """Otomatis set notified_customer=False jika status berubah"""
        if self.pk:  # Jika pesanan sudah ada
            old_order = Order.objects.get(pk=self.pk)
            if old_order.order_status != self.order_status:
                self.notified_customer = False  # 🔔 status berubah → notifikasi baru
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.id} - {self.customer.username} (Order: {self.order_status}, Payment: {self.payment_status})"

    @property
    def is_per_item(self):
        return self.service.type == 'per_item'

    def calculate_total(self):
        """Hitung total otomatis berdasarkan jenis layanan."""
        if self.is_per_item and self.item_type:
            return self.item_type.price * self.quantity
        elif self.service.type == 'per_kilo' and self.weight:
            return self.service.price * self.weight
        return 0


class Discount(models.Model):
    name = models.CharField(max_length=100)
    min_orders = models.PositiveIntegerField(default=0)  # minimal transaksi
    percent = models.DecimalField(max_digits=5, decimal_places=2)  # diskon %
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.percent}% untuk minimal {self.min_orders} transaksi)"
