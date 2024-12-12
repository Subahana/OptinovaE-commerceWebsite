from django.db import models

class Brand(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)  # New field for activation status

    def __str__(self):
        return self.name
