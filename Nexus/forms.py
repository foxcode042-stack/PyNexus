from datetime import date

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import StudentProfile


class StudentSignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone_number = forms.CharField(max_length=30)
    country = forms.CharField(max_length=80)
    zip_code = forms.CharField(max_length=20)
    occupation = forms.CharField(max_length=120)
    state = forms.CharField(max_length=100)
    location = forms.CharField(max_length=200)
    dob_day = forms.IntegerField(min_value=1, max_value=31)
    dob_month = forms.IntegerField(min_value=1, max_value=12)
    dob_year = forms.IntegerField(min_value=1900, max_value=2100)
    nationality = forms.CharField(max_length=100)

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
            "dob_day",
            "dob_month",
            "dob_year",
            "nationality",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Username"
        self.fields["first_name"].label = "First name"
        self.fields["last_name"].label = "Last name"
        self.fields["email"].label = "Email address"
        self.fields["phone_number"].label = "Phone number"
        self.fields["country"].label = "Country"
        self.fields["zip_code"].label = "Zip code"
        self.fields["occupation"].label = "Occupation"
        self.fields["state"].label = "State"
        self.fields["location"].label = "Location"
        self.fields["dob_day"].label = "Day of birth"
        self.fields["dob_month"].label = "Month of birth"
        self.fields["dob_year"].label = "Year of birth"
        self.fields["nationality"].label = "Nationality"
        for field in self.fields.values():
            field.widget.attrs["autocomplete"] = "off"
            field.widget.attrs["class"] = "account-input"
        self.fields["username"].widget.attrs["autocomplete"] = "username"
        self.fields["first_name"].widget.attrs["autocomplete"] = "given-name"
        self.fields["last_name"].widget.attrs["autocomplete"] = "family-name"
        self.fields["email"].widget.attrs["autocomplete"] = "email"
        self.fields["phone_number"].widget.attrs["autocomplete"] = "tel"
        self.fields["country"].widget.attrs["autocomplete"] = "country-name"
        self.fields["zip_code"].widget.attrs["autocomplete"] = "postal-code"
        self.fields["state"].widget.attrs["autocomplete"] = "address-level1"
        self.fields["location"].widget.attrs["autocomplete"] = "street-address"
        self.fields["password1"].widget.attrs["autocomplete"] = "new-password"
        self.fields["password2"].widget.attrs["autocomplete"] = "new-password"

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].strip()
        user_model = get_user_model()
        if user_model.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data is None:
            return {}
        year = cleaned_data.get("dob_year")
        month = cleaned_data.get("dob_month")
        day = cleaned_data.get("dob_day")
        if any(value is not None for value in (year, month, day)) and not all(
            value is not None for value in (year, month, day)
        ):
            raise forms.ValidationError(
                "Please complete your date of birth with a day, month, and year."
            )
        if year is not None and month is not None and day is not None:
            try:
                    cleaned_data["date_of_birth"] = date(int(year), int(month), int(day))
            except ValueError:
                raise forms.ValidationError("The date of birth you entered is invalid.")
        return cleaned_data

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
            profile.phone = self.cleaned_data.get("phone_number", "").strip()
            profile.country = self.cleaned_data.get("country", "").strip()
            profile.state = self.cleaned_data.get("state", "").strip()
            profile.zip_code = self.cleaned_data.get("zip_code", "").strip()
            profile.occupation = self.cleaned_data.get("occupation", "").strip()
            profile.location = self.cleaned_data.get("location", "").strip()
            profile.nationality = self.cleaned_data.get("nationality", "").strip()
            profile.address = profile.location
            profile.date_of_birth = self.cleaned_data.get("date_of_birth")
            profile.save()
        return user