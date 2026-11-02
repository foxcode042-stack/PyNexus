import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.test import override_settings
from django.utils import timezone
from django.urls import reverse

from .models import EmailVerificationCode, NewsletterSubscription, Payment


class AcademyPageTests(TestCase):
    def test_homepage_renders_django_template_and_first_visit_guide(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tech-Nexus Academy")
        self.assertContains(response, 'id="welcome-dialog"')
        self.assertContains(response, 'id="theme-toggle"')
        self.assertContains(response, 'Nexus/tech-nexus-logo.jpg')
        self.assertContains(response, "images.unsplash.com")
        self.assertContains(response, 'id="project-carousel"')
        self.assertContains(response, "data-carousel-next")
        self.assertContains(response, "paystack.shop/pay/8bye9mv3x-")
        self.assertContains(response, reverse("careers"))
        self.assertContains(response, reverse("sitemap"))
        for page_name in ("courses", "programmes", "enrolment", "payments", "register", "login"):
            self.assertContains(response, reverse(page_name))

    def test_requested_information_pages_are_available(self):
        page_names = (
            "about",
            "contact",
            "courses",
            "programmes",
            "enrolment",
            "payments",
            "password_reset",
            "enrolment_agreement",
            "refunds",
            "attendance",
            "code_of_conduct",
            "certificates",
            "student_projects",
            "acceptable_use",
            "careers",
            "cookies",
            "terms",
            "privacy",
            "faq",
            "help",
            "support",
            "sitemap",
        )

        for page_name in page_names:
            with self.subTest(page=page_name):
                response = self.client.get(reverse(page_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Nexus/tech-nexus-logo.jpg')

    def test_terms_page_links_to_student_policy_pages(self):
        response = self.client.get(reverse("terms"))

        self.assertContains(response, reverse("enrolment_agreement"))
        self.assertContains(response, reverse("refunds"))
        self.assertContains(response, reverse("code_of_conduct"))

    def test_blog_routes_render_academy_posts(self):
        for route_name in ("blog", "blogs"):
            with self.subTest(route=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Tech-Nexus knowledge centre")
                self.assertContains(response, "Build Your First Django REST API From Scratch")
                self.assertContains(response, "JavaScript Async/Await, Finally Explained")
                self.assertContains(response, "Cybersecurity")
                self.assertContains(response, "data-blog-search")
                self.assertContains(response, "data-category=")
                self.assertContains(response, "data-reader-content")
                self.assertContains(response, "data-newsletter-form")
                self.assertContains(response, 'Nexus/blog.js')

    def test_blog_newsletter_api_validates_and_deduplicates_emails(self):
        response = self.client.post(
            reverse("api_blog_newsletter"),
            data={"email": "not-an-email"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(NewsletterSubscription.objects.count(), 0)

        payload = {"email": "reader@example.com"}
        response = self.client.post(
            reverse("api_blog_newsletter"),
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["subscribed"])
        self.assertEqual(NewsletterSubscription.objects.count(), 1)

        response = self.client.post(
            reverse("api_blog_newsletter"),
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(NewsletterSubscription.objects.count(), 1)

    def test_blog_index_and_reader_are_accessible_without_javascript(self):
        response = self.client.get(reverse("blog"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Permission comes first")
        self.assertContains(response, "CourseSerializer")
        self.assertContains(response, "blog-category")

    def test_ai_chat_widget_is_available_on_site_pages(self):
        for route_name in (
            "home",
            "about",
            "contact",
            "blog",
            "login",
            "register",
            "dashboard",
            "sitemap",
            "password_reset",
            "verification_sent",
        ):
            with self.subTest(page=route_name):
                response = self.client.get(reverse(route_name), follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'data-ai-chat-widget')
                self.assertContains(response, 'data-widget-toggle')
                self.assertContains(response, 'Nexus/ai_tutor.js')

        self.assertEqual(self.client.get("/ai-tutor/").status_code, 404)

    def test_contact_page_posts_validated_enquiries_to_academy_email(self):
        payload = {
            "full_name": "Ada Lovelace",
            "email": "ada@example.com",
            "phone_number": "+2348012345678",
            "category": "technical_support",
            "subject": "Help with my account",
            "message": "I need help signing in.",
        }
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            invalid = self.client.post(
                reverse("api_contact_enquiries"),
                data={**payload, "email": "not-an-email"},
                content_type="application/json",
            )
            self.assertEqual(invalid.status_code, 400)
            self.assertEqual(len(mail.outbox), 0)

            response = self.client.post(
                reverse("api_contact_enquiries"),
                data=payload,
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 201)
        self.assertRegex(response.json()["reference"], r"^TNX-[0-9A-F]{6}$")
        self.assertEqual(mail.outbox[0].to, ["technonexusacademy@gmail.com"])
        self.assertEqual(mail.outbox[0].reply_to, ["ada@example.com"])
        self.assertIn("I need help signing in.", mail.outbox[0].body)
        self.assertEqual(self.client.get(reverse("api_contact_enquiries")).status_code, 405)

    def test_about_and_policy_pages_use_their_updated_content_styles(self):
        about = self.client.get(reverse("about"))
        self.assertContains(about, "Our founder")
        self.assertContains(about, "prose-copy")
        self.assertContains(about, "about-reveal")

        terms = self.client.get(reverse("terms"))
        self.assertContains(terms, "Accounts and learning materials")
        self.assertContains(terms, "terms-copy")

        privacy = self.client.get(reverse("privacy"))
        self.assertContains(privacy, "Information collected")
        self.assertContains(privacy, "privacy-copy")

    def test_ai_tutor_api_returns_level_aware_preview_and_validates_payload(self):
        response = self.client.post(
            reverse("api_ai_chat"),
            data={
                "messages": [{"role": "user", "content": "Show me a Python loop"}],
                "learning_level": "Beginner",
                "attachment": {
                    "name": "example.py",
                    "type": "text/x-python",
                    "content": "for item in items:\n    print(item)",
                },
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["mode"], "preview")
        self.assertIn("beginner-friendly Python example", response.json()["message"])
        self.assertIn("example.py", response.json()["message"])

        for payload in (
            {"messages": [], "learning_level": "Beginner", "attachment": None},
            {
                "messages": [{"role": "system", "content": "invalid role"}],
                "learning_level": "Beginner",
                "attachment": None,
            },
            {
                "messages": [{"role": "user", "content": "Help me"}],
                "learning_level": "Expert",
                "attachment": None,
            },
            {
                "messages": [{"role": "user", "content": "Help me"}],
                "learning_level": "Beginner",
                "attachment": {
                    "name": "large.txt",
                    "type": "text/plain",
                    "content": "x" * 100_001,
                },
            },
        ):
            with self.subTest(payload=payload):
                invalid_response = self.client.post(
                    reverse("api_ai_chat"),
                    data=payload,
                    content_type="application/json",
                )
                self.assertEqual(invalid_response.status_code, 400)
                self.assertIn("detail", invalid_response.json())

        self.assertEqual(self.client.get(reverse("api_ai_chat")).status_code, 405)

    def test_auth_pages_use_the_rebuilt_client_auth_surface(self):
        registration = self.client.get(reverse("register"))
        self.assertEqual(registration.status_code, 200)
        self.assertContains(registration, 'data-auth-register')
        self.assertContains(registration, 'data-capture-location')
        self.assertContains(registration, 'name="password2"')
        self.assertContains(registration, 'data-api-base="/api"')

        sign_in = self.client.get(reverse("login"))
        self.assertEqual(sign_in.status_code, 200)
        self.assertContains(sign_in, 'data-auth-login')
        self.assertContains(sign_in, 'data-show-forgot')
        self.assertContains(sign_in, 'name="remember"')

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_registration_requires_email_verification_and_saves_student_profile(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('dashboard')}",
            fetch_redirect_response=False,
        )

        response = self.client.post(
            reverse("register"),
            {
                "username": "newstudent",
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": "ada@example.com",
                "phone_number": "+2348012345678",
                "country": "Nigeria",
                "zip_code": "540001",
                "occupation": "Student",
                "state": "Cross River",
                "location": "Calabar",
                "dob_day": "10",
                "dob_month": "12",
                "dob_year": "2000",
                "nationality": "Nigerian",
                "password1": "Zebra!Mountain7224",
                "password2": "Zebra!Mountain7224",
            },
        )
        self.assertRedirects(response, reverse("verification_sent"), fetch_redirect_response=False)
        user = get_user_model().objects.get(username="newstudent")
        self.assertFalse(user.is_active)
        profile = user.student_profile
        self.assertEqual(profile.country, "Nigeria")
        self.assertEqual(profile.state, "Cross River")
        self.assertEqual(profile.zip_code, "540001")
        self.assertEqual(profile.location, "Calabar")
        self.assertEqual(profile.nationality, "Nigerian")
        self.assertEqual(str(profile.date_of_birth), "2000-12-10")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ada@example.com"])

        response = self.client.post(
            reverse("login"),
            {"username": "newstudent", "password": "Zebra!Mountain7224"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

        match = re.search(
            r"/verify-email/([A-Za-z0-9_-]+)/([A-Za-z0-9_-]+)/",
            mail.outbox[0].body,
        )
        self.assertIsNotNone(match)
        uidb64, token = match.groups()
        response = self.client.get(
            reverse("verify_email", kwargs={"uidb64": uidb64, "token": token})
        )
        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

        response = self.client.post(
            reverse("login"),
            {"username": "newstudent", "password": "Zebra!Mountain7224"},
        )
        self.assertRedirects(
            response,
            reverse("verification_sent"),
            fetch_redirect_response=False,
        )
        self.assertEqual(len(mail.outbox), 2)
        login_code = re.search(
            r"verification code is (\d{6})",
            mail.outbox[-1].body,
        ).group(1)
        response = self.client.post(
            reverse("api_auth_verify_email"),
            data={"email": "ada@example.com", "code": login_code},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["verified"])
        self.assertEqual(response.json()["redirect_url"], reverse("dashboard"))
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)
        dashboard_response = self.client.get(reverse("dashboard"))
        self.assertContains(dashboard_response, "Programme checkout")
        self.assertContains(dashboard_response, "TNX-")
        self.assertContains(dashboard_response, "Course activity tracking is not connected")
        self.assertContains(dashboard_response, "No payment records yet")
        self.assertContains(dashboard_response, "dashboard.js")

        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        self.assertRedirects(
            self.client.get(reverse("dashboard")),
            f"{reverse('login')}?next={reverse('dashboard')}",
            fetch_redirect_response=False,
        )

    def test_invalid_email_verification_link_is_rejected(self):
        response = self.client.get(
            reverse(
                "verify_email",
                kwargs={"uidb64": "invalid", "token": "invalid"},
            )
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "could not be verified", status_code=400)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_auth_api_registration_and_login_require_single_use_email_codes(self):
        response = self.client.post(
            reverse("api_auth_register"),
            data={
                "username": "gracehopper",
                "email": "grace@example.com",
                "first_name": "Grace",
                "last_name": "Hopper",
                "phone_number": "+2348012345678",
                "country": "Nigeria",
                "zip_code": "540001",
                "occupation": "Student",
                "state": "Cross River",
                "location": "Calabar",
                "latitude": 4.9517,
                "longitude": 8.3417,
                "location_accuracy": 18.5,
                "location_captured_at": "2026-11-01T21:40:00Z",
                "date_of_birth": "2000-12-10",
                "nationality": "Nigerian",
                "password": "Zebra!Mountain7224",
                "password_confirmation": "Zebra!Mountain7224",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["requires_verification"])
        self.assertTrue(response.json()["email_verification_required"])
        self.assertIn("detail", response.json())
        user = get_user_model().objects.get(username="gracehopper")
        self.assertFalse(user.is_active)
        self.assertEqual(user.student_profile.phone, "+2348012345678")
        self.assertEqual(user.student_profile.country, "Nigeria")
        self.assertEqual(str(user.student_profile.date_of_birth), "2000-12-10")
        self.assertEqual(user.student_profile.latitude, 4.9517)
        self.assertEqual(user.student_profile.longitude, 8.3417)
        self.assertEqual(user.student_profile.location_accuracy, 18.5)
        self.assertIsNotNone(user.student_profile.location_captured_at)

        signup_code = re.search(
            r"verification code is (\d{6})",
            mail.outbox[-1].body,
        ).group(1)
        response = self.client.post(
            reverse("api_auth_verify_email"),
            data={"email": "grace@example.com", "code": signup_code},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

        response = self.client.post(
            reverse("api_auth_login"),
            data={
                "identifier": "grace@example.com",
                "password": "Zebra!Mountain7224",
                "remember": True,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["requires_verification"])
        login_code = re.search(
            r"verification code is (\d{6})",
            mail.outbox[-1].body,
        ).group(1)

        response = self.client.post(
            reverse("api_auth_verify_email"),
            data={"email": "grace@example.com", "code": "not-the-code"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

        response = self.client.post(
            reverse("api_auth_verify_email"),
            data={"email": "grace@example.com", "code": login_code},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.json()["redirect_url"], reverse("dashboard"))
        self.assertGreater(self.client.session.get_expiry_age(), 60 * 60 * 24)

        response = self.client.post(
            reverse("api_auth_verify_email"),
            data={"email": "grace@example.com", "code": login_code},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_registration_api_validates_password_confirmation_and_location(self):
        registration = {
            "username": "safeuser",
            "email": "safe@example.com",
            "first_name": "Safe",
            "last_name": "Student",
            "phone_number": "+2348012345678",
            "country": "Nigeria",
            "zip_code": "540001",
            "occupation": "Student",
            "state": "Cross River",
            "location": "Calabar",
            "date_of_birth": "2000-12-10",
            "nationality": "Nigerian",
            "password": "Zebra!Mountain7224",
            "password_confirmation": "Different!Password7224",
        }
        response = self.client.post(
            reverse("api_auth_register"),
            data=registration,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("do not match", response.json()["detail"])
        self.assertFalse(get_user_model().objects.filter(username="safeuser").exists())

        registration["password_confirmation"] = registration["password"]
        registration.update({"latitude": 120, "longitude": 8})
        response = self.client.post(
            reverse("api_auth_register"),
            data=registration,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Latitude", response.json()["detail"])
        self.assertFalse(get_user_model().objects.filter(username="safeuser").exists())

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_auth_api_rejects_bad_credentials_and_limits_code_resends(self):
        user = get_user_model().objects.create_user(
            username="apiuser",
            password="Zebra!Mountain7224",
            email="apiuser@example.com",
            is_active=True,
        )
        response = self.client.post(
            reverse("api_auth_login"),
            data={"identifier": user.username, "password": "incorrect"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(mail.outbox, [])

        payload = {
            "identifier": user.username,
            "password": "Zebra!Mountain7224",
        }
        response = self.client.post(
            reverse("api_auth_login"),
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("api_auth_login"),
            data=payload,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 429)
        self.assertEqual(len(mail.outbox), 1)

    def test_auth_api_social_signin_reports_missing_provider_configuration(self):
        for provider in ("google", "github"):
            with self.subTest(provider=provider):
                response = self.client.get(f"/api/auth/{provider}/")
                self.assertEqual(response.status_code, 501)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_auth_api_rejects_expired_email_codes(self):
        user = get_user_model().objects.create_user(
            username="expiryuser",
            password="Zebra!Mountain7224",
            email="expiry@example.com",
            is_active=True,
        )
        self.client.post(
            reverse("api_auth_login"),
            data={"identifier": user.username, "password": "Zebra!Mountain7224"},
            content_type="application/json",
        )
        challenge = EmailVerificationCode.objects.get(
            user=user,
            purpose="login",
        )
        challenge.expires_at = timezone.now() - timedelta(minutes=1)
        challenge.save(update_fields=["expires_at"])

        response = self.client.post(
            reverse("api_auth_verify_email"),
            data={"email": user.email, "code": "123456"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout_other_devices_ends_only_other_user_sessions(self):
        user_model = get_user_model()
        student = user_model.objects.create_user(
            username="sessionstudent",
            password="Zebra!Mountain7224",
            email="sessions@example.com",
            is_active=True,
        )
        other_student = user_model.objects.create_user(
            username="othersessionstudent",
            password="Zebra!Mountain7224",
            email="other-sessions@example.com",
            is_active=True,
        )
        self.client.force_login(student)
        other_client = self.client_class()
        other_client.force_login(student)
        unrelated_client = self.client_class()
        unrelated_client.force_login(other_student)

        response = self.client.post(reverse("api_auth_logout_others"))

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.json()["sessions_ended"], 1)
        self.assertRedirects(
            other_client.get(reverse("dashboard")),
            f"{reverse('login')}?next={reverse('dashboard')}",
            fetch_redirect_response=False,
        )
        self.assertEqual(unrelated_client.get(reverse("dashboard")).status_code, 200)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_forgot_password_api_sends_a_working_reset_link(self):
        user = get_user_model().objects.create_user(
            username="resetuser",
            password="Zebra!Mountain7224",
            email="reset@example.com",
            is_active=True,
        )

        response = self.client.post(
            reverse("api_auth_forgot_password"),
            data={"email": user.email},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        match = re.search(
            r"http://testserver(/password-reset/[^\s]+)",
            mail.outbox[0].body,
        )
        self.assertIsNotNone(match)
        reset_url = match.group(1)
        response = self.client.post(
            reset_url,
            data={
                "new_password1": "Meadow!River8821",
                "new_password2": "Meadow!River8821",
            },
        )
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.check_password("Meadow!River8821"))

    def test_dashboard_shows_only_the_signed_in_students_saved_payments(self):
        user_model = get_user_model()
        student = user_model.objects.create_user(
            username="dashboardstudent",
            password="Secure!Passphrase7224",
            email="dashboard@example.com",
            first_name="Sam",
            is_active=True,
        )
        other_student = user_model.objects.create_user(
            username="anotherstudent",
            password="Secure!Passphrase7224",
            email="another@example.com",
            is_active=True,
        )
        Payment.objects.create(
            user=student,
            transaction_reference="TNX-PAY-001",
            plan_id="starter",
            plan_name="Starter",
            fee="60000.00",
            amount_paid="15000.00",
            status="Pending",
        )
        Payment.objects.create(
            user=other_student,
            transaction_reference="TNX-PAY-002",
            plan_id="mastery",
            plan_name="Mastery",
            fee="250000.00",
            amount_paid="250000.00",
            status="Paid",
        )
        self.client.force_login(student)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TNX-")
        self.assertContains(response, "TNX-PAY-001")
        self.assertContains(response, "₦15000.00")
        self.assertContains(response, "Pending")
        self.assertNotContains(response, "TNX-PAY-002")
        self.assertContains(response, 'id="dashboard-menu-toggle"')
        self.assertContains(response, 'id="dashboard-search-input"')
        self.assertContains(response, 'Nexus/tech-nexus-logo.jpg')
        self.assertContains(response, 'data-auth-logout')
        self.assertContains(response, 'data-logout-other-devices')

    def test_logout_rejects_get_requests(self):
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)

    def test_staff_administration_requires_staff_account(self):
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(
            username="student",
            password="Secure!Passphrase729",
        )
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("administration")).status_code, 302)

        user.is_staff = True
        user.save(update_fields=["is_staff"])
        response = self.client.get(reverse("administration"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Course, enrolment, payment")