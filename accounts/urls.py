from django.urls import path
from . import views

urlpatterns = [
    path('', views.first_page, name='first_page'),
    path('admin_login/', views.admin_login, name='admin_login'),
    path('user_login_view/', views.user_login_view, name='user_login_view'),
    path('registration/', views.registration_view, name='registration_view'),
    path('otp_verify/<str:username>/', views.otp_verify, name='otp_verify'),
    path('resend_otp/', views.resend_otp, name='resend_otp'),
    path('password_reset/', views.password_reset_request, name='password_reset_request'),
    path('password_reset_verify/<str:username>/', views.password_reset_verify, name='password_reset_verify'),
    path('password_reset_form/<str:username>/', views.password_reset_form, name='password_reset_form'),
]
