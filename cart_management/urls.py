from django.urls import path
from . import views

urlpatterns = [
    path('cart_detail/', views.cart_detail, name='cart_detail'),
    path('add_to_cart/<int:variant_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove_from_cart/<int:cart_item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update_cart_item_quantity/<int:item_id>/', views.update_cart_item_quantity, name='update_cart_item_quantity'),
    path('wishlist/', views.view_wishlist, name='view_wishlist'),
    path('wishlist/add/<int:variant_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/', views.remove_from_wishlist, name='remove_from_wishlist'),
]
