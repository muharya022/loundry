from django.contrib import admin
from .models import PaymentSetting

@admin.register(PaymentSetting)
class PaymentSettingAdmin(admin.ModelAdmin):
    list_display = (
        "bank_name",
        "account_number",
        "is_active",
    )