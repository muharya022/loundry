# services/models.py
from django.db import models

class Service(models.Model):
    SERVICE_TYPE_CHOICES = [
        ('per_kilo', 'Per Kilo'),
        ('per_item', 'Per Item'),
    ]

    DURATION_CHOICES = [
        ('biasa', 'Biasa (2-3 hari)'),
        ('sicepat', 'SiCepat (1 hari)'),
        ('express', 'Express (6 jam)'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=20, choices=SERVICE_TYPE_CHOICES)
    duration = models.CharField(max_length=20, choices=DURATION_CHOICES, default='biasa')
    image = models.ImageField(upload_to='service_images/', blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

class ItemType(models.Model):
    """Jenis item untuk layanan per item"""
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='item_images/', blank=True, null=True)  # tambah ini

    def __str__(self):
        return f"{self.name} (Rp {self.price})"
