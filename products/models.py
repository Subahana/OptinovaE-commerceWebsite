from django.db import models
from PIL import Image
from django.core.exceptions import ValidationError
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
from brand_management.models import Brand
from django.utils import timezone
from django.apps import apps
from decimal import Decimal

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(default='')
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, related_name='products', null=True, blank=True)  # Update here
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    @property
    def main_variant(self):
        return self.variants.filter(is_main_variant=True).first()

    @property
    def price(self):
        main_variant = self.main_variant
        return main_variant.price if main_variant else self.base_price

    def main_image(self):
        main_variant = self.main_variant
        if main_variant:
            image = main_variant.images.first()
            return image.image.url if image else 'default_image.png'
        return 'default_image.png'

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    color = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    is_main_variant = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['product', 'color'], name='unique_product_color')
        ]

    def __str__(self):
        return f'{self.product.name} - {self.color}'

    @property
    def is_sold_out(self):
        return self.stock <= 0

    def save(self, *args, **kwargs):
        if self.is_main_variant:
            # Ensure only one main variant exists
            ProductVariant.objects.filter(product=self.product, is_main_variant=True).update(is_main_variant=False)
        super().save(*args, **kwargs)

    def decrease_stock(self, quantity):
        if self.stock >= quantity:
            self.stock -= quantity
            self.save()
        else:
            raise ValueError('Not enough stock available')

    def increase_stock(self, quantity):
        self.stock += quantity
        self.save()

    def clean(self):
        if self.stock < 0:
            raise ValidationError('Stock cannot be negative.')

    def get_discounted_price(self):
        # Base price of the variant
        base_price = self.price

        # Get any active offers applicable to this variant
        offers = self.product.category.offers.filter(is_active=True)

        # Apply the highest discount
        discount_amount = Decimal('0.00')
        for offer in offers:
            if offer.discount_percent:
                discount_amount = max(discount_amount, (base_price * offer.discount_percent) / Decimal('100'))

        # Calculate the discounted price
        discounted_price = base_price - discount_amount
        return discounted_price if discounted_price > 0 else base_price

    @property
    def main_image(self):
        image = self.images.first()
        return image.image.url if image else 'default_image.png'

class ProductImage(models.Model):
    variant = models.ForeignKey('ProductVariant', on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/', max_length=500)

    def __str__(self):
        return f'Image for {self.variant.product.name} ({self.variant.color})'

    def save(self, *args, **kwargs):
        # Call the original save method
        super().save(*args, **kwargs)
        # Resize the image only if necessary
        self.resize_image()

    def resize_image(self):
        try:
            # Open the image
            img = Image.open(self.image)

            # Set output size
            output_size = (800, 800)

            # Only resize if the image is larger than the output size
            if img.height > output_size[1] or img.width > output_size[0]:
                # Create a BytesIO stream for the resized image
                img.thumbnail(output_size)
                img_format = img.format

                output = BytesIO()
                img.save(output, format=img_format)
                output.seek(0)

                # Create a new InMemoryUploadedFile
                self.image = InMemoryUploadedFile(
                    output, 'ImageField', self.image.name, 
                    img_format.lower(), sys.getsizeof(output), None
                )

                # Save the resized image
                super().save()

        except Exception as e:
            print(f"Error resizing the image: {e}")
