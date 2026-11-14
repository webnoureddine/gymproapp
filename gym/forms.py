from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from .models import Activity, Expense, ExpenseCategory, GymSettings, Member, Payment, Plan, Product

User = get_user_model()


class StyledMixin:
    """Adds CSS classes to every widget so templates stay tiny."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            w = field.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs.setdefault("class", "checkbox")
            elif isinstance(w, (forms.Select, forms.SelectMultiple)):
                w.attrs.setdefault("class", "input")
            elif isinstance(w, forms.ClearableFileInput):
                w.attrs.setdefault("class", "file")
            else:
                w.attrs.setdefault("class", "input")
            if isinstance(w, forms.Textarea):
                w.attrs.setdefault("rows", 3)


class DateInput(forms.DateInput):
    input_type = "date"

    def __init__(self, **kw):
        super().__init__(format="%Y-%m-%d", **kw)


class MemberForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            "first_name", "last_name", "gender", "birth_date", "phone", "phone2", "email", "address",
            "national_id", "photo", "blood_type", "medical_notes", "emergency_name", "emergency_phone",
            "insurance_until", "joined_at", "notes",
        ]
        widgets = {
            "birth_date": DateInput(), "insurance_until": DateInput(), "joined_at": DateInput(),
            "phone": forms.TextInput(attrs={"inputmode": "tel", "placeholder": "05 50 12 34 56"}),
            "phone2": forms.TextInput(attrs={"inputmode": "tel"}),
            "emergency_phone": forms.TextInput(attrs={"inputmode": "tel"}),
            "photo": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }


class SubscriptionForm(StyledMixin, forms.Form):
    plan = forms.ModelChoiceField(label=_("Plan"), queryset=Plan.objects.none())
    start_date = forms.DateField(label=_("Start date"), widget=DateInput())
    price = forms.DecimalField(label=_("Price"), min_value=0, decimal_places=2)
    discount = forms.DecimalField(label=_("Discount"), min_value=0, decimal_places=2, initial=0, required=False)
    paid = forms.DecimalField(label=_("Amount paid now"), min_value=0, decimal_places=2, required=False)
    method = forms.ChoiceField(label=_("Method"), choices=Payment.METHOD_CHOICES, initial="cash")
    reference = forms.CharField(label=_("Reference"), required=False)
    add_registration = forms.BooleanField(label=_("Add registration fee"), required=False)
    add_insurance = forms.BooleanField(label=_("Add annual insurance"), required=False)
    notes = forms.CharField(label=_("Notes"), required=False)

    def __init__(self, *args, member=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Plan.objects.filter(is_active=True).select_related("activity")
        if member is not None:
            qs = qs.filter(gender__in=["all", member.gender])
        self.fields["plan"].queryset = qs
        self.fields["plan"].label_from_instance = lambda p: f"{p.name} — {p.price:,.0f}".replace(",", " ")

    def clean(self):
        data = super().clean()
        data["discount"] = data.get("discount") or Decimal("0")
        data["paid"] = data.get("paid") or Decimal("0")
        return data


class PaymentForm(StyledMixin, forms.Form):
    amount = forms.DecimalField(label=_("Amount"), min_value=Decimal("0.01"), decimal_places=2)
    method = forms.ChoiceField(label=_("Method"), choices=Payment.METHOD_CHOICES, initial="cash")
    reference = forms.CharField(label=_("Reference"), required=False)
    note = forms.CharField(label=_("Note"), required=False)


class OtherPaymentForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["kind", "amount", "method", "reference", "note"]


class PlanForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Plan
        fields = ["name", "activity", "plan_type", "duration_days", "sessions", "price", "gender", "description", "is_active"]


class ActivityForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Activity
        fields = ["name", "color", "is_active"]
        widgets = {"color": forms.TextInput(attrs={"type": "color"})}


class ProductForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "category", "barcode", "buy_price", "sell_price", "stock", "low_stock", "is_active"]


class ExpenseForm(StyledMixin, forms.ModelForm):
    new_category = forms.CharField(label=_("Or new category"), required=False)

    class Meta:
        model = Expense
        fields = ["label", "category", "amount", "date", "method"]
        widgets = {"date": DateInput()}

    def save(self, commit=True):
        obj = super().save(commit=False)
        new = self.cleaned_data.get("new_category", "").strip()
        if new:
            obj.category, _c = ExpenseCategory.objects.get_or_create(name=new)
        if commit:
            obj.save()
        return obj


class GymSettingsForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = GymSettings
        fields = [
            "name", "slogan", "logo", "address", "city", "phone", "email", "nif", "rc", "nis", "currency",
            "expiry_alert_days", "registration_fee", "insurance_fee", "allow_checkin_with_debt",
            "allow_checkin_expired", "women_schedule", "receipt_footer", "whatsapp_template",
        ]


class StaffForm(StyledMixin, forms.ModelForm):
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput(render_value=False), required=False,
                               help_text=_("Leave empty to keep the current password"))

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "role", "phone", "email", "language", "is_active"]
        widgets = {"language": forms.Select(choices=[("fr", "Français"), ("ar", "العربية"), ("en", "English")])}

    def clean(self):
        data = super().clean()
        if not self.instance.pk and not data.get("password"):
            self.add_error("password", _("Password is required for a new account"))
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class LicenseForm(StyledMixin, forms.Form):
    key = forms.CharField(label=_("License key"), widget=forms.Textarea(attrs={"rows": 3}))
