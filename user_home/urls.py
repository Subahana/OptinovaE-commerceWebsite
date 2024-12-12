from django.urls import path
from . import views

urlpatterns = [
    path('', views.user_home, name='user_home'),
    path('shop/', views.shop, name='shop'),
    path('user_product_detail/<int:product_id>/', views.user_product_detail, name='user_product_detail'),
    path('logout_view/', views.logout_view, name='logout_view'),

]
