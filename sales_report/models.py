from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

class SalesReport(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    total_sales = models.DecimalField(max_digits=10, decimal_places=2)
    total_orders = models.IntegerField()
    report_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Report for {self.user} on {self.report_date}"
