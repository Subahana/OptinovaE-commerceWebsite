from django.conf import settings
from django.db import models
from decimal import Decimal

class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    def __str__(self):
        return f"Wallet of {self.user.username} - Balance: {self.balance}"
   
class WalletTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ]
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    wallet = models.ForeignKey('Wallet', on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    date = models.DateTimeField(auto_now_add=True)


    def save(self, *args, **kwargs):
        if self.pk is None:  # Only update on creation
            amount = Decimal(self.amount)
            if self.transaction_type == 'debit':
                if self.wallet.balance < amount:
                    raise ValueError("Insufficient balance in wallet for this transaction.")
                self.wallet.balance -= amount
            elif self.transaction_type == 'credit':
                self.wallet.balance += amount
            self.wallet.save()
        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.transaction_type.capitalize()} - {self.amount} for {self.description}"
