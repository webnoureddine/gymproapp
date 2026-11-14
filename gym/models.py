from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

User = settings.AUTH_USER_MODEL
ZERO = Decimal("0")


def today():
    return timezone.localdate()


# =====================================================================
#  Gym settings (one row)
# =====================================================================
class GymSettings(models.Model):
    name = models.CharField(_("Gym name"), max_length=120, default="Ma Salle de Sport")
    logo = models.ImageField(_("Logo"), upload_to="gym/", blank=True, null=True)
    slogan = models.CharField(_("Slogan"), max_length=150, blank=True)
    address = models.CharField(_("Address"), max_length=255, blank=True)
    city = models.CharField(_("City / Wilaya"), max_length=80, blank=True)
    phone = models.CharField(_("Phone"), max_length=40, blank=True)
    email = models.EmailField(_("Email"), blank=True)
    nif = models.CharField("NIF", max_length=40, blank=True)
    rc = models.CharField("RC", max_length=40, blank=True)
    nis = models.CharField("NIS", max_length=40, blank=True)
    currency = models.CharField(_("Currency"), max_length=10, default="DA")

    expiry_alert_days = models.PositiveIntegerField(_("Warn X days before expiry"), default=5)
    insurance_fee = models.DecimalField(_("Annual insurance fee"), max_digits=10, decimal_places=2, default=0)
    registration_fee = models.DecimalField(_("Registration fee (new members)"), max_digits=10, decimal_places=2, default=0)
    allow_checkin_with_debt = models.BooleanField(_("Allow entry when member has debt"), default=True)
    allow_checkin_expired = models.BooleanField(_("Allow entry when subscription expired"), default=False)
    women_schedule = models.CharField(_("Women hours (shown on cards)"), max_length=150, blank=True)
    receipt_footer = models.CharField(_("Receipt footer"), max_length=255, default="Merci pour votre confiance !")
    whatsapp_template = models.TextField(
        _("WhatsApp reminder message"),
        default="Bonjour {name}, votre abonnement à {gym} expire le {date}. Pensez à le renouveler. Merci !",
        help_text=_("Variables: {name} {gym} {date} {debt}"),
    )

    license_key = models.TextField(_("License key"), blank=True)
    install_id = models.CharField(_("Installation ID"), max_length=20, blank=True)
    installed_at = models.DateField(default=today)
    # last answer of the online license server (see gym/license.py)
    license_cache = models.JSONField(default=dict, blank=True)
    license_checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Gym settings")

    def __str__(self):
        return self.name

    _cache = None
    _cache_at = 0

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        GymSettings._cache = None

    @classmethod
    def get(cls):
        import time
        if cls._cache is not None and time.time() - cls._cache_at < 15:
            return cls._cache
        obj = cls.objects.first()
        if obj is None:
            import secrets
            obj = cls.objects.create(install_id="-".join(secrets.token_hex(2).upper() for _i in range(3)))
        cls._cache, cls._cache_at = obj, time.time()
        return obj


# =====================================================================
#  Activities & plans (offers)
# =====================================================================
class Activity(models.Model):
    name = models.CharField(_("Name"), max_length=80, unique=True)
    color = models.CharField(_("Color"), max_length=7, default="#2563eb")
    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Activity")
        verbose_name_plural = _("Activities")

    def __str__(self):
        return self.name


class Plan(models.Model):
    DURATION = "duration"
    SESSIONS = "sessions"
    TYPE_CHOICES = [(DURATION, _("By duration (days)")), (SESSIONS, _("By number of sessions"))]
    GENDER_CHOICES = [("all", _("Everyone")), ("M", _("Men")), ("F", _("Women"))]

    name = models.CharField(_("Name"), max_length=100)
    activity = models.ForeignKey(Activity, verbose_name=_("Activity"), on_delete=models.SET_NULL, null=True, blank=True, related_name="plans")
    plan_type = models.CharField(_("Type"), max_length=10, choices=TYPE_CHOICES, default=DURATION)
    duration_days = models.PositiveIntegerField(_("Duration (days)"), default=30)
    sessions = models.PositiveIntegerField(_("Number of sessions"), default=0, help_text=_("Only for session plans"))
    price = models.DecimalField(_("Price"), max_digits=10, decimal_places=2)
    gender = models.CharField(_("For"), max_length=3, choices=GENDER_CHOICES, default="all")
    description = models.CharField(_("Description"), max_length=255, blank=True)
    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        ordering = ["activity__name", "price"]
        verbose_name = _("Plan")
        verbose_name_plural = _("Plans")

    def __str__(self):
        return self.name

    @property
    def is_sessions(self):
        return self.plan_type == self.SESSIONS


# =====================================================================
#  Members
# =====================================================================
def member_photo_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"members/{instance.code or 'new'}_{timezone.now():%Y%m%d%H%M%S}.{ext}"


class MemberQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(is_archived=False)


class Member(models.Model):
    GENDER_CHOICES = [("M", _("Male")), ("F", _("Female"))]
    BLOOD_CHOICES = [(b, b) for b in ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")]

    code = models.CharField(_("Member ID"), max_length=20, unique=True, blank=True)
    first_name = models.CharField(_("First name"), max_length=80)
    last_name = models.CharField(_("Last name"), max_length=80)
    gender = models.CharField(_("Gender"), max_length=1, choices=GENDER_CHOICES, default="M")
    birth_date = models.DateField(_("Birth date"), null=True, blank=True)
    phone = models.CharField(_("Phone"), max_length=20, blank=True)
    phone2 = models.CharField(_("Second phone"), max_length=20, blank=True)
    email = models.EmailField(_("Email"), blank=True)
    address = models.CharField(_("Address"), max_length=255, blank=True)
    national_id = models.CharField(_("ID card number"), max_length=40, blank=True)
    photo = models.ImageField(_("Photo"), upload_to=member_photo_path, blank=True, null=True)
    blood_type = models.CharField(_("Blood type"), max_length=3, choices=BLOOD_CHOICES, blank=True)
    medical_notes = models.TextField(_("Medical notes"), blank=True)
    emergency_name = models.CharField(_("Emergency contact"), max_length=100, blank=True)
    emergency_phone = models.CharField(_("Emergency phone"), max_length=20, blank=True)
    notes = models.TextField(_("Notes"), blank=True)
    insurance_until = models.DateField(_("Insurance valid until"), null=True, blank=True)
    joined_at = models.DateField(_("Join date"), default=today)
    is_archived = models.BooleanField(_("Archived"), default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = MemberQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Member")
        verbose_name_plural = _("Members")
        indexes = [models.Index(fields=["last_name", "first_name"]), models.Index(fields=["phone"])]

    def __str__(self):
        return f"{self.full_name} ({self.code})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.code:
            self.code = f"M{self.pk:05d}"
            super().save(update_fields=["code"])

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def initials(self):
        return (self.first_name[:1] + self.last_name[:1]).upper()

    @property
    def age(self):
        if not self.birth_date:
            return None
        t = today()
        return t.year - self.birth_date.year - ((t.month, t.day) < (self.birth_date.month, self.birth_date.day))

    # ---------- subscription status
    def current_subscription(self):
        """The subscription that matters now: running one, else the latest."""
        subs = [s for s in self.subscriptions.all() if not s.cancelled]
        if not subs:
            return None
        running = [s for s in subs if s.start_date <= today() <= s.end_date]
        if running:
            return sorted(running, key=lambda s: s.end_date)[-1]
        upcoming = [s for s in subs if s.start_date > today()]
        if upcoming:
            return sorted(upcoming, key=lambda s: s.start_date)[0]
        return sorted(subs, key=lambda s: s.end_date)[-1]

    def status(self):
        sub = self.current_subscription()
        if sub is None:
            return "none"
        return sub.status()

    @property
    def balance_due(self):
        due = ZERO
        for s in self.subscriptions.all():
            if not s.cancelled:
                due += s.due
        for sale in self.sales.all():
            due += sale.due
        return due

    @property
    def insurance_ok(self):
        return self.insurance_until is not None and self.insurance_until >= today()

    @property
    def whatsapp_phone(self):
        """Algerian numbers: 0550123456 -> 213550123456"""
        digits = "".join(c for c in self.phone if c.isdigit())
        if digits.startswith("00"):
            digits = digits[2:]
        if digits.startswith("0"):
            digits = "213" + digits[1:]
        return digits


# =====================================================================
#  Subscriptions
# =====================================================================
class Subscription(models.Model):
    member = models.ForeignKey(Member, verbose_name=_("Member"), on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, verbose_name=_("Plan"), on_delete=models.SET_NULL, null=True)
    plan_name = models.CharField(max_length=100)  # snapshot, kept if plan deleted
    start_date = models.DateField(_("Start date"), default=today)
    end_date = models.DateField(_("End date"))
    sessions_total = models.PositiveIntegerField(default=0)  # 0 = unlimited
    sessions_used = models.PositiveIntegerField(default=0)
    price = models.DecimalField(_("Price"), max_digits=10, decimal_places=2)
    discount = models.DecimalField(_("Discount"), max_digits=10, decimal_places=2, default=0)
    frozen_since = models.DateField(_("Paused since"), null=True, blank=True)
    frozen_days_total = models.PositiveIntegerField(default=0)
    cancelled = models.BooleanField(default=False)
    notes = models.CharField(_("Notes"), max_length=255, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date", "-created_at"]
        verbose_name = _("Subscription")
        verbose_name_plural = _("Subscriptions")

    def __str__(self):
        return f"{self.member.full_name} - {self.plan_name}"

    @property
    def total(self):
        return max(self.price - self.discount, ZERO)

    @property
    def paid(self):
        if hasattr(self, "_paid_cache"):
            return self._paid_cache
        return sum((p.amount for p in self.payments.all()), ZERO)

    @property
    def due(self):
        return max(self.total - self.paid, ZERO)

    @property
    def sessions_left(self):
        if not self.sessions_total:
            return None
        return max(self.sessions_total - self.sessions_used, 0)

    @property
    def days_left(self):
        return (self.end_date - today()).days

    def status(self):
        if self.cancelled:
            return "cancelled"
        if self.frozen_since:
            return "frozen"
        t = today()
        if self.start_date > t:
            return "upcoming"
        if self.end_date < t or (self.sessions_total and self.sessions_used >= self.sessions_total):
            return "expired"
        alert = GymSettings.get().expiry_alert_days
        if self.days_left <= alert or (self.sessions_left is not None and self.sessions_left <= 2):
            return "expiring"
        return "active"

    def freeze(self):
        if not self.frozen_since:
            self.frozen_since = today()
            self.save(update_fields=["frozen_since"])

    def unfreeze(self):
        if self.frozen_since:
            days = max((today() - self.frozen_since).days, 0)
            self.end_date = self.end_date + timedelta(days=days)
            self.frozen_days_total += days
            self.frozen_since = None
            self.save(update_fields=["end_date", "frozen_days_total", "frozen_since"])


# =====================================================================
#  Shop (supplements, drinks, accessories)
# =====================================================================
class Product(models.Model):
    name = models.CharField(_("Name"), max_length=120)
    category = models.CharField(_("Category"), max_length=60, blank=True)
    barcode = models.CharField(_("Barcode"), max_length=60, blank=True)
    buy_price = models.DecimalField(_("Purchase price"), max_digits=10, decimal_places=2, default=0)
    sell_price = models.DecimalField(_("Selling price"), max_digits=10, decimal_places=2)
    stock = models.IntegerField(_("Stock"), default=0)
    low_stock = models.PositiveIntegerField(_("Low stock alert"), default=5)
    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

    def __str__(self):
        return self.name

    @property
    def is_low(self):
        return self.stock <= self.low_stock


class Sale(models.Model):
    number = models.CharField(max_length=30, unique=True, blank=True)
    member = models.ForeignKey(Member, verbose_name=_("Member"), on_delete=models.SET_NULL, null=True, blank=True, related_name="sales")
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.number:
            self.number = f"V{self.created_at:%y}-{self.pk:05d}"
            super().save(update_fields=["number"])

    @property
    def paid(self):
        return sum((p.amount for p in self.payments.all()), ZERO)

    @property
    def due(self):
        return max(self.total - self.paid, ZERO)

    @property
    def profit(self):
        return sum(((i.unit_price - i.unit_cost) * i.quantity for i in self.items.all()), ZERO)


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=120)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def line_total(self):
        return self.unit_price * self.quantity


# =====================================================================
#  Payments (every dinar that comes in)
# =====================================================================
class Payment(models.Model):
    METHOD_CHOICES = [
        ("cash", _("Cash")),
        ("ccp", "CCP / BaridiMob"),
        ("edahabia", "Edahabia"),
        ("cib", "CIB"),
        ("transfer", _("Bank transfer")),
        ("cheque", _("Cheque")),
    ]
    KIND_CHOICES = [
        ("subscription", _("Subscription")),
        ("registration", _("Registration fee")),
        ("insurance", _("Insurance")),
        ("product", _("Shop sale")),
        ("other", _("Other")),
    ]

    number = models.CharField(_("Receipt number"), max_length=30, unique=True, blank=True)
    member = models.ForeignKey(Member, verbose_name=_("Member"), on_delete=models.SET_NULL, null=True, blank=True, related_name="payments")
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments")
    sale = models.ForeignKey(Sale, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments")
    kind = models.CharField(_("Type"), max_length=20, choices=KIND_CHOICES, default="subscription")
    amount = models.DecimalField(_("Amount"), max_digits=12, decimal_places=2)
    method = models.CharField(_("Method"), max_length=20, choices=METHOD_CHOICES, default="cash")
    reference = models.CharField(_("Reference"), max_length=80, blank=True)
    note = models.CharField(_("Note"), max_length=255, blank=True)
    paid_at = models.DateTimeField(_("Date"), default=timezone.now)
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["-paid_at"]
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
        indexes = [models.Index(fields=["paid_at"])]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.number:
            self.number = f"R{self.paid_at:%y}-{self.pk:05d}"
            super().save(update_fields=["number"])

    def __str__(self):
        return self.number


# =====================================================================
#  Attendance
# =====================================================================
class CheckIn(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="checkins")
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name="checkins")
    at = models.DateTimeField(default=timezone.now, db_index=True)
    allowed = models.BooleanField(default=True)
    reason = models.CharField(max_length=120, blank=True)
    by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["-at"]


# =====================================================================
#  Expenses
# =====================================================================
class ExpenseCategory(models.Model):
    name = models.CharField(_("Name"), max_length=80, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Expense(models.Model):
    category = models.ForeignKey(ExpenseCategory, verbose_name=_("Category"), on_delete=models.SET_NULL, null=True, blank=True)
    label = models.CharField(_("Description"), max_length=160)
    amount = models.DecimalField(_("Amount"), max_digits=12, decimal_places=2)
    date = models.DateField(_("Date"), default=today)
    method = models.CharField(_("Method"), max_length=20, choices=Payment.METHOD_CHOICES, default="cash")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]


# =====================================================================
#  Business operations (kept here so views stay simple)
# =====================================================================
def next_start_date(member):
    """Renewal starts the day after the current subscription ends (if still running)."""
    last = (
        member.subscriptions.filter(cancelled=False, end_date__gte=today()).order_by("-end_date").first()
    )
    return last.end_date + timedelta(days=1) if last else today()


@transaction.atomic
def create_subscription(member, plan, user, start_date=None, discount=ZERO, paid=ZERO, method="cash",
                        reference="", notes="", price=None):
    start_date = start_date or next_start_date(member)
    price = plan.price if price is None else price
    end_date = start_date + timedelta(days=max(plan.duration_days, 1) - 1)
    sub = Subscription.objects.create(
        member=member, plan=plan, plan_name=plan.name, start_date=start_date, end_date=end_date,
        sessions_total=plan.sessions if plan.is_sessions else 0, price=price, discount=discount or ZERO,
        notes=notes, created_by=user,
    )
    payment = None
    if paid and paid > 0:
        payment = Payment.objects.create(
            member=member, subscription=sub, kind="subscription", amount=min(paid, sub.total) if sub.total else paid,
            method=method, reference=reference, received_by=user,
        )
    return sub, payment


def checkin_member(member, user, force=False):
    """Validate & record entry. Returns (checkin, ok, reason_code)."""
    cfg = GymSettings.get()
    sub = member.current_subscription()
    reason = ""
    ok = True
    if member.is_archived:
        ok, reason = False, "archived"
    elif sub is None:
        ok, reason = False, "no_subscription"
    else:
        st = sub.status()
        if st == "frozen":
            ok, reason = False, "frozen"
        elif st == "upcoming":
            ok, reason = False, "upcoming"
        elif st == "expired" and not cfg.allow_checkin_expired:
            ok, reason = False, "expired"
        elif member.balance_due > 0 and not cfg.allow_checkin_with_debt:
            ok, reason = False, "debt"
    if not ok and force:
        ok, reason = True, "forced:" + reason
    already = ok and CheckIn.objects.filter(member=member, allowed=True, at__date=today()).exists()
    if already and not reason:
        reason = "already_today"
    ci = CheckIn.objects.create(member=member, subscription=sub, allowed=ok, reason=reason, by=user)
    if ok and sub and sub.sessions_total and not already:
        Subscription.objects.filter(pk=sub.pk).update(sessions_used=models.F("sessions_used") + 1)
    return ci, ok, reason
