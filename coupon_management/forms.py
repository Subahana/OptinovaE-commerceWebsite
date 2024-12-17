from django import forms
from .models import Coupon
from django.utils import timezone

class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = ['code', 'coupon_type', 'discount_percentage', 'discount_amount', 'valid_from', 'valid_to', 'active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Dynamically set fields as optional or required based on coupon type
        self.fields['discount_percentage'].required = False
        self.fields['discount_amount'].required = False

    def clean_code(self):
        """Ensure the coupon code is unique."""
        code = self.cleaned_data.get('code')
        if Coupon.objects.filter(code=code).exclude(id=self.instance.pk if self.instance else None).exists():
            raise forms.ValidationError("This coupon code already exists. Please choose a unique code.")
        return code

    def clean(self):
        """Perform validations on fields based on the coupon type."""
        cleaned_data = super().clean()
        coupon_type = cleaned_data.get('coupon_type')
        discount_percentage = cleaned_data.get('discount_percentage')
        discount_amount = cleaned_data.get('discount_amount')
        valid_from = cleaned_data.get('valid_from')
        valid_to = cleaned_data.get('valid_to')

        if coupon_type == 'percentage':
            if not discount_percentage:
                self.add_error('discount_percentage', "Discount percentage is required for a percentage-based coupon.")
            elif not (0 < discount_percentage <= 100):
                self.add_error('discount_percentage', "Discount percentage must be between 1 and 100.")

        elif coupon_type == 'fixed':
            if not discount_amount:
                self.add_error('discount_amount', "Discount amount is required for a fixed amount coupon.")
            elif discount_amount <= 0:
                self.add_error('discount_amount', "Discount amount must be greater than 0.")

        if valid_from and valid_to:
            if valid_from > valid_to:
                self.add_error('valid_from', "Start date must be earlier than the end date.")
                self.add_error('valid_to', "End date must be later than the start date.")

        return cleaned_data

    def save(self, commit=True):
        """Handle additional logic before saving the instance."""
        instance = super().save(commit=False)

        # Automatically deactivate the coupon if the valid_to date is in the past
        if instance.valid_to and instance.valid_to < timezone.now():
            instance.active = False

        if commit:
            instance.save()
        return instance
