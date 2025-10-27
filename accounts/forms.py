from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'address']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400'
            }),
            'address': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400',
                'rows': 3
            }),
        }


from django import forms
from django.contrib.auth.forms import PasswordChangeForm

class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'w-full px-4 py-2 border border-red-400 rounded-md bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-300'
    }))
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'w-full px-4 py-2 border border-red-400 rounded-md bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-300'
    }))
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'w-full px-4 py-2 border border-red-400 rounded-md bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-300'
    }))

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400'
            }),
        }

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400'
        })
    )
    password2 = forms.CharField(
        label="Konfirmasi Password",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400'
        })
    )
