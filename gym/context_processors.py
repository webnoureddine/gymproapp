from .models import GymSettings


def gym_context(request):
    if request.path.startswith(("/static/", "/media/")):
        return {}
    try:
        gym = GymSettings.get()
    except Exception:  # database not migrated yet
        gym = None
    can = {}
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        for perm in ("members", "members_view", "checkin", "payments", "plans", "shop", "shop_manage",
                     "expenses", "reports", "debts"):
            can[perm] = user.can(perm)
    return {"gym": gym, "license": getattr(request, "license", None), "can": can}
