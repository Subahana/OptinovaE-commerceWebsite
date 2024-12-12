from django.urls import path
from . import views

urlpatterns = [
    path('brands/', views.brand_list, name='brand_list'),
    path('brands/add/', views.brand_create, name='brand_create'),
    path('brands/edit/<int:pk>/', views.brand_edit, name='brand_edit'),
    path('brands/activate/<int:pk>/', views.brand_activate, name='brand_activate'),
    path('brands/deactivate/<int:pk>/', views.brand_deactivate, name='brand_deactivate'), 
]
