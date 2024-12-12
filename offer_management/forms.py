# forms.py
from django import forms
from django.utils import timezone
from .models import CategoryOffer

class CategoryOfferForm(forms.ModelForm):
    class Meta:
        model = CategoryOffer
        fields = ['category', 'discount_percent', 'start_date', 'end_date', 'is_active']
    
    def clean_discount_percent(self):
        discount = self.cleaned_data.get('discount_percent')
        if discount is not None and (discount < 0 or discount > 100):
            raise forms.ValidationError("Discount percent must be between 0 and 100.")
        return discount
    
    def clean_start_date(self):
        start_date = self.cleaned_data.get('start_date')
        if start_date is None:
            raise forms.ValidationError("Start date is required.")
        if start_date < timezone.now().date():
            raise forms.ValidationError("Start date cannot be in the past.")
        return start_date
    
    def clean_end_date(self):
        end_date = self.cleaned_data.get('end_date')
        if end_date is None:
            raise forms.ValidationError("End date is required.")
        return end_date
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        # Only check start and end date order if both are present
        if start_date and end_date:
            if start_date > end_date:
                self.add_error('end_date', "End date must be after the start date.")
