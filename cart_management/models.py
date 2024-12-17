from django.db import models
from django.conf import settings
from products.models import Product, ProductVariant
from coupon_management.models import Coupon 

class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.SET_NULL)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  
    total_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  

    def __str__(self):
        return f"Cart of {self.user.username}"

    def get_original_total(self):
        # Sum up original prices without any discount
        return sum(item.quantity * item.variant.price for item in self.cartitem_set.all())

    def get_offer_total(self):
        # Sum up prices with any variant-specific discounts applied
        return sum(
            item.quantity * (item.variant.get_discounted_price() or item.variant.price)
            for item in self.cartitem_set.all()
        )

    def calculate_final_total(self):
        original_total = self.get_original_total()
        offer_total = self.get_offer_total()
        
        # Calculate offer-based discount
        offer_discount_amount = original_total - offer_total

        # Initialize coupon discount amount
        coupon_discount_amount = 0
        # Apply coupon if it's valid
        if self.coupon and self.coupon.is_valid():
            discount_base = offer_total if offer_discount_amount > 0 else original_total
            coupon_discount_amount = self.coupon.get_discount_amount(discount_base)

        # Total discount is the sum of offer and coupon discounts
        total_discount = offer_discount_amount + coupon_discount_amount
        final_total = original_total - total_discount
        return final_total

    def get_total_price(self):
        # Calls the calculate_final_total method to return the final price with discounts
        return self.calculate_final_total()

    def get_discount(self):
        # Calls calculate_final_total to fetch total discount applied
        return self.get_original_total() - self.calculate_final_total()


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # New field

    class Meta:
        unique_together = ('cart', 'variant')  # Ensure unique items per variant in each cart

    def save(self, *args, **kwargs):
        """Override save method to automatically update total_price."""
        # Calculate total price based on variant's discounted or original price
        discounted_price = self.variant.get_discounted_price()
        self.total_price = discounted_price * self.quantity if discounted_price < self.variant.price else self.variant.price * self.quantity
        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.variant} ({self.quantity}) in Cart"


class Wishlist(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product, related_name='wishlists')
    variants = models.ManyToManyField(ProductVariant, related_name='wishlisted_by')

    def __str__(self):
        return f"{self.user.username}'s Wishlist"
