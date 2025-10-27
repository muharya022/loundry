from django import forms
from .models import Service

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['name', 'description', 'price', 'type', 'duration', 'image']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full border rounded-lg px-4 py-2',
                'placeholder': 'Masukkan nama layanan'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full border rounded-lg px-4 py-2',
                'rows': 3,
                'placeholder': 'Masukkan deskripsi layanan'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'w-full border rounded-lg px-4 py-2',
                'placeholder': 'Masukkan harga layanan'
            }),
            'type': forms.Select(attrs={
                'class': 'w-full border rounded-lg px-4 py-2'
            }),
            'duration': forms.Select(attrs={
                'class': 'w-full border rounded-lg px-4 py-2'
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'w-full border rounded-lg px-4 py-2 bg-white'
            }),
        }
