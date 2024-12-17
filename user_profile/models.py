from django.db import models
from django.contrib.auth import get_user_model
from django.utils.timezone import now

User = get_user_model()

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pin_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)  # For soft delete
    deleted_at = models.DateTimeField(null=True, blank=True)  # Optional timestamp for deletion

    def soft_delete(self):
        """Mark the address as deleted."""
        self.is_deleted = True
        self.deleted_at = now()
        self.save()

    def restore(self):
        """Restore a soft-deleted address."""
        self.is_deleted = False
        self.deleted_at = None
        self.save()

    def __str__(self):
        return f"{self.street}, {self.city}, {self.state}, {self.country}"
