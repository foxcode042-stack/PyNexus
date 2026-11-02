from django.conf import settings
from django.db import models


class EmailVerificationCode(models.Model):
    PURPOSE_CHOICES = [
        ("signup", "Signup"),
        ("login", "Login"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verification_codes",
    )
    purpose = models.CharField(max_length=12, choices=PURPOSE_CHOICES)
    code_hash = models.CharField(max_length=128)
    remember_device = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "purpose", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.get_username()} ({self.purpose})"


class NewsletterSubscription(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.email


class StudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )
    full_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    country = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    occupation = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=200, blank=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    location_accuracy = models.FloatField(blank=True, null=True)
    location_captured_at = models.DateTimeField(blank=True, null=True)
    nationality = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    parent_name = models.CharField(max_length=150, blank=True)
    parent_phone = models.CharField(max_length=30, blank=True)
    parent_email = models.EmailField(blank=True)
    bio = models.CharField(max_length=600, blank=True)

    def __str__(self) -> str:
        return self.full_name or self.user.get_username()


class Payment(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Paid", "Paid"),
        ("Failed", "Failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="academy_payments",
    )
    transaction_reference = models.CharField(max_length=100, unique=True)
    plan_id = models.CharField(max_length=30)
    plan_name = models.CharField(max_length=100)
    fee = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending",
    )
    paid_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user.get_username()} - {self.plan_name} ({self.status})"


class Work(models.Model):
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to="works/%Y/%m/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return self.title
