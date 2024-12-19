from django.urls import path
from . import views
from .views import VerifyRazorpayPayment

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('order/success/razorpay/<int:order_id>/', views.razorpay_order_success, name='razorpay_order_success'),
    path('order/success/cod/<int:order_id>/', views.cod_order_success, name='cod_order_success'),
    path('handle_payment_failure/<int:order_id>/', views.handle_payment_failure, name='handle_payment_failure'),
    path('complete_payment/<int:order_id>/', views.complete_payment, name='complete_payment'),
    path('list_orders/', views.list_orders, name='list_orders'),
    path('update_order_status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('verify_razorpay_payment/<int:order_id>/', VerifyRazorpayPayment.as_view(), name='verify_razorpay_payment'),

    path('order/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('order/<int:order_id>/cancel_with_refund/', views.cancel_order_with_refund, name='cancel_order_with_refund'),
    path('order/<int:order_id>/return_with_refund/', views.return_order_with_refund, name='return_order_with_refund'),

]

