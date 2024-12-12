from django import forms
from .models import Coupon
from django.utils import timezone
from products.models import Product  

class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = ['code', 'coupon_type', 'discount_percentage', 'discount_amount', 'valid_from', 'valid_to', 'active', ]

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.get('instance', None)  # Capture instance if editing
        super().__init__(*args, **kwargs)

        # Dynamically hide unused fields based on the coupon type
        if self.instance and self.instance.coupon_type:
            self.fields['discount_percentage'].required = False
            self.fields['discount_amount'].required = False
      

    def clean_code(self):
        code = self.cleaned_data['code']

        # Check if the code is unique, accounting for whether this is a new coupon or being edited
        if self.instance:
            if Coupon.objects.filter(code=code).exclude(id=self.instance.id).exists():
                raise forms.ValidationError("Coupon code must be unique.")
        else:
            if Coupon.objects.filter(code=code).exists():
                raise forms.ValidationError("Coupon code must be unique.")

        return code

    def clean(self):
        cleaned_data = super().clean()
        coupon_type = cleaned_data.get('coupon_type')

        # Validate based on the coupon type
        if coupon_type == 'percentage':
            discount_percentage = cleaned_data.get('discount_percentage')
            if not discount_percentage:
                raise forms.ValidationError("For percentage discount, a discount percentage is required.")
            if discount_percentage <= 0 or discount_percentage > 100:
                raise forms.ValidationError("Discount percentage must be between 1 and 100.")

        elif coupon_type == 'fixed':
            discount_amount = cleaned_data.get('discount_amount')
            if not discount_amount:
                raise forms.ValidationError("For fixed amount discount, a discount amount is required.")
            if discount_amount <= 0:
                raise forms.ValidationError("Discount amount must be greater than 0.")

        # Validate date range
        valid_from = cleaned_data.get('valid_from')
        valid_to = cleaned_data.get('valid_to')
        if valid_from and valid_to and valid_from > valid_to:
            raise forms.ValidationError("Valid from date must be earlier than the valid to date.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Deactivate the coupon if the expiration date is in the past
        if instance.valid_to and instance.valid_to < timezone.now():
            instance.active = False
        
        if commit:
            instance.save()
        return instance
