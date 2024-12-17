from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.validators import MinValueValidator
from user_profile.models import Address
from products.models import ProductVariant
from coupon_management.models import Coupon


class OrderStatus(models.Model):
    status = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.status

    @staticmethod
    def get_default_status():
        status, _ = OrderStatus.objects.get_or_create(status="Pending")
        return status.id

    @staticmethod
    def get_returned_status():
        status, _ = OrderStatus.objects.get_or_create(status="Returned")
        return status.id

class PaymentStatus(models.Model):
    status = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.status

    @staticmethod
    def get_default_payment_status():
        status, _ = PaymentStatus.objects.get_or_create(status="Pending")
        return status.id


class PaymentDetails(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("COD", "Cash on Delivery"),
        ("razorpay", "Online Payment (Razorpay)"),
        ("Wallet", "Wallet Payment"),
    ]
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    razorpay_order_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    payment_status = models.ForeignKey(
        PaymentStatus, on_delete=models.SET_NULL, null=True, default=PaymentStatus.get_default_payment_status
    )


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    address = models.ForeignKey(Address, on_delete=models.CASCADE)
    order_id = models.CharField(max_length=100, editable=False, unique=True)
    payment_details = models.OneToOneField(PaymentDetails, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.ForeignKey(OrderStatus, on_delete=models.CASCADE, default=OrderStatus.get_default_status)
    is_cancelled = models.BooleanField(default=False)
    canceled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="canceled_orders"
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=100, null=True, blank=True)
    is_returned = models.BooleanField(default=False)
    return_reason = models.CharField(max_length=255, null=True, blank=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  

    def save(self, *args, **kwargs):
        # Ensure a unique order ID is generated only for new orders
        if not self.order_id:
            self.order_id = self.generate_order_id()

        # Handle status updates
        if self.is_cancelled and not self.status.status.lower() == 'cancelled':
            cancelled_status, _ = OrderStatus.objects.get_or_create(status="Cancelled")
            self.status = cancelled_status

        if self.is_returned and not self.status.status.lower() == 'returned':
            returned_status, _ = OrderStatus.objects.get_or_create(status="Returned")
            self.status = returned_status

        super().save(*args, **kwargs)

    def generate_order_id(self):
        """
        Generate a unique order ID based on the current year and an incremental number.
        Format: ORD<year><5-digit-incremental-number>
        """
        current_year = timezone.now().year
        last_order = Order.objects.filter(created_at__year=current_year).order_by('id').last()
        try:
            if last_order:
                last_id_number = int(last_order.order_id[-5:])
                new_id_number = last_id_number + 1
            else:
                new_id_number = 10001
            return f"ORD{current_year}{new_id_number:05d}"
        except (ValueError, AttributeError):
            raise ValueError("Error generating order ID. Please check existing order IDs.")

    def total_amount(self):
        return self.items.aggregate(total=models.Sum(models.F("quantity") * models.F("price")))["total"] or 0

    def mark_as_refunded(self):
        refunded_status, _ = OrderStatus.objects.get_or_create(status="Refunded")
        self.status = refunded_status
        if self.payment_details:
            refunded_payment_status, _ = PaymentStatus.objects.get_or_create(status="Refunded")
            self.payment_details.payment_status = refunded_payment_status
            self.payment_details.save()
        self.save()


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, related_name="order_items", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.price = self.variant.price
            self.variant.decrease_stock(self.quantity)
        super().save(*args, **kwargs)

    def total_price(self):
        return self.price * self.quantity


class OrderRefund(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    refund_reason = models.TextField(null=True, blank=True)
    refunded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.amount > self.order.total_amount():
            raise ValidationError("Refund amount cannot exceed the order total.")
        self.order.mark_as_refunded()
        super().save(*args, **kwargs)
