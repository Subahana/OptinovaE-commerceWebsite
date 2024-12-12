from django.db import models
from django.utils import timezone
from products.models import Product  
from django.conf import settings
from django.contrib.auth.models import User

class Coupon(models.Model):
    COUPON_TYPES = (
        ('percentage', 'Percentage Discount'),
        ('fixed', 'Fixed Amount Discount'),
    )
    
    code = models.CharField(max_length=50, unique=True)
    coupon_type = models.CharField(max_length=20, choices=COUPON_TYPES, default='percentage')
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    active = models.BooleanField(default=True)
    used_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='used_coupons', blank=True)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    def is_valid(self):
        now = timezone.now()
        return self.active and (self.valid_from <= now <= self.valid_to)
        
    def deactivate_if_expired(self):
        """
        Deactivate the coupon if it has expired.
        """
        if self.valid_to < timezone.now():
            self.active = False
            self.save()

    def get_discount_amount(self, total_amount):
        if self.coupon_type == 'percentage' and self.discount_percentage:
            return total_amount * (self.discount_percentage / 100)
        elif self.coupon_type == 'fixed' and self.discount_amount:
            return min(self.discount_amount, total_amount)  
        return 0

    def __str__(self):
        return self.code

