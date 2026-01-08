from django.urls import path
from . import views

app_name = 'courier'

urlpatterns = [
    path('', views.courier_dashboard, name='courier_dashboard'),
    path('update-status/<int:order_id>/<str:new_status>/', views.update_order_status, name='update_status'),
    path('mark-cod-paid/<int:order_id>/', views.mark_cod_paid, name='mark_cod_paid'),

]
