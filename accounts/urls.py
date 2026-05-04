from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [

    path('', views.home, name='home'),    
    path('login/', views.user_login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='accounts:login'), name='logout'),
    path('register/', views.register, name='register'),
    path("password-reset-otp/", views.password_reset_otp, name="password_reset_otp"),
    path('verify-otp/', views.verify_registration_otp, name='verify_registration_otp'),  
    path('manage/', views.manage_users, name='manage_users'),
    path('add/', views.add_user, name='add_user'),
    path('delete/<int:user_id>/', views.delete_user, name='delete_user'),
    path('profile/', views.profile_view, name='profile'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('add-courier/', views.add_courier, name='add_courier'),

    path('export-excel/<int:year>/<int:month>/', views.export_orders_excel, name='export_orders_excel'),
    path('export-excel/', views.export_orders_excel, name='export_orders_excel_current'),
        
]
