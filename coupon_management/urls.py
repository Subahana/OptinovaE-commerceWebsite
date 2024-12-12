from django.urls import path
from . import views

urlpatterns = [
    path('coupons/', views.coupon_list, name='coupon_list'),
    path('coupons/create/', views.create_coupon, name='create_coupon'),
    path('coupons/edit/<int:coupon_id>/', views.edit_coupon, name='edit_coupon'),
    path('coupons/coupon_status/<int:coupon_id>/', views.coupon_status, name='coupon_status'),
    path('apply_coupon/', views.apply_coupon, name='apply_coupon'),
    path('remove_coupon/', views.remove_coupon, name='remove_coupon'),

]
