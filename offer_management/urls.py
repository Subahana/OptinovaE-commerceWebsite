from django.urls import path
from . import views

urlpatterns = [
    path('offers/category/new/', views.create_category_offer, name='create_category_offer'),
    path('offers/category/edit/<int:offer_id>/', views.update_category_offer, name='update_category_offer'),
    path('offers/category/', views.offer_list, name='offer_list'),
    path('offers/category/status/<int:offer_id>/', views.offer_status, name='offer_status'),

]
