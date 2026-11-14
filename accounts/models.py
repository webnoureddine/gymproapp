from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    OWNER = "owner"
    MANAGER = "manager"
    RECEPTION = "reception"
    COACH = "coach"
    ROLE_CHOICES = [
        (OWNER, _("Owner")),
        (MANAGER, _("Manager")),
        (RECEPTION, _("Receptionist")),
        (COACH, _("Coach")),
    ]

    role = models.CharField(_("Role"), max_length=20, choices=ROLE_CHOICES, default=RECEPTION)
    phone = models.CharField(_("Phone"), max_length=20, blank=True)
    photo = models.ImageField(_("Photo"), upload_to="staff/", blank=True, null=True)
    language = models.CharField(_("Language"), max_length=5, default="fr")

    # ---- permissions per role (simple and easy to understand for gym owners)
    PERMS = {
        OWNER: {"*"},
        MANAGER: {"members", "checkin", "payments", "plans", "shop", "shop_manage", "expenses", "reports", "debts"},
        RECEPTION: {"members", "checkin", "payments", "shop", "debts"},
        COACH: {"members_view", "checkin"},
    }

    def can(self, perm):
        if self.is_superuser:
            return True
        perms = self.PERMS.get(self.role, set())
        if "*" in perms or perm in perms:
            return True
        return perm == "members_view" and "members" in perms

    @property
    def is_owner(self):
        return self.is_superuser or self.role == self.OWNER

    @property
    def display_name(self):
        return self.get_full_name() or self.username
