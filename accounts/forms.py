from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
import re

CustomUser = get_user_model()

class UserSignupForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={"placeholder": "First Name"}),
        required=True,
        help_text='Required. 30 characters or fewer.'
    )
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={"placeholder": "Last Name"}),
        required=True,
        help_text='Required. 30 characters or fewer.'
    )
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={"placeholder": "Email"}),
        required=True,
        help_text='Required. Enter a valid email address.'
    )
    username = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={"placeholder": "Username"}),
        required=True,
        help_text='Required. 30 characters or fewer.'
    )

    class Meta:
        model = CustomUser  # Use the custom user model
        fields = ('first_name', 'last_name', 'username', 'email', 'password1', 'password2')

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not re.match("^[A-Za-z]+$", first_name):
            raise forms.ValidationError("First name should contain only letters.")
        if len(first_name) > 30:
            raise forms.ValidationError("First name should be 30 characters or fewer.")
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if not re.match("^[A-Za-z]+$", last_name):
            raise forms.ValidationError("Last name should contain only letters.")
        if len(last_name) > 30:
            raise forms.ValidationError("Last name should be 30 characters or fewer.")
        return last_name

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Check if the email format is correct
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
            raise forms.ValidationError("Enter a valid email address.")
        # Check if the email is already in use
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not re.match("^[A-Za-z0-9_]+$", username):
            raise forms.ValidationError("Username can only contain letters, numbers, and underscores.")
        if len(username) < 3 or len(username) > 30:
            raise forms.ValidationError("Username must be between 3 and 30 characters.")
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with that username already exists.")
        return username



