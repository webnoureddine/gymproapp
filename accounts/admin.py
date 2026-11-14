from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class GymUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("GymPro", {"fields": ("role", "phone", "photo", "language")}),)
    list_display = ("username", "first_name", "last_name", "role", "is_active")
