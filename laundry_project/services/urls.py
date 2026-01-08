# services/urls.py
from django.urls import path
from .views import service_list
from . import views

app_name = 'services'

urlpatterns = [
    path('', service_list, name='list'),
    path('add/', views.add_service, name='add_service'),
    path('edit/<int:pk>/', views.edit_service, name='edit_service'),
    path('delete/<int:pk>/', views.delete_service, name='delete_service'),
]
