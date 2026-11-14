from django.contrib import admin

from . import models

for m in (models.GymSettings, models.Activity, models.Plan, models.Member, models.Subscription, models.Payment,
          models.CheckIn, models.Product, models.Sale, models.SaleItem, models.Expense, models.ExpenseCategory):
    admin.site.register(m)
