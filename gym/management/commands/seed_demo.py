"""Fill the database with realistic demo data (for presentations to clients). python manage.py seed_demo"""
import random
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from gym.models import (CheckIn, Expense, ExpenseCategory, Member, Payment, Plan, Product, Sale, SaleItem,
                        Subscription)

FIRST_M = ["Mohamed", "Yacine", "Amine", "Karim", "Sofiane", "Walid", "Bilal", "Riad", "Nassim", "Islam", "Abdelkader", "Hichem", "Mehdi", "Anis", "Fares"]
FIRST_F = ["Amina", "Sara", "Yasmine", "Meriem", "Lina", "Nour", "Imane", "Rania", "Khadidja", "Asma"]
LAST = ["Benali", "Bouzid", "Haddad", "Belkacem", "Mansouri", "Cherif", "Saidi", "Boudiaf", "Zerrouki", "Hamidi", "Mebarki", "Kaci", "Rahmani", "Taleb", "Brahimi", "Ouali"]


class Command(BaseCommand):
    help = "Create demo members, payments, check-ins, products and expenses"

    def add_arguments(self, parser):
        parser.add_argument("--members", type=int, default=60)

    def handle(self, *args, **o):
        call_command("setup_gym", no_input=True, name="Atlas Gym Oran", username="admin", password="admin123")
        User = get_user_model()
        owner = User.objects.filter(role=User.OWNER).first()
        rec, _c = User.objects.get_or_create(username="reception", defaults={"role": User.RECEPTION, "first_name": "Samir"})
        rec.set_password("reception123")
        rec.save()
        random.seed(7)
        tz = timezone.get_current_timezone()
        today = timezone.localdate()
        plans = list(Plan.objects.all())
        prods = []
        for n, c, b, s, st in [("Whey Protein 1kg", "Compléments", 6500, 8500, 12), ("Créatine 300g", "Compléments", 2800, 3800, 4),
                               ("Eau 1.5L", "Boissons", 30, 60, 80), ("Boisson énergétique", "Boissons", 120, 200, 3),
                               ("Gants de musculation", "Accessoires", 900, 1500, 10), ("Serviette", "Accessoires", 400, 800, 15),
                               ("Barre protéinée", "Compléments", 180, 300, 40)]:
            prods.append(Product.objects.get_or_create(name=n, defaults=dict(category=c, buy_price=b, sell_price=s, stock=st))[0])

        def at(d, h=None):
            return timezone.make_aware(datetime.combine(d, time(h or random.randint(8, 22), random.randint(0, 59))), tz)

        for i in range(o["members"]):
            g = "F" if random.random() < .3 else "M"
            first = random.choice(FIRST_F if g == "F" else FIRST_M)
            joined = today - timedelta(days=random.randint(0, 330))
            m = Member.objects.create(first_name=first, last_name=random.choice(LAST), gender=g,
                                      phone=f"0{random.choice('567')}{random.randint(10000000, 99999999)}",
                                      birth_date=today - timedelta(days=random.randint(16 * 365, 45 * 365)), joined_at=joined,
                                      insurance_until=joined + timedelta(days=365), created_by=owner,
                                      medical_notes="Asthme léger" if random.random() < .05 else "")
            start = joined
            while start <= today:
                cand = [p for p in plans if p.gender in ("all", g)]
                plan = random.choice(cand)
                end = start + timedelta(days=plan.duration_days - 1)
                sub = Subscription.objects.create(member=m, plan=plan, plan_name=plan.name, start_date=start, end_date=end,
                                                  sessions_total=plan.sessions if plan.is_sessions else 0, price=plan.price, created_by=owner)
                Subscription.objects.filter(pk=sub.pk).update(created_at=at(start))
                paid = plan.price if random.random() > .15 else plan.price - Decimal(random.choice([500, 1000, 1500]))
                Payment.objects.create(member=m, subscription=sub, amount=max(paid, Decimal(0)), paid_at=at(start),
                                       method=random.choice(["cash"] * 6 + ["ccp", "edahabia", "cib"]), received_by=random.choice([owner, rec]))
                # visits
                for d in range(0, min((min(end, today) - start).days + 1, 120)):
                    if random.random() < .4:
                        day = start + timedelta(days=d)
                        CheckIn.objects.create(member=m, subscription=sub, at=at(day, random.choice([7, 9, 10, 12, 17, 18, 18, 19, 19, 20, 21])), by=rec)
                if plan.is_sessions:
                    sub.sessions_used = min(plan.sessions, sub.checkins.count())
                    sub.save(update_fields=["sessions_used"])
                if random.random() < .25:  # some members stop coming
                    break
                start = end + timedelta(days=random.choice([1, 1, 1, 5, 20]))
        # shop sales
        for _ in range(120):
            d = today - timedelta(days=random.randint(0, 120))
            s = Sale.objects.create(created_by=rec, created_at=at(d))
            tot = Decimal(0)
            for p in random.sample(prods, random.randint(1, 2)):
                q = random.randint(1, 3)
                SaleItem.objects.create(sale=s, product=p, product_name=p.name, quantity=q, unit_price=p.sell_price, unit_cost=p.buy_price)
                tot += p.sell_price * q
            s.total = tot
            s.save()
            Payment.objects.create(sale=s, kind="product", amount=tot, paid_at=at(d), received_by=rec)
        # expenses
        cats = {c.name: c for c in ExpenseCategory.objects.all()}
        for k in range(12):
            d = (today.replace(day=1) - timedelta(days=30 * k)).replace(day=5)
            if d > today:
                continue
            Expense.objects.create(category=cats["Loyer"], label="Loyer du local", amount=45000, date=d)
            Expense.objects.create(category=cats["Salaires"], label="Salaires coachs", amount=60000, date=d)
            Expense.objects.create(category=cats["Électricité / Gaz (Sonelgaz)"], label="Facture Sonelgaz", amount=random.randint(9000, 18000), date=d + timedelta(days=10))
        self.stdout.write(self.style.SUCCESS("✓ Demo data created. Login: admin / admin123  (reception / reception123)"))
