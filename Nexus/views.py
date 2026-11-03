import binascii
import json
import logging
import math
import re
import secrets
import smtplib
from datetime import date, timedelta

from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.id_token import verify_oauth2_token
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.core.mail import BadHeaderError, EmailMessage, send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.encoding import force_str
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.http import (
    url_has_allowed_host_and_scheme,
    urlsafe_base64_decode,
    urlsafe_base64_encode,
)

from .forms import StudentSignUpForm
from .models import EmailVerificationCode, NewsletterSubscription, StudentProfile


logger = logging.getLogger(__name__)


PAGE_CONTENT = {
    "about": {
        "title": "About Tech-Nexus Academy",
        "eyebrow": "Knowledge | Connection | Advancement",
        "intro": (
            "Tech-Nexus Academy is a technology learning community in "
            "Calabar, Cross River, Nigeria. We help aspiring developers build "
            "practical skills through hands-on learning."
        ),
        "sections": [
            {
                "heading": "Our mission",
                "paragraphs": [
                    "To provide accessible, structured, and practical technology "
                    "education that helps learners progress from programming "
                    "fundamentals to real-world projects and professional readiness."
                ],
            },
            {
                "heading": "Our vision and values",
                "paragraphs": [
                    "Our vision is to be a trusted technology learning community "
                    "where aspiring developers gain the knowledge, practical skills, "
                    "and creativity to contribute to the digital world.",
                    "Knowledge, connection, advancement, creativity, practical "
                    "learning, and continuous improvement guide the academy."
                ],
            },
            {
                "heading": "What we do",
                "paragraphs": [
                    "We are building practical technology programmes in web "
                    "development, programming, software development, and digital "
                    "product creation. Course availability and delivery format "
                    "depend on each upcoming cohort.",
                ],
            },
            {
                "heading": "Learning at Tech-Nexus",
                "paragraphs": [
                    "Our approach is centered on clear explanations, guided practice, "
                    "and projects that help learners apply each new concept. We aim "
                    "to make technology education welcoming to beginners while "
                    "supporting learners as they advance.",
                ],
            },
            {
                "heading": "Our founder",
                "paragraphs": [
                    "Tech-Nexus Academy was founded by Engineer Chimuanya Praise "
                    "Oluomachi to help more people gain practical skills and "
                    "confidence in technology.",
                ],
            },
        ],
    },
    "courses": {
        "title": "Courses",
        "eyebrow": "Planned learning areas",
        "intro": (
            "Explore the skills Tech-Nexus Academy plans to teach. Course "
            "availability and exact syllabuses depend on the upcoming cohort."
        ),
        "sections": [
            {
                "heading": "Web development",
                "paragraphs": [
                    "HTML, CSS, JavaScript, responsive design, interactive "
                    "websites, front-end development, and full-stack fundamentals."
                ],
            },
            {
                "heading": "Programming and software development",
                "paragraphs": [
                    "Planned languages include Python, Java, JavaScript, C++, "
                    "C#, PHP, and potentially Ruby, Swift, and Go. Software "
                    "topics may include databases, APIs, authentication, and "
                    "application design."
                ],
            },
            {
                "heading": "Design and emerging technology",
                "paragraphs": [
                    "UI/UX fundamentals and project-based learning are planned. "
                    "Advanced topics such as machine learning, cybersecurity, "
                    "systems programming, and API management depend on instructor "
                    "availability and programme scope."
                ],
            },
        ],
    },
    "programmes": {
        "title": "Training programmes",
        "eyebrow": "Proposed programmes and fees",
        "intro": (
            "The durations and fees below are proposed programme details from "
            "the academy profile, not confirmation that enrollment is currently "
            "open. Contact the academy to confirm current availability, schedule, "
            "and final terms."
        ),
        "sections": [
            {
                "heading": "Programme overview",
                "paragraphs": [
                    "Starter — 3 months, ₦60,000: proposed beginner programme.",
                    "Professional — 6 months, ₦125,000: proposed intermediate programme.",
                    "Advanced — 9 months, ₦190,000: proposed extended practice and career preparation.",
                    "Mastery — 1 year, ₦250,000: proposed comprehensive programme.",
                ],
            },
            {
                "heading": "Confirm before enrolling",
                "paragraphs": [
                    "Project counts, mentorship, learning materials, batch sizes, "
                    "certificates, schedules, and payment terms are proposed and "
                    "must be confirmed with the academy. Free account registration "
                    "does not mean the training programme is free."
                ],
            },
        ],
    },
    "enrolment": {
        "title": "Enrolment",
        "eyebrow": "Start with a conversation",
        "intro": (
            "Create an account to access the student area, then contact the "
            "academy to confirm an available programme and cohort."
        ),
        "sections": [
            {
                "heading": "Current enrollment process",
                "paragraphs": [
                    "The programme selection, payment verification, and course "
                    "access workflow is not yet connected to this website. Do not "
                    "send payment until the academy confirms the current cohort, "
                    "official fee, and payment instructions directly.",
                    "Account creation is free and does not enroll you in a course "
                    "or grant access to paid learning materials."
                ],
            },
        ],
    },
    "payments": {
        "title": "Payments and fees",
        "eyebrow": "Confirm payment details first",
        "intro": (
            "The academy profile lists proposed programme fees. Online payment "
            "processing and transaction records are not yet enabled on this site."
        ),
        "sections": [
            {
                "heading": "Proposed programme fees",
                "paragraphs": [
                    "Starter (3 months): ₦60,000.",
                    "Professional (6 months): ₦125,000.",
                    "Advanced (9 months): ₦190,000.",
                    "Mastery (1 year): ₦250,000.",
                ],
            },
            {
                "heading": "Before making a payment",
                "paragraphs": [
                    "Confirm the current price, payment recipient, due dates, "
                    "refund policy, and any extra charges directly with the "
                    "academy. This website does not currently initiate or verify "
                    "Paystack payments, and no payment should be considered "
                    "confirmed through this page."
                ],
            },
        ],
    },
    "password_reset": {
        "title": "Password help",
        "eyebrow": "Account recovery",
        "intro": (
            "Self-service password reset is not configured yet. Contact the "
            "academy for assistance with your account."
        ),
        "sections": [
            {
                "heading": "Need help signing in?",
                "paragraphs": [
                    "Email technonexusacademy@gmail.com from the email address "
                    "you used to register. Do not send your password or payment "
                    "card details."
                ],
            },
        ],
    },
    "enrolment_agreement": {
        "title": "Student enrolment agreement",
        "eyebrow": "Draft policy outline",
        "intro": (
            "A formal agreement has not yet been published. Review the topics "
            "below with the academy before enrolling or paying."
        ),
        "sections": [
            {
                "heading": "Confirm the programme terms",
                "paragraphs": [
                    "Ask for the confirmed programme, duration, learning format, "
                    "fees, payment deadlines, attendance expectations, support "
                    "included, cancellation terms, and completion requirements "
                    "in writing."
                ],
            },
        ],
    },
    "refunds": {
        "title": "Fees, cancellations, and refunds",
        "eyebrow": "Policy not yet published",
        "intro": (
            "No refund or cancellation terms have been configured on this site. "
            "Request the current written policy before making a payment."
        ),
        "sections": [
            {
                "heading": "Before paying",
                "paragraphs": [
                    "Confirm the payment amount and recipient, installment due "
                    "dates, cancellation window, refund eligibility, and how "
                    "refund requests are handled. Do not rely on this page as a "
                    "refund promise."
                ],
            },
        ],
    },
    "attendance": {
        "title": "Attendance and missed classes",
        "eyebrow": "Cohort policy to be confirmed",
        "intro": (
            "Attendance requirements and missed-class arrangements should be "
            "confirmed with the academy before enrollment."
        ),
        "sections": [
            {
                "heading": "Ask your cohort coordinator",
                "paragraphs": [
                    "Request the current class calendar, attendance expectations, "
                    "absence notification process, and any make-up lesson options."
                ],
            },
        ],
    },
    "code_of_conduct": {
        "title": "Student code of conduct",
        "eyebrow": "Community expectations",
        "intro": (
            "A formal code of conduct has not yet been published. Learners are "
            "expected to treat classmates, instructors, and staff respectfully."
        ),
        "sections": [
            {
                "heading": "Respectful participation",
                "paragraphs": [
                    "Be respectful in learning sessions and online spaces, "
                    "credit other people's work, and do not harass others, share "
                    "private information, or disrupt learning activities. Ask the "
                    "academy for its formal policy when available."
                ],
            },
        ],
    },
    "certificates": {
        "title": "Course completion and certificates",
        "eyebrow": "Requirements to be confirmed",
        "intro": (
            "Certificate eligibility and completion standards have not yet been "
            "defined for this website."
        ),
        "sections": [
            {
                "heading": "Confirm eligibility",
                "paragraphs": [
                    "Before enrolling, ask the academy which lessons, projects, "
                    "attendance, and assessments are required, whether certificates "
                    "are included in a programme, and how certificate authenticity "
                    "can be verified."
                ],
            },
        ],
    },
    "student_projects": {
        "title": "Student projects and intellectual property",
        "eyebrow": "Ownership and permissions",
        "intro": (
            "A formal intellectual-property policy has not yet been published. "
            "Ask the academy to clarify ownership before sharing or publishing "
            "student work."
        ),
        "sections": [
            {
                "heading": "Showcase permissions",
                "paragraphs": [
                    "Do not assume the academy may publish a student's name, "
                    "project, image, or testimonial without permission. Confirm "
                    "how project work may be used, credited, or showcased."
                ],
            },
        ],
    },
    "acceptable_use": {
        "title": "Website and account acceptable use",
        "eyebrow": "Protect accounts and learning spaces",
        "intro": (
            "Use the site and any academy learning spaces lawfully and "
            "respectfully. A full account security policy is still being prepared."
        ),
        "sections": [
            {
                "heading": "Account safety",
                "paragraphs": [
                    "Keep your password private, use your own account, and "
                    "contact the academy if you suspect unauthorized access. "
                    "Do not attempt to access another learner's account or "
                    "restricted course materials."
                ],
            },
        ],
    },
    "contact": {
        "title": "Contact Tech-Nexus Academy",
        "eyebrow": "We would love to hear from you",
        "intro": (
            "Ask us about courses, enrollment, schedules, or partnerships."
        ),
        "sections": [
            {
                "heading": "Get in touch",
                "paragraphs": [
                    "Email: technonexusacademy@gmail.com",
                    "WhatsApp: +234 903 975 9275",
                    "Location: University of Calabar, Calabar, Cross River, Nigeria",
                    "Office hours: Monday to Friday, 8:00 AM to 5:00 PM."
                ],
            },
        ],
    },
    "careers": {
        "title": "Careers",
        "eyebrow": "Grow with us",
        "intro": (
            "We welcome people who care about practical technology education "
            "and helping learners succeed."
        ),
        "sections": [
            {
                "heading": "Working at Tech-Nexus",
                "paragraphs": [
                    "There are no live vacancies listed on this page at the moment. "
                    "If you are interested in teaching, mentoring, or supporting "
                    "academy programs, introduce yourself by email.",
                    "Send your experience and the kind of role you are interested "
                    "in to technonexusacademy@gmail.com."
                ],
            },
        ],
    },
    "cookies": {
        "title": "Cookie and storage notice",
        "eyebrow": "Your privacy matters",
        "intro": (
            "This notice explains the small amount of browser storage used by "
            "this site."
        ),
        "sections": [
            {
                "heading": "Welcome guide preference",
                "paragraphs": [
                    "The home page uses browser local storage to remember that you "
                    "dismissed the welcome guide, so it does not appear again on "
                    "your next visit in the same browser. This preference is stored "
                    "on your device and is not used to identify you.",
                    "You can clear the preference by clearing this site's stored "
                    "browser data. The site does not use this preference for "
                    "advertising or cross-site tracking."
                ],
            },
        ],
    },
    "terms": {
        "title": "Terms of use",
        "eyebrow": "Using this website",
        "intro": (
            "These terms describe the basic expectations for using the "
            "Tech-Nexus Academy website."
        ),
        "sections": [
            {
                "heading": "Using the website",
                "paragraphs": [
                    "We aim to keep course and academy information useful and "
                    "current, but details such as availability, schedules, and "
                    "pricing may change. Please contact the academy to confirm "
                    "current details before making decisions.",
                    "Use the website lawfully, respect other learners, and do not "
                    "interfere with its security or operation. Do not submit "
                    "unlawful, misleading, abusive, or harmful content, or attempt "
                    "to access another person's account or information."
                ],
            },
            {
                "heading": "Accounts and learning materials",
                "paragraphs": [
                    "Provide accurate account information and keep your sign-in "
                    "credentials private. You are responsible for activity carried "
                    "out through your account; contact the academy promptly if you "
                    "suspect unauthorized access.",
                    "Website material is provided for learning and general "
                    "information. Unless a course agreement says otherwise, do not "
                    "reproduce or redistribute academy materials without permission. "
                    "Respect the licenses and ownership of software and other "
                    "third-party materials."
                ],
            },
            {
                "heading": "Courses, fees, and third-party services",
                "paragraphs": [
                    "Course enrollment, schedules, fees, and refunds are governed "
                    "by the applicable course information and student policies. "
                    "Confirm the current details with the academy before paying.",
                    "Payments may be handled by an external provider. Its own "
                    "terms and privacy policy apply to information you provide "
                    "directly to that provider."
                ],
            },
            {
                "heading": "Availability and changes",
                "paragraphs": [
                    "We work to keep the website available and accurate, but do not "
                    "promise uninterrupted access or that every page will be "
                    "error-free. We may update website content and these terms as "
                    "the academy develops."
                ],
            },
            {
                "heading": "Questions",
                "paragraphs": [
                    "If you have questions about these terms, email "
                    "technonexusacademy@gmail.com."
                ],
            },
        ],
    },
    "privacy": {
        "title": "Privacy notice",
        "eyebrow": "A clear approach to privacy",
        "intro": (
            "This page describes the information you may share when contacting "
            "Tech-Nexus Academy through the contact details on this website."
        ),
        "sections": [
            {
                "heading": "Information collected",
                "paragraphs": [
                    "When you create an account, the site processes the details "
                    "you provide, which may include your username, name, email, "
                    "phone number, country, location, date of birth, and learning "
                    "profile information. Browser location is optional and is only "
                    "captured after you choose to share it.",
                    "If you contact the academy, the details and message you submit "
                    "are used to respond. Sign-in and verification activity is "
                    "processed to protect accounts. Payment records on this site "
                    "contain transaction and plan information; card or payment "
                    "credentials should be entered only with the payment provider."
                ],
            },
            {
                "heading": "How information is used and shared",
                "paragraphs": [
                    "Information is used to operate accounts, respond to questions, "
                    "provide learning services, process enrollment and payment "
                    "records, and help protect the website. Contact enquiries are "
                    "sent to the academy by email. Information entered directly "
                    "into an external payment service is handled under that "
                    "provider's privacy terms.",
                    "The AI tutor currently returns preview responses from this "
                    "site's Django endpoint. Questions and any attached text are "
                    "sent to that endpoint for the response and are not saved as "
                    "conversation history by the site."
                ],
            },
            {
                "heading": "Cookies, storage, and retention",
                "paragraphs": [
                    "The site uses cookies needed for sign-in sessions and request "
                    "security. The homepage may store a preference in your browser "
                    "so a dismissed welcome guide stays dismissed. See the Cookies "
                    "page for more details.",
                    "Account and transaction records are retained while needed to "
                    "operate the service and meet applicable obligations. Contact "
                    "messages are handled through the academy email system. To ask "
                    "about information you provided, contact "
                    "technonexusacademy@gmail.com."
                ],
            },
            {
                "heading": "Your choices and questions",
                "paragraphs": [
                    "You can choose not to provide optional location information "
                    "and can clear site cookies or browser storage through your "
                    "browser. Do not submit passwords, payment credentials, or "
                    "other sensitive information in contact messages.",
                    "For privacy questions or requests about information you sent, "
                    "contact technonexusacademy@gmail.com."
                ],
            },
        ],
    },
    "faq": {
        "title": "Frequently asked questions",
        "eyebrow": "Quick answers",
        "intro": "A few helpful starting points for prospective learners.",
        "sections": [
            {
                "heading": "Where is the academy?",
                "paragraphs": [
                    "Tech-Nexus Academy is based at the University of Calabar in "
                    "Calabar, Cross River, Nigeria."
                ],
            },
            {
                "heading": "Can I study online?",
                "paragraphs": [
                    "Online and in-person learning are planned. Contact the academy "
                    "to confirm which formats are available for a specific cohort."
                ],
            },
            {
                "heading": "How do I ask about courses and fees?",
                "paragraphs": [
                    "Email technonexusacademy@gmail.com or message "
                    "+234 903 975 9275 on WhatsApp for current course, schedule, "
                    "and pricing information."
                ],
            },
        ],
    },
    "help": {
        "title": "Help center",
        "eyebrow": "Find your next step",
        "intro": "Use these quick links to find information or get assistance.",
        "sections": [
            {
                "heading": "Getting started",
                "paragraphs": [
                    "Browse the courses on the home page, read the FAQ, or contact "
                    "the academy if you need help choosing a learning path."
                ],
            },
        ],
    },
    "support": {
        "title": "Learner support",
        "eyebrow": "Here to help",
        "intro": "For enrollment and course questions, reach the academy directly.",
        "sections": [
            {
                "heading": "Contact support",
                "paragraphs": [
                    "Email technonexusacademy@gmail.com or contact us on WhatsApp "
                    "at +234 903 975 9275. Our listed office hours are Monday to "
                    "Friday, 8:00 AM to 5:00 PM."
                ],
            },
        ],
    },
    "sitemap": {
        "title": "Sitemap",
        "eyebrow": "Find your way around",
        "intro": "Browse the main pages and resources available on this website.",
        "sections": [],
    },
}

PAGE_LINKS = [
    ("Home", "home"),
    ("About", "about"),
    ("Courses", "courses"),
    ("Programmes", "programmes"),
    ("Schedule", "home", "#schedule"),
    ("Blog", "blog"),
    ("Contact", "contact"),
    ("Enrolment", "enrolment"),
    ("Payments", "payments"),
    ("Careers", "careers"),
    ("Register", "register"),
    ("Login", "login"),
    ("Student dashboard", "dashboard"),
    ("Administration", "administration"),
    ("Enrolment agreement", "enrolment_agreement"),
    ("Fees and refunds", "refunds"),
    ("Attendance", "attendance"),
    ("Code of conduct", "code_of_conduct"),
    ("Certificates", "certificates"),
    ("Student projects", "student_projects"),
    ("Acceptable use", "acceptable_use"),
    ("FAQ", "faq"),
    ("Help", "help"),
    ("Support", "support"),
    ("Privacy", "privacy"),
    ("Terms", "terms"),
    ("Cookies", "cookies"),
    ("Sitemap", "sitemap"),
]

BLOG_POSTS = [
    {
        "id": 1,
        "slug": "build-your-first-django-rest-api",
        "category": "Web Development",
        "title": "Build Your First Django REST API From Scratch",
        "excerpt": "A practical, beginner-friendly guide to models, serializers, views and clean API design.",
        "author": "Nana Adwoa Mensah",
        "role": "Senior Backend Mentor",
        "date": "May 24, 2025",
        "read_time": "12 min read",
        "image": "https://images.unsplash.com/photo-1555066931-4365d14bab8c?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=85&w=1400",
        "image_alt": "Code on a computer screen",
        "featured": True,
        "video": False,
        "sections": [
            {
                "heading": "Start with a focused data model",
                "paragraph": "Good APIs begin with good data decisions. Create a small course model and expose only the fields that a client needs. Keeping a first version focused makes it easier to test, understand, and extend.",
            },
            {
                "heading": "Make validation part of the design",
                "paragraph": "A serializer is more than a data converter. It is also a boundary that protects your application from incomplete or incorrect input. Add rules that produce useful messages for the people building against your API.",
            },
            {
                "heading": "Where to go next",
                "paragraph": "Connect your views, add permissions, and write tests for both successful and unsuccessful requests. You now have a foundation for a learning-platform API.",
            },
        ],
    },
    {
        "id": 2,
        "slug": "javascript-async-await-explained",
        "category": "Programming Languages",
        "title": "JavaScript Async/Await, Finally Explained",
        "excerpt": "Make asynchronous code feel predictable with clear mental models and real examples.",
        "author": "Kwame Owusu",
        "role": "Frontend Engineer",
        "date": "May 21, 2025",
        "read_time": "8 min read",
        "image": "https://images.unsplash.com/photo-1607799279861-4dd421887fb3?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1000",
        "image_alt": "Colorful code on a monitor",
        "featured": False,
        "video": False,
        "sections": [
            {"heading": "What asynchronous code means", "paragraph": "Some operations take time: a network request, a file read, or a timer. JavaScript can keep the page responsive while those operations finish, then continue when their result is ready."},
            {"heading": "Read promises from top to bottom", "paragraph": "An async function returns a promise. Inside it, await pauses that function until a promise settles, while other work in the browser can continue. Use try and catch to handle failures clearly."},
            {"heading": "Practice with real requests", "paragraph": "Try a small request, render a loading state, and handle both success and failure. This makes the asynchronous flow visible instead of hiding it behind a demo."},
        ],
    },
    {
        "id": 3,
        "slug": "beginners-guide-to-ethical-hacking",
        "category": "Cybersecurity",
        "title": "A Beginner’s Guide to Ethical Hacking",
        "excerpt": "Understand the mindset, tools and responsible practices that protect modern systems.",
        "author": "Ama Boateng",
        "role": "Security Analyst",
        "date": "May 18, 2025",
        "read_time": "10 min read",
        "image": "https://images.unsplash.com/photo-1510915228340-29c85a43dcfe?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1000",
        "image_alt": "A computer with a development environment",
        "featured": False,
        "video": True,
        "sections": [
            {"heading": "Permission comes first", "paragraph": "Security testing is only ethical when you have clear authorization and an agreed scope. Practice in a lab or on systems you own; never test someone else’s service without permission."},
            {"heading": "Build a defensive mindset", "paragraph": "Learn how accounts, updates, backups, and access controls work together. Document observations responsibly and focus on helping system owners reduce risk."},
            {"heading": "Keep learning safely", "paragraph": "Use intentionally vulnerable training environments and beginner-friendly security courses. Responsible disclosure and careful note-taking are part of the work."},
        ],
    },
    {
        "id": 4,
        "slug": "design-interfaces-people-understand",
        "category": "UI/UX",
        "title": "Design Interfaces People Understand Instantly",
        "excerpt": "Six practical UX principles for clearer navigation, hierarchy and product decisions.",
        "author": "Elsie Koomson",
        "role": "Product Designer",
        "date": "May 14, 2025",
        "read_time": "7 min read",
        "image": "https://images.unsplash.com/photo-1484417894907-623942c8ee29?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1000",
        "image_alt": "A designer working at a laptop",
        "featured": False,
        "video": False,
        "sections": [
            {"heading": "Give each screen a clear purpose", "paragraph": "A strong interface makes the next useful action easy to find. Keep visual hierarchy consistent and group related information so people can scan with confidence."},
            {"heading": "Use familiar patterns", "paragraph": "Labels, buttons, and navigation should behave as people expect. Clear language and visible feedback reduce uncertainty when a user completes an action."},
            {"heading": "Check the design with people", "paragraph": "Observe a few users trying realistic tasks. Their questions and pauses can reveal confusing wording or missing feedback before a design is released."},
        ],
    },
    {
        "id": 5,
        "slug": "how-machine-learning-models-learn",
        "category": "AI & Machine Learning",
        "title": "How Machine Learning Models Actually Learn",
        "excerpt": "An intuitive tour through training data, loss functions and model evaluation.",
        "author": "Daniel Asare",
        "role": "ML Engineer",
        "date": "May 10, 2025",
        "read_time": "11 min read",
        "image": "https://images.unsplash.com/photo-1614741118887-7a4ee193a5fa?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1000",
        "image_alt": "Abstract machine learning visualization",
        "featured": False,
        "video": False,
        "sections": [
            {"heading": "Learn from examples", "paragraph": "A model uses examples to estimate patterns that may help with new inputs. The examples, their labels, and how they were collected all influence the result."},
            {"heading": "Measure the error", "paragraph": "A loss function summarizes how far predictions are from expected answers. Training adjusts model parameters to reduce that measured error on the training data."},
            {"heading": "Evaluate beyond training data", "paragraph": "A separate evaluation set helps show whether a model generalizes. Check appropriate metrics and limitations before relying on predictions in a real setting."},
        ],
    },
    {
        "id": 6,
        "slug": "developer-toolkit-we-recommend",
        "category": "Developer Resources",
        "title": "The Developer Toolkit We Recommend in 2025",
        "excerpt": "Editors, terminals, extensions and workflows that help you build with less friction.",
        "author": "Tech-Nexus Editorial",
        "role": "Academy Team",
        "date": "May 6, 2025",
        "read_time": "6 min read",
        "image": "https://images.unsplash.com/photo-1488590528505-98d2b5aba04b?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1000",
        "image_alt": "Laptop displaying code",
        "featured": False,
        "video": False,
        "sections": [
            {"heading": "Choose tools that fit the work", "paragraph": "A code editor, terminal, version control, and browser tools cover much of a beginner’s daily workflow. Start with reliable defaults before adding more extensions."},
            {"heading": "Make the workflow repeatable", "paragraph": "Keep project instructions, formatting, and common commands easy to find. Small routines reduce setup friction and make it easier to return to a project."},
            {"heading": "Keep your toolkit manageable", "paragraph": "Add a tool when it solves a real problem, and review it periodically. A smaller, understood toolkit is often more useful than a long list of add-ons."},
        ],
    },
]

BLOG_CATEGORIES = [
    "All articles",
    "Web Development",
    "Programming Languages",
    "Cybersecurity",
    "AI & Machine Learning",
    "UI/UX",
    "Developer Resources",
]


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "Nexus/index.html")


def send_verification_email(request: HttpRequest, user) -> None:
    uid = urlsafe_base64_encode(str(user.pk).encode("utf-8"))
    token = default_token_generator.make_token(user)
    verification_url = request.build_absolute_uri(
        reverse("verify_email", kwargs={"uidb64": uid, "token": token})
    )
    issue_email_code(
        user,
        "signup",
        verification_url=verification_url,
    )


class VerificationRateLimit(Exception):
    pass


def issue_email_code(
    user,
    purpose: str,
    *,
    remember_device: bool = False,
    verification_url: str = "",
    enforce_cooldown: bool = True,
) -> EmailVerificationCode:
    now = timezone.now()
    with transaction.atomic():
        latest = EmailVerificationCode.objects.filter(
            user=user,
            purpose=purpose,
        ).first()
        if (
            enforce_cooldown
            and latest is not None
            and (now - latest.created_at).total_seconds() < 30
        ):
            raise VerificationRateLimit

        EmailVerificationCode.objects.filter(
            user=user,
            purpose=purpose,
            consumed_at__isnull=True,
        ).update(consumed_at=now)

        code = f"{secrets.randbelow(1_000_000):06d}"
        challenge = EmailVerificationCode.objects.create(
            user=user,
            purpose=purpose,
            code_hash=make_password(code),
            remember_device=remember_device,
            expires_at=now + timedelta(minutes=10),
        )
        message = (
            f"Hello {user.first_name or user.username},\n\n"
            f"Your Tech-Nexus Academy verification code is {code}.\n"
            "It expires in 10 minutes. Do not share it with anyone."
        )
        if verification_url:
            message += (
                "\n\nYou can also verify your account using this link:\n"
                f"{verification_url}"
            )
        send_mail(
            "Your Tech-Nexus Academy verification code",
            message,
            None,
            [user.email],
            fail_silently=False,
        )
    return challenge


def _json_body(request: HttpRequest) -> tuple[dict, JsonResponse | None]:
    try:
        data = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}, JsonResponse({"detail": "Invalid JSON request body."}, status=400)
    if not isinstance(data, dict):
        return {}, JsonResponse({"detail": "A JSON object is required."}, status=400)
    return data, None


def _api_method_not_allowed() -> JsonResponse:
    return JsonResponse({"detail": "Method not allowed."}, status=405)


def _account_email(user) -> str:
    return str(getattr(user, "email"))


def _safe_redirect(request: HttpRequest, requested: str) -> str:
    if not url_has_allowed_host_and_scheme(
        requested,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return reverse("dashboard")
    return requested


def _verify_email_code(
    email: str,
    code: str,
) -> tuple[EmailVerificationCode | None, str]:
    user = get_user_model()._default_manager.filter(email__iexact=email).first()
    if user is None:
        return None, "The code is invalid or has expired."

    challenge = EmailVerificationCode.objects.filter(
        user=user,
        consumed_at__isnull=True,
    ).first()
    if (
        challenge is None
        or challenge.expires_at <= timezone.now()
        or challenge.attempts >= 5
    ):
        return None, "The code is invalid or has expired."

    if not check_password(code, challenge.code_hash):
        challenge.attempts += 1
        challenge.save(update_fields=["attempts"])
        return None, "The code is invalid or has expired."

    if challenge.purpose == "signup" and not user.is_active:
        user.is_active = True
        user.save(update_fields=["is_active"])
    elif challenge.purpose == "login" and not user.is_active:
        return None, "The code is invalid or has expired."

    challenge.consumed_at = timezone.now()
    challenge.save(update_fields=["consumed_at"])
    return challenge, ""


@ensure_csrf_cookie
def api_csrf(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return _api_method_not_allowed()
    return JsonResponse({"csrf_token": request.META.get("CSRF_COOKIE", "")})


def api_register(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _api_method_not_allowed()
    data, error = _json_body(request)
    if error:
        return error

    date_of_birth = str(data.get("date_of_birth", "")).strip()
    if date_of_birth:
        try:
            birth_date = date.fromisoformat(date_of_birth)
        except ValueError:
            return JsonResponse(
                {"detail": "Enter a valid date of birth in YYYY-MM-DD format."},
                status=400,
            )
    else:
        try:
            legacy_dob = (
                data.get("dob_year"),
                data.get("dob_month"),
                data.get("dob_day"),
            )
            birth_date = (
                date(*(int(value) for value in legacy_dob))
                if all(value not in (None, "") for value in legacy_dob)
                else None
            )
        except (TypeError, ValueError):
            return JsonResponse(
                {"detail": "Enter a valid date of birth in YYYY-MM-DD format."},
                status=400,
            )

    password = str(data.get("password", ""))
    password_confirmation = str(data.get("password_confirmation", ""))
    if password != password_confirmation:
        return JsonResponse({"detail": "The passwords do not match."}, status=400)

    form_data = {
        "username": data.get("username", ""),
        "first_name": data.get("first_name", ""),
        "last_name": data.get("last_name", ""),
        "email": data.get("email", ""),
        "password1": password,
        "password2": password_confirmation,
        "phone_number": data.get("phone_number", ""),
        "country": data.get("country", ""),
        "zip_code": data.get("zip_code", ""),
        "occupation": data.get("occupation", ""),
        "state": data.get("state", ""),
        "location": data.get("location", ""),
        "date_of_birth": birth_date.isoformat() if birth_date else "",
        "nationality": data.get("nationality", ""),
        "terms_accepted": data.get("terms_accepted") is True,
    }
    form = StudentSignUpForm(form_data)
    if not form.is_valid():
        return JsonResponse(
            {"detail": form.errors.as_text(), "errors": form.errors.get_json_data()},
            status=400,
        )
    location_fields, location_error = _parse_location_metadata(data)
    if location_error or location_fields is None:
        return JsonResponse({"detail": location_error}, status=400)

    try:
        with transaction.atomic():
            user = form.save()
            profile = StudentProfile.objects.get(user=user)
            for field, value in location_fields.items():
                setattr(profile, field, value)
            profile.save(update_fields=list(location_fields))
            email = _account_email(user)
            request.session["pending_verification_email"] = email
            send_verification_email(request, user)
    except (OSError, smtplib.SMTPException):
        request.session.pop("pending_verification_email", None)
        logger.exception("Could not send account verification email")
        return JsonResponse(
            {
                "detail": (
                    "Your account was not created because we couldn't send the "
                    "verification email. Please try again later or contact support."
                )
            },
            status=503,
        )
    return JsonResponse(
        {
            "detail": "Your account has been created. Check your email for a verification code.",
            "email_verification_required": True,
            "requires_verification": True,
            "email": _account_email(user),
            "redirect_url": reverse("verification_sent"),
        },
        status=201,
    )


def _parse_location_metadata(data: dict) -> tuple[dict[str, object] | None, str]:
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    accuracy = data.get("location_accuracy")
    captured_at = data.get("location_captured_at")

    if (latitude is None) != (longitude is None):
        return None, "Latitude and longitude must both be provided or both be empty."

    try:
        latitude_value = float(latitude) if latitude is not None else None
        longitude_value = float(longitude) if longitude is not None else None
        accuracy_value = float(accuracy) if accuracy is not None else None
    except (TypeError, ValueError):
        return None, "Location coordinates and accuracy must be numbers."

    if latitude_value is not None and (
        not math.isfinite(latitude_value) or not -90 <= latitude_value <= 90
    ):
        return None, "Latitude must be between -90 and 90."
    if longitude_value is not None and (
        not math.isfinite(longitude_value) or not -180 <= longitude_value <= 180
    ):
        return None, "Longitude must be between -180 and 180."
    if accuracy_value is not None and (
        not math.isfinite(accuracy_value) or accuracy_value < 0
    ):
        return None, "Location accuracy must be a non-negative number."

    captured_value = None
    if captured_at:
        captured_value = parse_datetime(str(captured_at))
        if captured_value is None:
            return None, "Location capture time must be a valid ISO-8601 datetime."
        if timezone.is_naive(captured_value):
            captured_value = timezone.make_aware(captured_value)

    return {
        "latitude": latitude_value,
        "longitude": longitude_value,
        "location_accuracy": accuracy_value,
        "location_captured_at": captured_value,
    }, ""


def api_login(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _api_method_not_allowed()
    data, error = _json_body(request)
    if error:
        return error

    identifier = str(data.get("identifier", "")).strip()
    password = str(data.get("password", ""))
    if not identifier or not password:
        return JsonResponse(
            {"detail": "Enter your username or email and password."},
            status=400,
        )

    user_model = get_user_model()
    user = user_model._default_manager.filter(username__iexact=identifier).first()
    if user is None:
        user = user_model._default_manager.filter(email__iexact=identifier).first()
    if user is None or not user.check_password(password):
        return JsonResponse(
            {"detail": "Invalid username/email or password."},
            status=400,
        )

    purpose = "login" if user.is_active else "signup"
    authenticated_user = (
        authenticate(request, username=user.get_username(), password=password)
        if user.is_active
        else None
    )
    if user.is_active and authenticated_user is None:
        return JsonResponse(
            {"detail": "Invalid username/email or password."},
            status=400,
        )

    remember = data.get("remember") is True
    try:
        issue_email_code(
            user,
            purpose,
            remember_device=remember,
        )
    except VerificationRateLimit:
        return JsonResponse(
            {"detail": "Please wait before requesting another verification code."},
            status=429,
        )
    except (OSError, smtplib.SMTPException):
        logger.exception("Could not send login verification email")
        return JsonResponse(
            {
                "detail": (
                    "We couldn't send your login code. Please try again later or "
                    "contact support."
                )
            },
            status=503,
        )

    email = _account_email(user)
    request.session["pending_verification_email"] = email
    request.session["pending_auth_backend"] = (
        getattr(authenticated_user, "backend", "")
        if authenticated_user is not None
        else ""
    )
    request.session["pending_login_next"] = _safe_redirect(
        request,
        str(data.get("next", "")),
    )
    return JsonResponse(
        {
            "requires_verification": True,
            "email": email,
            "detail": "A verification code has been sent to your email address.",
        }
    )


def api_verify_email(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _api_method_not_allowed()
    data, error = _json_body(request)
    if error:
        return error
    email = str(data.get("email", "")).strip()
    code = str(data.get("code", "")).strip()
    challenge, message = _verify_email_code(email, code)
    if challenge is None:
        return JsonResponse({"detail": message}, status=400)

    request.session.pop("pending_verification_email", None)
    if challenge.purpose == "login":
        backend = request.session.pop("pending_auth_backend", "")
        login(
            request,
            challenge.user,
            backend=backend or "django.contrib.auth.backends.ModelBackend",
        )
        request.session.set_expiry(60 * 60 * 24 * 14 if challenge.remember_device else 0)
        redirect_url = request.session.pop("pending_login_next", "")
        return JsonResponse(
            {
                "verified": True,
                "redirect_url": _safe_redirect(request, redirect_url),
            }
        )

    request.session.pop("pending_auth_backend", None)
    request.session.pop("pending_login_next", None)
    return JsonResponse(
        {"verified": True, "redirect_url": reverse("login")}
    )


def api_resend_code(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _api_method_not_allowed()
    data, error = _json_body(request)
    if error:
        return error
    email = str(data.get("email", "")).strip()
    user = get_user_model()._default_manager.filter(email__iexact=email).first()
    if user is None:
        return JsonResponse(
            {"detail": "If that account exists, a verification code has been sent."}
        )
    purpose = "signup" if not user.is_active else "login"
    try:
        issue_email_code(user, purpose)
    except VerificationRateLimit:
        return JsonResponse(
            {"detail": "Please wait before requesting another verification code."},
            status=429,
        )
    except (OSError, smtplib.SMTPException):
        logger.exception("Could not resend account verification email")
        return JsonResponse(
            {"detail": "We couldn't send a verification code. Please try again later."},
            status=503,
        )
    email = _account_email(user)
    request.session["pending_verification_email"] = email
    return JsonResponse(
        {
            "detail": "If that account exists, a verification code has been sent.",
            "email": email,
        }
    )


def api_forgot_password(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _api_method_not_allowed()
    data, error = _json_body(request)
    if error:
        return error
    email = str(data.get("email", "")).strip()
    user = get_user_model()._default_manager.filter(
        email__iexact=email,
        is_active=True,
    ).first()
    if user is not None:
        send_password_reset_email(request, user)
    return JsonResponse(
        {"detail": "If an account exists for that email, password reset instructions have been sent."}
    )


def api_logout(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _api_method_not_allowed()
    logout(request)
    return JsonResponse({"logged_out": True})


def api_logout_other_devices(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _api_method_not_allowed()
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required."}, status=401)
    from django.contrib.sessions.models import Session

    current_key = request.session.session_key
    removed = 0
    sessions = Session.objects.filter(expire_date__gt=timezone.now()).iterator()
    for session in sessions:
        if session.session_key == current_key:
            continue
        if session.get_decoded().get("_auth_user_id") == str(request.user.pk):
            session.delete()
            removed += 1
    return JsonResponse({"logged_out": True, "sessions_ended": removed})


def api_social_login(request: HttpRequest, provider: str) -> JsonResponse:
    if provider != "google":
        if request.method != "GET":
            return _api_method_not_allowed()
        return JsonResponse(
            {"detail": f"{provider.title()} sign-in is not configured."},
            status=501,
        )
    if request.method != "POST":
        return _api_method_not_allowed()
    if not settings.GOOGLE_CLIENT_ID:
        return JsonResponse(
            {"detail": "Google sign-in is not configured on the server."},
            status=503,
        )

    data, error = _json_body(request)
    if error:
        return error
    credential = data.get("credential")
    if not isinstance(credential, str) or not credential or len(credential) > 10_000:
        return JsonResponse({"detail": "A valid Google credential is required."}, status=400)

    try:
        claims = verify_oauth2_token(
            credential,
            GoogleRequest(),
            settings.GOOGLE_CLIENT_ID,
        )
    except (GoogleAuthError, ValueError):
        logger.info("Google sign-in rejected an invalid identity token")
        return JsonResponse({"detail": "Google sign-in could not verify your account."}, status=401)

    email = claims.get("email")
    if (
        not isinstance(email, str)
        or claims.get("email_verified") is not True
        or not isinstance(claims.get("sub"), str)
    ):
        return JsonResponse(
            {"detail": "Google must provide a verified email address."},
            status=401,
        )
    email = email.strip()
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({"detail": "Google returned an invalid email address."}, status=401)

    user_model = get_user_model()
    user = user_model._default_manager.filter(email__iexact=email).first()
    if user is None and data.get("terms_accepted") is not True:
        return JsonResponse(
            {"detail": "Please accept the Terms and Conditions and Privacy Policy before creating an account with Google."},
            status=400,
        )

    if user is None:
        username_field = user_model._meta.get_field(user_model.USERNAME_FIELD)
        local_part = email.split("@", maxsplit=1)[0]
        base_username = re.sub(r"[^A-Za-z0-9.@_+-]", "", local_part)
        base_username = (base_username or "googleuser")[: username_field.max_length - 7]
        username = base_username
        while user_model._default_manager.filter(
            **{f"{user_model.USERNAME_FIELD}__iexact": username}
        ).exists():
            username = f"{base_username}_{secrets.token_hex(3)}"

        full_name = str(claims.get("name", "")).strip()
        first_name = str(claims.get("given_name", "")).strip()[:150]
        last_name = str(claims.get("family_name", "")).strip()[:150]
        if not first_name and full_name:
            first_name = full_name.split()[0][:150]
        if not last_name and len(full_name.split()) > 1:
            last_name = " ".join(full_name.split()[1:])[:150]

        user = user_model(
            **{
                user_model.USERNAME_FIELD: username,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "is_active": True,
            }
        )
        user.set_unusable_password()
        user.save()
        StudentProfile.objects.get_or_create(
            user=user,
            defaults={
                "full_name": full_name[:150],
                "terms_accepted_at": timezone.now(),
            },
        )
    elif not user.is_active:
        user.is_active = True
        user.save(update_fields=["is_active"])

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return JsonResponse(
        {
            "authenticated": True,
            "redirect_url": _safe_redirect(request, str(data.get("next", ""))),
        }
    )


def api_blog_newsletter(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _api_method_not_allowed()
    data, error = _json_body(request)
    if error:
        return error

    email = str(data.get("email", "")).strip()
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({"detail": "Enter a valid email address."}, status=400)

    _, created = NewsletterSubscription.objects.get_or_create(email=email)
    return JsonResponse(
        {
            "subscribed": True,
            "detail": (
                "Thanks — your interest in academy updates has been recorded. Email delivery is not configured yet."
                if created
                else "That email is already recorded for future academy updates."
            ),
        },
        status=201 if created else 200,
    )


def api_contact_enquiries(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _api_method_not_allowed()
    if len(request.body) > 12_000:
        return JsonResponse({"detail": "This enquiry is too large."}, status=413)

    data, error = _json_body(request)
    if error:
        return error

    limits = {
        "full_name": 150,
        "email": 254,
        "phone_number": 30,
        "category": 40,
        "subject": 180,
        "message": 6_000,
    }
    enquiry = {}
    for field, limit in limits.items():
        value = data.get(field, "")
        if not isinstance(value, str) or len(value.strip()) > limit:
            return JsonResponse({"detail": f"Enter a valid {field.replace('_', ' ')}."}, status=400)
        enquiry[field] = value.strip()

    required_fields = ("full_name", "email", "category", "subject", "message")
    if any(not enquiry[field] for field in required_fields):
        return JsonResponse({"detail": "Complete your name, email, category, subject, and message."}, status=400)
    try:
        validate_email(enquiry["email"])
    except ValidationError:
        return JsonResponse({"detail": "Enter a valid email address."}, status=400)

    categories = {
        "general",
        "courses",
        "enrolment",
        "payments",
        "technical_support",
        "partnerships",
        "other",
    }
    if enquiry["category"] not in categories:
        return JsonResponse({"detail": "Choose a valid enquiry category."}, status=400)
    if "\r" in enquiry["subject"] or "\n" in enquiry["subject"]:
        return JsonResponse({"detail": "The subject must fit on one line."}, status=400)

    reference = f"TNX-{secrets.token_hex(3).upper()}"
    email_body = (
        f"Enquiry reference: {reference}\n"
        f"Name: {enquiry['full_name']}\n"
        f"Email: {enquiry['email']}\n"
        f"Phone: {enquiry['phone_number'] or 'Not provided'}\n"
        f"Category: {enquiry['category']}\n\n"
        f"{enquiry['message']}"
    )
    try:
        sent = EmailMessage(
            f"[Tech-Nexus enquiry] {enquiry['subject']}",
            email_body,
            settings.DEFAULT_FROM_EMAIL,
            ["technonexusacademy@gmail.com"],
            reply_to=[enquiry["email"]],
        ).send(fail_silently=False)
    except (BadHeaderError, OSError, smtplib.SMTPException):
        return JsonResponse(
            {"detail": "Your enquiry could not be sent right now. Please try again or email the academy directly."},
            status=503,
        )
    if sent != 1:
        return JsonResponse(
            {"detail": "Your enquiry could not be sent. Please email the academy directly."},
            status=503,
        )

    return JsonResponse(
        {"reference": reference, "detail": "Your enquiry was sent to the academy."},
        status=201,
    )


def api_ai_chat(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _api_method_not_allowed()
    if len(request.body) > 250_000:
        return JsonResponse({"detail": "This chat request is too large."}, status=413)

    data, error = _json_body(request)
    if error:
        return error

    messages = data.get("messages")
    if not isinstance(messages, list) or not messages or len(messages) > 20:
        return JsonResponse(
            {"detail": "Send between 1 and 20 chat messages."},
            status=400,
        )
    for message in messages:
        if (
            not isinstance(message, dict)
            or message.get("role") not in {"user", "assistant"}
            or not isinstance(message.get("content"), str)
            or len(message["content"]) > 4_000
        ):
            return JsonResponse(
                {"detail": "Each message needs a supported role and text under 4,000 characters."},
                status=400,
            )
    latest = messages[-1]
    if latest["role"] != "user" or not latest["content"].strip():
        return JsonResponse(
            {"detail": "Add a question before sending your message."},
            status=400,
        )

    learning_level = data.get("learning_level")
    if learning_level not in {"Beginner", "Intermediate", "Advanced"}:
        return JsonResponse(
            {"detail": "Choose a valid learning level."},
            status=400,
        )

    attachment = data.get("attachment")
    if attachment is not None:
        if (
            not isinstance(attachment, dict)
            or not isinstance(attachment.get("name"), str)
            or not isinstance(attachment.get("type"), str)
            or not isinstance(attachment.get("content"), str)
            or not attachment["name"].strip()
            or len(attachment["name"]) > 255
            or len(attachment["type"]) > 100
            or len(attachment["content"]) > 100_000
        ):
            return JsonResponse(
                {"detail": "The attachment is invalid or exceeds the 100 KB text limit."},
                status=400,
            )

    message = _ai_tutor_preview(
        latest["content"],
        learning_level,
        attachment["name"] if attachment else "",
    )
    return JsonResponse({"message": message, "mode": "preview"})


def _ai_tutor_preview(question: str, level: str, file_name: str = "") -> str:
    prompt = question.lower()
    file_note = (
        f"\n\nI also received **{file_name}**. "
        "Connect a Django AI provider to analyze its complete contents securely."
        if file_name
        else ""
    )
    if "python" in prompt or "loop" in prompt:
        return (
            f"Here’s a {level.lower()}-friendly Python example. A loop repeats a block "
            "of code for each item:\n\n"
            "```python\n"
            'languages = ["Python", "JavaScript", "Java"]\n\n'
            "for language in languages:\n"
            '    print(f"I am learning {language}")\n'
            "```\n\n"
            "**Try this:** Change the list to three technologies you want to learn, "
            "then print their position using `enumerate()`."
            f"{file_note}"
        )
    if "error" in prompt or "debug" in prompt:
        return (
            "Let’s debug it step by step:\n\n"
            "1. Read the final line of the error first—it usually names the problem.\n"
            "2. Check the file and line number in the traceback.\n"
            "3. Print or inspect the values used on that line.\n"
            "4. Reduce the code to the smallest example that still fails.\n\n"
            "Paste the error and the relevant code, and I’ll explain the root cause "
            "rather than only patching the symptom."
            f"{file_note}"
        )
    if "html" in prompt or "css" in prompt:
        return (
            "Start with semantic HTML, then use CSS for presentation:\n\n"
            "```html\n"
            '<article class="lesson-card">\n'
            "  <h2>Introduction to Web Development</h2>\n"
            "  <p>Build accessible, responsive experiences.</p>\n"
            "  <button>Start lesson</button>\n"
            "</article>\n"
            "```\n\n"
            "Use clear elements first; add styling only after the content structure "
            f"makes sense.{file_note}"
        )
    if "project" in prompt:
        return (
            f"A strong project for your {level.lower()} level is a "
            "**Study Progress Tracker**.\n\n"
            "**Core features**\n"
            "- Add courses and weekly goals\n"
            "- Mark lessons complete\n"
            "- Display progress percentages\n"
            "- Save data through a Django REST API\n\n"
            "Build the static interface first, then add state, persistence, "
            f"authentication, and tests one layer at a time.{file_note}"
        )
    return (
        "I can help you understand that through explanation, code and practice. "
        "Tell me what language you’re using, what you expected to happen, and what "
        "happened instead.\n\n"
        "For the best answer, include a small code sample or attach the relevant file. "
        f"I’ll adapt the explanation to your **{level.lower()}** learning level."
        f"{file_note}"
    )


def password_reset_confirm(
    request: HttpRequest,
    uidb64: str,
    token: str,
) -> HttpResponse:
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = get_user_model()._default_manager.filter(pk=uid).first()
    except (binascii.Error, TypeError, UnicodeDecodeError, ValueError):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        return render(
            request,
            "Nexus/password_reset_confirm.html",
            {"form": None, "invalid_link": True},
            status=400,
        )
    form = SetPasswordForm(user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your password has been updated. Please sign in.")
        return redirect("login")
    return render(
        request,
        "Nexus/password_reset_confirm.html",
        {"form": form, "invalid_link": False},
    )


def send_password_reset_email(request: HttpRequest, user) -> None:
    uid = urlsafe_base64_encode(str(user.pk).encode("utf-8"))
    token = default_token_generator.make_token(user)
    reset_url = request.build_absolute_uri(
        reverse(
            "password_reset_confirm",
            kwargs={"uidb64": uid, "token": token},
        )
    )
    send_mail(
        "Reset your Tech-Nexus Academy password",
        f"Use this link to choose a new password:\n{reset_url}",
        None,
        [user.email],
        fail_silently=False,
    )


def password_reset_request(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        user = get_user_model()._default_manager.filter(
            email__iexact=email,
            is_active=True,
        ).first()
        if user is not None:
            send_password_reset_email(request, user)
        messages.success(
            request,
            "If an account exists for that email, password reset instructions have been sent.",
        )
        return redirect("password_reset")
    return render(request, "Nexus/password_reset_request.html")


def register(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = StudentSignUpForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
                request.session["pending_verification_email"] = user.email
                send_verification_email(request, user)
        except (OSError, smtplib.SMTPException):
            request.session.pop("pending_verification_email", None)
            logger.exception("Could not send account verification email")
            form.add_error(
                None,
                "We couldn't send your verification email. Please try again later.",
            )
        else:
            return redirect("verification_sent")
    return render(request, "Nexus/account_form.html", {
        "title": "Create your account",
        "eyebrow": "Free account registration",
        "is_registration": True,
        "form": form,
        "google_client_id": settings.GOOGLE_CLIENT_ID,
        "submit_label": "Create account",
        "alternate_url": reverse("login"),
        "alternate_label": "Already have an account? Sign in",
    })


def verification_sent(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        email = (
            request.POST.get("email")
            or request.session.get("pending_verification_email")
            or ""
        ).strip()
        code = request.POST.get("code", "").strip()
        challenge, error = _verify_email_code(email, code)
        if challenge is None:
            messages.error(request, error)
        elif challenge.purpose == "login":
            backend = request.session.pop("pending_auth_backend", "")
            login(
                request,
                challenge.user,
                backend=backend or "django.contrib.auth.backends.ModelBackend",
            )
            request.session.set_expiry(
                60 * 60 * 24 * 14 if challenge.remember_device else 0
            )
            next_url = request.session.pop("pending_login_next", "")
            request.session.pop("pending_verification_email", None)
            return redirect(_safe_redirect(request, next_url))
        else:
            request.session.pop("pending_verification_email", None)
            messages.success(request, "Your email is verified. You can now sign in.")
            return redirect("login")
    return render(
        request,
        "Nexus/verification_sent.html",
        {"verification_email": request.session.get("pending_verification_email", "")},
    )


def resend_verification(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return HttpResponse(status=405)
    email = (request.POST.get("email") or "").strip()
    user = get_user_model()._default_manager.filter(email__iexact=email).first()
    if user is not None:
        try:
            if user.is_active:
                issue_email_code(user, "login")
            else:
                send_verification_email(request, user)
            request.session["pending_verification_email"] = _account_email(user)
        except VerificationRateLimit:
            messages.error(request, "Please wait before requesting another verification code.")
        except (OSError, smtplib.SMTPException):
            logger.exception("Could not resend account verification email")
            messages.error(
                request,
                "We couldn't send a verification code. Please try again later.",
            )
    return redirect("verification_sent")


def verify_email(request: HttpRequest, uidb64: str, token: str) -> HttpResponse:
    user = None
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = get_user_model()._default_manager.filter(pk=uid).first()
    except (binascii.Error, TypeError, UnicodeDecodeError, ValueError):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        return render(
            request,
            "Nexus/verification_result.html",
            {"verified": False},
            status=400,
        )

    if not user.is_active:
        user.is_active = True
        user.save(update_fields=["is_active"])
    messages.success(request, "Your email is verified. You can now sign in.")
    return redirect("login")


def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("dashboard")

    form_data = request.POST.copy() if request.method == "POST" else None
    if form_data is not None:
        identifier = (form_data.get("username") or "").strip()
        user_model = get_user_model()
        if not user_model._default_manager.filter(username__iexact=identifier).exists():
            matched_user = user_model._default_manager.filter(
                email__iexact=identifier,
            ).first()
            if matched_user is not None:
                form_data["username"] = matched_user.get_username()
    form = AuthenticationForm(
        request,
        data=form_data,
    )
    form.fields["username"].label = "Username or email"
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        next_url = request.POST.get("next") or request.GET.get("next", "")
        request.session["pending_verification_email"] = _account_email(user)
        request.session["pending_auth_backend"] = getattr(user, "backend", "")
        request.session["pending_login_next"] = _safe_redirect(request, next_url)
        try:
            issue_email_code(
                user,
                "login",
                remember_device=request.POST.get("remember") == "on",
            )
        except VerificationRateLimit:
            messages.error(request, "Please wait before requesting another verification code.")
            return redirect("verification_sent")
        except (OSError, smtplib.SMTPException):
            logger.exception("Could not send login verification email")
            form.add_error(
                None,
                "We couldn't send your login code. Please try again later.",
            )
            return render(request, "Nexus/account_form.html", {
                "title": "Sign in",
                "eyebrow": "Welcome back",
                "is_registration": False,
                "form": form,
                "google_client_id": settings.GOOGLE_CLIENT_ID,
                "submit_label": "Sign in",
                "alternate_url": reverse("register"),
                "alternate_label": "New here? Create an account",
                "next": request.GET.get("next", ""),
                "password_help_url": reverse("password_reset"),
            })
        return redirect("verification_sent")
    return render(request, "Nexus/account_form.html", {
        "title": "Sign in",
        "eyebrow": "Welcome back",
        "is_registration": False,
        "form": form,
        "google_client_id": settings.GOOGLE_CLIENT_ID,
        "submit_label": "Sign in",
        "alternate_url": reverse("register"),
        "alternate_label": "New here? Create an account",
        "next": request.GET.get("next", ""),
        "password_help_url": reverse("password_reset"),
    })


def logout_view(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return HttpResponse(status=405)
    logout(request)
    return redirect("home")


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    from .models import Payment, StudentProfile

    payments = Payment.objects.filter(user=request.user)
    return render(
        request,
        "Nexus/dashboard.html",
        {
            "profile": StudentProfile.objects.filter(user=request.user).first(),
            "payments": payments[:5],
            "payment_count": payments.count(),
            "student_reference": f"TNX-{request.user.date_joined.year}-{request.user.pk:05d}",
            "paystack_plans": [
                {
                    "name": "Starter",
                    "duration": "3 months",
                    "fee": "₦60,000",
                    "url": "https://paystack.shop/pay/8bye9mv3x-",
                },
                {
                    "name": "Professional",
                    "duration": "6 months",
                    "fee": "₦125,000",
                    "url": "https://paystack.shop/pay/b530lxy-d0",
                },
                {
                    "name": "Advanced",
                    "duration": "9 months",
                    "fee": "₦190,000",
                    "url": "https://paystack.shop/pay/d68lxuvltv",
                },
                {
                    "name": "Mastery",
                    "duration": "1 year",
                    "fee": "₦250,000",
                    "url": "https://paystack.shop/pay/ejfmyk0uig",
                },
            ],
        },
    )


@staff_member_required
def administration(request: HttpRequest) -> HttpResponse:
    return render(request, "Nexus/administration.html")


def blog(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "Nexus/blog.html",
        {
            "posts": BLOG_POSTS,
            "categories": BLOG_CATEGORIES,
            "featured_post": BLOG_POSTS[0],
            "page_links": build_page_links(),
        },
    )


def page(request: HttpRequest, slug: str) -> HttpResponse:
    page_content = PAGE_CONTENT[slug]
    context = {
        **page_content,
        "slug": slug,
        "page_links": build_page_links(),
    }
    if slug == "sitemap":
        context["sitemap_links"] = build_sitemap_links()
    if slug == "terms":
        context["policy_links"] = [
            {"label": label, "url": reverse(url_name)}
            for label, url_name in (
                ("Student enrolment agreement", "enrolment_agreement"),
                ("Fees, cancellations, and refunds", "refunds"),
                ("Attendance and missed classes", "attendance"),
                ("Code of conduct", "code_of_conduct"),
                ("Certificates and completion", "certificates"),
                ("Student projects and ownership", "student_projects"),
                ("Website and account acceptable use", "acceptable_use"),
            )
        ]
    return render(request, "Nexus/page.html", context)


def build_page_links() -> list[dict[str, str]]:
    return [
        {
            "label": label,
            "url": reverse(url_name) + anchor,
        }
        for label, url_name, *anchor_value in PAGE_LINKS
        for anchor in anchor_value or [""]
    ]


def build_sitemap_links() -> list[dict[str, str]]:
    return build_page_links()