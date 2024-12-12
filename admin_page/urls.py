from django.urls import path
from django.http import HttpResponse
from . import views

urlpatterns = [
    path('admin_page/', views.admin_page, name='admin_page'),
    path('users/', views.user_management_page, name='user_management_page'),
    path('users/block/<int:id>/', views.block_user, name='block_user'),
    path('users/unblock/<int:id>/', views.unblock_user, name='unblock_user'),
    path('users/details/<int:id>/', views.user_details_page, name='user_details_page'),
    path('user/<int:id>/delete/', views.permanent_delete_user, name='permanent_delete_user'),
    path('admin_logout_view/', views.admin_logout_view, name='admin_logout_view'),

]
