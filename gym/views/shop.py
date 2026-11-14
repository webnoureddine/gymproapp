import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from ..forms import ProductForm
from ..models import Member, Payment, Product, Sale, SaleItem
from ..utils import day_range, parse_period, perm_required


@perm_required("shop")
def pos(request):
    products = Product.objects.filter(is_active=True)
    cats = sorted({p.category for p in products if p.category})
    return render(request, "gym/shop/pos.html", {
        "products": products, "categories": cats, "METHODS": Payment.METHOD_CHOICES,
        "products_json": json.dumps([{"id": p.id, "name": p.name, "price": float(p.sell_price), "stock": p.stock,
                                      "barcode": p.barcode, "cat": p.category} for p in products]),
    })


@perm_required("shop")
@require_POST
def pos_checkout(request):
    try:
        data = json.loads(request.body)
        items = data.get("items", [])
        paid = Decimal(str(data.get("paid", 0) or 0))
    except (ValueError, InvalidOperation):
        return JsonResponse({"ok": False, "message": _("Invalid data")}, status=400)
    if not items:
        return JsonResponse({"ok": False, "message": _("Cart is empty")}, status=400)
    member = Member.objects.filter(pk=data.get("member_id")).first() if data.get("member_id") else None
    with transaction.atomic():
        sale = Sale.objects.create(member=member, created_by=request.user)
        total = Decimal("0")
        for it in items:
            p = Product.objects.select_for_update().get(pk=it["id"])
            qty = max(int(it.get("qty", 1)), 1)
            SaleItem.objects.create(sale=sale, product=p, product_name=p.name, quantity=qty,
                                    unit_price=p.sell_price, unit_cost=p.buy_price)
            Product.objects.filter(pk=p.pk).update(stock=F("stock") - qty)
            total += p.sell_price * qty
        sale.total = total
        sale.save(update_fields=["total"])
        if member is None:
            paid = total  # walk-in customers pay everything
        paid = min(paid, total)
        pay = None
        if paid > 0:
            pay = Payment.objects.create(member=member, sale=sale, kind="product", amount=paid,
                                         method=data.get("method", "cash"), received_by=request.user)
    return JsonResponse({"ok": True, "sale": sale.number, "receipt": f"/receipt/{pay.pk}/" if pay else "",
                         "message": _("Sale recorded.")})


@perm_required("shop")
def sale_list(request):
    start, end, period = parse_period(request, "today")
    a, b = day_range(start, end)
    qs = Sale.objects.filter(created_at__gte=a, created_at__lt=b).select_related("member", "created_by").prefetch_related("items", "payments")
    sales = list(qs)
    return render(request, "gym/shop/sales.html", {
        "page": Paginator(sales, 30).get_page(request.GET.get("page")),
        "total": sum((s.total for s in sales), Decimal(0)), "profit": sum((s.profit for s in sales), Decimal(0)),
        "start": start, "end": end, "period": period,
    })


@perm_required("shop_manage")
def product_list(request):
    qs = Product.objects.all()
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(barcode=q) | Q(category__icontains=q))
    if request.GET.get("low") == "1":
        qs = qs.filter(stock__lte=F("low_stock"))
    value = qs.aggregate(v=Sum(F("stock") * F("buy_price")))["v"] or 0
    return render(request, "gym/shop/products.html", {"products": qs, "stock_value": value})


@perm_required("shop_manage")
def product_edit(request, pk=None):
    obj = get_object_or_404(Product, pk=pk) if pk else None
    form = ProductForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Product saved."))
        return redirect("product_list")
    return render(request, "gym/plans/form.html", {"form": form, "obj": obj, "title": _("Product"), "back": "product_list"})


@perm_required("shop_manage")
@require_POST
def product_stock(request, pk):
    p = get_object_or_404(Product, pk=pk)
    try:
        qty = int(request.POST.get("qty", 0))
    except ValueError:
        qty = 0
    if qty:
        Product.objects.filter(pk=pk).update(stock=F("stock") + qty)
        messages.success(request, _("Stock updated for %(name)s.") % {"name": p.name})
    return redirect("product_list")
