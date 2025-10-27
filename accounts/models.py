from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    is_customer = models.BooleanField(default=True)
    is_courier = models.BooleanField(default=False)
    is_staff_member = models.BooleanField(default=False)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.username
