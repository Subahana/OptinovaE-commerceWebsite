from django.urls import path
from .views import *

urlpatterns = [
    path('categories/', category_list, name='category_list'),
    path('categories/add/', add_category, name='add_category'),
    path('categories/edit/<int:id>/', edit_category, name='edit_category'),
    path('categories/activate/<int:id>/', activate_category, name='activate_category'),
    path('categories/delete/permanent/<int:id>/', permanent_delete_category, name='permanent_delete_category'),
    path('categories/delete/soft/<int:id>/', soft_delete_category, name='soft_delete_category'),

    path('products/', product_list, name='product_list'),
    path('products/add/', add_product, name='add_product'),
    path('products/add/variants/<int:product_id>/', add_variant, name='add_variant'),
    path('products/edit/variants/<int:variant_id>/', edit_variant, name='edit_variant'),
    path('products/add_images/<int:variant_id>/', add_images, name='add_images'),
    path('products/edit_images/<int:variant_id>/', edit_images, name='edit_images'),
    path('products/delete_image/<int:variant_id>/', delete_image, name='delete_image'),
    path('products/edit/<int:product_id>/', edit_product, name='edit_product'),
    path('products/delete/soft/<int:product_id>/', soft_delete_product, name='soft_delete_product'),
    path('products/delete/permanent/<int:product_id>/', permanent_delete_product, name='permanent_delete_product'),
    path('variants/activate/<int:variant_id>/', activate_variant, name='activate_variant'),
    path('variants/deactivate/<int:variant_id>/', deactivate_variant, name='deactivate_variant'),
    path('variants/delete/<int:variant_id>/', delete_variant, name='delete_variant'),
    path('images/delete/<int:variant_id>/', delete_selected_images, name='delete_selected_images'),
    path('products/products/activate/<int:product_id>/', activate_product, name='activate_product'),
    path('products/detail/<int:product_id>/<int:variant_id>/', product_detail, name='product_detail'),

    path('images/delete/<int:product_id>/', delete_selected_images, name='delete_selected_images'),

    path('admin/dashboard/', admin_dashboard, name='admin_dashboard'),

    path('variant/<int:variant_id>/set-main/', set_main_variant, name='set_main_variant'),

]
