from django import forms
from .models import Brand
import re  # For regex-based validation

class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ['name', 'description']
    # Adding placeholders using widgets
    def __init__(self, *args, **kwargs):
        super(BrandForm, self).__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({
            'placeholder': 'Enter brand name',
            'class': 'form-control',  # Optional class to style the field
        })
        self.fields['description'].widget.attrs.update({
            'placeholder': 'Provide a brief brand description',
            'class': 'form-control',  # Optional class to style the field
        })
    # Enhanced field-specific validation for 'name'
    def clean_name(self):
        name = self.cleaned_data.get('name')

        # 1. Check if the name is empty or None
        if not name:
            raise forms.ValidationError('Brand name is required.')

        # 2. Check for minimum and maximum length
        if len(name) < 3:
            raise forms.ValidationError('Brand name must be at least 3 characters long.')
        if len(name) > 50:
            raise forms.ValidationError('Brand name must not exceed 50 characters.')

        # 3. Check for alphanumeric characters only (can include spaces between words)
        if not re.match(r'^[a-zA-Z0-9 ]+$', name):
            raise forms.ValidationError('Brand name can only contain letters, numbers, and spaces.')

        # 4. Strip leading and trailing whitespaces and check
        name = name.strip()
        if not name:
            raise forms.ValidationError('Brand name cannot be just whitespace.')

        # 5. Check for any prohibited characters (e.g., special characters like @, $, etc.)
        prohibited_characters = ['@', '#', '$', '%', '^', '&', '*', '(', ')', '!', '~', '`']
        if any(char in name for char in prohibited_characters):
            raise forms.ValidationError('Brand name contains invalid characters: @, #, $, %, ^, &, *, etc.')

        # 6. Ensure the name is unique in the database
        if Brand.objects.filter(name=name).exists():
            raise forms.ValidationError('A brand with this name already exists.')

        return name

    # Validation for 'description' field
    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description and len(description) > 500:
            raise forms.ValidationError('Description cannot exceed 500 characters.')
        return description
