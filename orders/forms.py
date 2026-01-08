from django import forms
from .models import UserPromo

class AssignPromoForm(forms.ModelForm):
    class Meta:
        model = UserPromo
        fields = ['user', 'promo']

from django import forms
from .models import Promo

class PromoForm(forms.ModelForm):
    class Meta:
        model = Promo
        fields = [
            'title',
            'description',
            'discount',
            'min_transaction',
            'image',          # ⬅️ tambah ini
            'is_active'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'discount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'min_transaction': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'image': forms.ClearableFileInput(attrs={   # ⬅️ widget upload
                'class': 'form-control'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
