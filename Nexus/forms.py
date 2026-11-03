import re
from datetime import date

import phonenumbers
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from django_countries import countries

from .models import StudentProfile


COUNTRY_CHOICES = [("", "Select a country"), *list(countries)]
COUNTRY_NAME_BY_CODE = dict(countries)
OCCUPATION_CHOICES = (
    ("", "Select an occupation"),
    ("student", "Student"),
    ("employed", "Employed / worker"),
    ("self_employed", "Self-employed / freelancer"),
    ("unemployed", "Unemployed"),
    ("homemaker", "Homemaker"),
    ("independent_learner", "Independent learner"),
    ("other", "Other"),
)


class StudentSignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone_number = forms.CharField(max_length=30)
    country = forms.ChoiceField(choices=COUNTRY_CHOICES)
    zip_code = forms.CharField(max_length=20)
    occupation = forms.ChoiceField(choices=OCCUPATION_CHOICES)
    state = forms.CharField(max_length=100)
    location = forms.CharField(max_length=200)
    date_of_birth = forms.DateField(
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    nationality = forms.ChoiceField(choices=COUNTRY_CHOICES)
    terms_accepted = forms.BooleanField(required=True)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "country",
            "zip_code",
            "occupation",
            "state",
            "location",
            "date_of_birth",
            "nationality",
            "terms_accepted",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        labels = {
            "username": "Username",
            "first_name": "First name",
            "last_name": "Last name",
            "email": "Email address",
            "phone_number": "Phone number",
            "country": "Country",
            "zip_code": "Zip code",
            "occupation": "Occupation",
            "state": "State / region",
            "location": "City or location",
            "date_of_birth": "Date of birth",
            "nationality": "Nationality",
            "terms_accepted": "I agree to the Terms and Conditions and Privacy Policy",
        }
        for field_name, label in labels.items():
            self.fields[field_name].label = label
        for field in self.fields.values():
            field.widget.attrs["autocomplete"] = "off"
            field.widget.attrs["class"] = "account-input"
        self.fields["username"].widget.attrs["autocomplete"] = "username"
        self.fields["first_name"].widget.attrs["autocomplete"] = "given-name"
        self.fields["last_name"].widget.attrs["autocomplete"] = "family-name"
        self.fields["email"].widget.attrs["autocomplete"] = "email"
        self.fields["phone_number"].widget.attrs.update(
            {"autocomplete": "tel", "type": "tel", "inputmode": "tel"}
        )
        self.fields["country"].widget.attrs["autocomplete"] = "country"
        self.fields["zip_code"].widget.attrs["autocomplete"] = "postal-code"
        self.fields["state"].widget.attrs["autocomplete"] = "address-level1"
        self.fields["location"].widget.attrs["autocomplete"] = "address-level2"
        self.fields["date_of_birth"].widget.attrs["autocomplete"] = "bday"
        self.fields["password1"].widget.attrs["autocomplete"] = "new-password"
        self.fields["password2"].widget.attrs["autocomplete"] = "new-password"
        self.fields["terms_accepted"].widget.attrs["class"] = "account-checkbox"

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].strip()
        user_model = get_user_model()
        if user_model.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_phone_number(self) -> str:
        value = self.cleaned_data["phone_number"].strip()
        country_code = self.cleaned_data.get("country") or self.data.get(
            self.add_prefix("country")
        )
        try:
            phone = phonenumbers.parse(value, country_code or None)
        except phonenumbers.NumberParseException as exc:
            raise forms.ValidationError(
                "Enter a valid phone number, including its country code if needed."
            ) from exc
        if not phonenumbers.is_valid_number(phone):
            raise forms.ValidationError(
                "Enter a valid phone number for the selected country."
            )
        return phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.E164)

    def clean_zip_code(self) -> str:
        value = self.cleaned_data["zip_code"].strip()
        country_code = self.cleaned_data.get("country")
        if country_code == "US" and not re.fullmatch(r"\d{5}(?:-\d{4})?", value):
            raise forms.ValidationError("Enter a valid US ZIP code (for example, 90210).")
        if country_code == "NG" and not re.fullmatch(r"\d{6}", value):
            raise forms.ValidationError("Enter a valid 6-digit Nigerian postal code.")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 -]{0,19}", value):
            raise forms.ValidationError("Enter a valid postal or ZIP code.")
        return value

    def clean_date_of_birth(self) -> date:
        value = self.cleaned_data["date_of_birth"]
        if value > date.today():
            raise forms.ValidationError("Date of birth cannot be in the future.")
        return value

    def save(self, commit: bool = True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data["last_name"].strip()
        user.email = self.cleaned_data["email"]
        user.is_active = False
        if commit:
            user.save()
            profile, _ = StudentProfile.objects.get_or_create(user=user)
            profile.full_name = f"{user.first_name} {user.last_name}".strip() or user.username
            profile.phone = self.cleaned_data["phone_number"]
            profile.country = COUNTRY_NAME_BY_CODE[self.cleaned_data["country"]]
            profile.state = self.cleaned_data["state"].strip()
            profile.zip_code = self.cleaned_data["zip_code"].strip()
            profile.occupation = dict(OCCUPATION_CHOICES)[self.cleaned_data["occupation"]]
            profile.location = self.cleaned_data["location"].strip()
            profile.nationality = COUNTRY_NAME_BY_CODE[self.cleaned_data["nationality"]]
            profile.address = profile.location
            profile.date_of_birth = self.cleaned_data["date_of_birth"]
            profile.terms_accepted_at = timezone.now()
            profile.save()
        return user
