"""
Admin لتطبيق الطلاب
الطلاب يتسجلوا تلقائياً - مش محتاجين Admin
"""
from django.contrib import admin
from .models import Student

# ❌ لا نسجل Student في Admin
# الطلاب يتسجلوا تلقائياً من accounts/signals.py
# لو محتاج تشوف الطلاب → استخدم User model في accounts
