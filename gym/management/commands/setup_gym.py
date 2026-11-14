"""
First-time setup: default plans/activities/categories + the owner account.
    python manage.py setup_gym                         (asks questions)
    python manage.py setup_gym --name "Salle Atlas" --username admin --password secret123
"""
import getpass
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from gym.models import Activity, ExpenseCategory, GymSettings, Plan


class Command(BaseCommand):
    help = "Initial setup of the gym (owner account + default data)"

    def add_arguments(self, parser):
        parser.add_argument("--name")
        parser.add_argument("--username")
        parser.add_argument("--password")
        parser.add_argument("--no-input", action="store_true")

    def handle(self, *args, **o):
        User = get_user_model()
        gym = GymSettings.get()
        interactive = not o["no_input"]

        name = o["name"] or (input(f"Nom de la salle [{gym.name}]: ").strip() if interactive else "") or gym.name
        gym.name = name
        gym.save()

        if not Activity.objects.exists():
            colors = {"Musculation": "#0e9f6e", "Fitness": "#ec4899", "Cardio": "#f59e0b", "CrossFit": "#ef4444",
                      "Boxe": "#2563eb", "Arts martiaux": "#8b5cf6"}
            acts = {n: Activity.objects.create(name=n, color=c) for n, c in colors.items()}
            P = Decimal
            Plan.objects.bulk_create([
                Plan(name="Musculation 1 mois", activity=acts["Musculation"], duration_days=30, price=P(2500)),
                Plan(name="Musculation 3 mois", activity=acts["Musculation"], duration_days=90, price=P(6500)),
                Plan(name="Musculation 6 mois", activity=acts["Musculation"], duration_days=180, price=P(12000)),
                Plan(name="Musculation 1 an", activity=acts["Musculation"], duration_days=365, price=P(22000)),
                Plan(name="Fitness Femmes 1 mois", activity=acts["Fitness"], duration_days=30, price=P(3000), gender="F"),
                Plan(name="Carte 12 séances", activity=acts["Cardio"], plan_type=Plan.SESSIONS, sessions=12, duration_days=60, price=P(2000)),
                Plan(name="Séance unique", activity=acts["Musculation"], plan_type=Plan.SESSIONS, sessions=1, duration_days=1, price=P(300)),
                Plan(name="Boxe 1 mois", activity=acts["Boxe"], duration_days=30, price=P(3500)),
            ])
            self.stdout.write(self.style.SUCCESS("✓ Activités et offres par défaut créées (modifiables)"))
        for c in ("Loyer", "Électricité / Gaz (Sonelgaz)", "Eau", "Salaires", "Équipement", "Entretien", "Achat produits", "Publicité", "Autre"):
            ExpenseCategory.objects.get_or_create(name=c)

        if not User.objects.filter(role=User.OWNER).exists():
            username = o["username"] or (input("Nom d'utilisateur du propriétaire [admin]: ").strip() if interactive else "") or "admin"
            password = o["password"]
            while not password:
                password = getpass.getpass("Mot de passe (min 6 caractères): ") if interactive else "admin123"
                if len(password) < 6:
                    self.stdout.write(self.style.ERROR("Trop court."))
                    password = None
            User.objects.create_superuser(username=username, password=password, email="", role=User.OWNER, language="fr")
            self.stdout.write(self.style.SUCCESS(f"✓ Compte propriétaire '{username}' créé"))
        else:
            self.stdout.write("• Un compte propriétaire existe déjà")
        self.stdout.write(self.style.SUCCESS(f"✓ Installation prête. ID d'installation : {gym.install_id}"))
