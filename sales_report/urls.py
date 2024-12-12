from django.urls import path
from . import views 

urlpatterns = [
    path('sales-report/', views.sales_report, name='sales_report'),
    path('generate_pdf_report/', views.generate_pdf_report, name='generate_pdf_report'),
    path('generate_excel_report/', views.generate_excel_report, name='generate_excel_report'),
    path('download_invoice/<int:order_id>/', views.download_invoice, name='download_invoice'),

]
