from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import admin_views, auth, checkin, dashboard, finance, members, plans, pwa, reports, shop, subscriptions

urlpatterns = [
    path("login/", auth.LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("i18n/setlang/", auth.set_language, name="set_language"),

    path("", dashboard.dashboard, name="dashboard"),
    path("manifest.webmanifest", pwa.manifest, name="manifest"),
    path("sw.js", pwa.service_worker, name="service_worker"),

    path("members/", members.member_list, name="member_list"),
    path("members/export/", members.member_export, name="member_export"),
    path("members/new/", members.member_create, name="member_create"),
    path("members/cards/", members.member_cards, name="member_cards"),
    path("members/search/", members.member_search_api, name="member_search_api"),
    path("members/<int:pk>/", members.member_detail, name="member_detail"),
    path("members/<int:pk>/edit/", members.member_edit, name="member_edit"),
    path("members/<int:pk>/archive/", members.member_archive, name="member_archive"),
    path("members/<int:pk>/delete/", members.member_delete, name="member_delete"),
    path("members/<int:pk>/card/", members.member_card, name="member_card"),
    path("members/<int:member_pk>/subscribe/", subscriptions.subscription_create, name="subscription_create"),
    path("members/<int:member_pk>/pay-other/", subscriptions.member_other_payment, name="member_other_payment"),
    path("subscriptions/<int:pk>/pay/", subscriptions.subscription_pay, name="subscription_pay"),
    path("subscriptions/<int:pk>/<str:action>/", subscriptions.subscription_action, name="subscription_action"),

    path("checkin/", checkin.checkin_page, name="checkin"),
    path("checkin/api/", checkin.checkin_api, name="checkin_api"),

    path("payments/", finance.payment_list, name="payment_list"),
    path("payments/export/", finance.payment_export, name="payment_export"),
    path("payments/<int:pk>/delete/", subscriptions.payment_delete, name="payment_delete"),
    path("receipt/<int:pk>/", subscriptions.receipt, name="receipt"),
    path("debts/", finance.debt_list, name="debt_list"),
    path("expenses/", finance.expense_list, name="expense_list"),
    path("expenses/<int:pk>/delete/", finance.expense_delete, name="expense_delete"),

    path("plans/", plans.plan_list, name="plan_list"),
    path("plans/new/", plans.plan_edit, name="plan_create"),
    path("plans/<int:pk>/", plans.plan_edit, name="plan_edit"),
    path("plans/<int:pk>/delete/", plans.plan_delete, name="plan_delete"),
    path("activities/new/", plans.activity_edit, name="activity_create"),
    path("activities/<int:pk>/", plans.activity_edit, name="activity_edit"),

    path("shop/", shop.pos, name="pos"),
    path("shop/checkout/", shop.pos_checkout, name="pos_checkout"),
    path("shop/sales/", shop.sale_list, name="sale_list"),
    path("shop/products/", shop.product_list, name="product_list"),
    path("shop/products/new/", shop.product_edit, name="product_create"),
    path("shop/products/<int:pk>/", shop.product_edit, name="product_edit"),
    path("shop/products/<int:pk>/stock/", shop.product_stock, name="product_stock"),

    path("reports/", reports.reports, name="reports"),

    path("staff/", admin_views.staff_list, name="staff_list"),
    path("staff/new/", admin_views.staff_edit, name="staff_create"),
    path("staff/<int:pk>/", admin_views.staff_edit, name="staff_edit"),
    path("settings/", admin_views.settings_view, name="settings"),
    path("settings/license/", admin_views.license_view, name="license"),
    path("settings/backup/", admin_views.backup, name="backup"),
    path("account/password/", admin_views.my_password, name="my_password"),
]
