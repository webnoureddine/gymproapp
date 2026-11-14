from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from ..forms import ActivityForm, PlanForm
from ..models import Activity, Plan
from ..utils import perm_required


@perm_required("plans")
def plan_list(request):
    plans = Plan.objects.select_related("activity").annotate(n=Count("subscription"))
    return render(request, "gym/plans/list.html", {
        "plans": plans, "activities": Activity.objects.annotate(n=Count("plans")),
        "plan_form": PlanForm(), "activity_form": ActivityForm(),
    })


@perm_required("plans")
def plan_edit(request, pk=None):
    plan = get_object_or_404(Plan, pk=pk) if pk else None
    form = PlanForm(request.POST or None, instance=plan)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Plan saved."))
        return redirect("plan_list")
    return render(request, "gym/plans/form.html", {"form": form, "obj": plan, "title": _("Plan")})


@perm_required("plans")
def activity_edit(request, pk=None):
    act = get_object_or_404(Activity, pk=pk) if pk else None
    form = ActivityForm(request.POST or None, instance=act)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Activity saved."))
        return redirect("plan_list")
    return render(request, "gym/plans/form.html", {"form": form, "obj": act, "title": _("Activity")})


@perm_required("plans")
@require_POST
def plan_delete(request, pk):
    plan = get_object_or_404(Plan, pk=pk)
    if plan.subscription_set.exists():
        plan.is_active = False
        plan.save(update_fields=["is_active"])
        messages.info(request, _("This plan is used by subscriptions, it was deactivated instead of deleted."))
    else:
        plan.delete()
        messages.success(request, _("Plan deleted."))
    return redirect("plan_list")
