from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Endpoint API
    path('notifications/', views.get_order_notifications, name='get_order_notifications'),
    path('notifications/read/', views.mark_notifications_as_read, name='mark_notifications_as_read'),

    # Endpoint frontend / admin
    path('', views.order_list, name='order_list'),
    path('<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('order/', views.create_order, name='order'),
    path("payment/<int:order_id>/", views.payment, name="payment"),
    path("payment-success/", views.payment_success, name="payment_success"),
    path("invoice/<int:order_id>/", views.order_invoice, name="order_invoice"),
    path('order/download/<int:order_id>/', views.download_invoice, name='download_invoice'),
    path("midtrans-callback/", views.callback_midtrans, name="midtrans_callback"),
    path('delete/<int:order_id>/', views.delete_order, name='delete_order'),
    path('update-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('order/<int:order_id>/update-payment/', views.update_payment_status, name='update_payment_status'),
    path('assign-courier/<int:order_id>/', views.assign_courier, name='assign_courier'),
    path('add-item/', views.add_laundry_item, name='add_laundry_item'),
    path('edit-item/<int:item_id>/', views.edit_laundry_item, name='edit_laundry_item'),
    path('delete-item/<int:item_id>/', views.delete_laundry_item, name='delete_laundry_item'),
    path('notifications/', views.get_order_notifications, name='get_order_notifications'),
]
