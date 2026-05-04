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
        # ('settlement', 'Selesai'),
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

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )

    service = models.ForeignKey(Service, on_delete=models.PROTECT, null=True, blank=True)
    notified_customer = models.BooleanField(default=False)

    # Untuk layanan per kilo
    weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    price_total = models.DecimalField(max_digits=12, decimal_places=2)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Nominal diskon yang didapat")
    
    pickup_address = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    scheduled_pickup = models.DateTimeField()
    estimated_completion = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Estimasi Selesai"
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
    cart_data = models.JSONField(null=True, blank=True, default=dict)

    def save(self, *args, **kwargs):
        """Otomatis set notified_customer=False jika status berubah"""
        if self.pk:  # Jika pesanan sudah ada
            old_order = Order.objects.get(pk=self.pk)
            if old_order.order_status != self.order_status:
                self.notified_customer = False  # 🔔 status berubah → notifikasi baru
        super().save(*args, **kwargs)

    def __str__(self):
        pickup_display = self.get_pickup_method_display() if self.pickup_method else '-'
        delivery_display = self.get_delivery_method_display() if self.delivery_method else '-'
        return f"Order #{self.id} - {self.customer.username} (Pickup: {pickup_display}, Delivery: {delivery_display})"

    @property
    def is_per_item(self):
        return self.service.type == 'per_item' if self.service else False

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

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_items")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, null=True, blank=True)
    laundry_item = models.ForeignKey(LaundryItem, on_delete=models.CASCADE, null=True, blank=True)
    
    quantity = models.IntegerField(null=True, blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)


class Promo(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    discount_amount = models.PositiveIntegerField()  # 🔥 NOMINAL
    min_transaction = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='promo/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


from django.conf import settings
from django.db import models

class UserPromo(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    promo = models.ForeignKey('Promo', on_delete=models.CASCADE)
    is_used = models.BooleanField(default=False)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'promo')

    def __str__(self):
        return f"{self.user} - {self.promo.title}"
