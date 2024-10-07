from django.core.management.base import BaseCommand
from django.db.models import Max
from api.models import Hero
from django.utils import timezone

class Command(BaseCommand):
    help = 'Displays the latest 10 heroes with PENDING_HERO status'

    def handle(self, *args, **options):
        # Get the latest 10 heroes with HERO status
        latest_heroes = Hero.objects.filter(status='PENDING_HERO').order_by('-created_at')[:10]

        # Print the details of the latest 10 heroes with HERO status
        for hero in latest_heroes:
            self.stdout.write(self.style.SUCCESS(f"Hero: {hero.name} (@{hero.handle})"))
            self.stdout.write(f"Created at: {hero.created_at}")
            self.stdout.write(f"X.com link: https://x.com/{hero.handle}")
            self.stdout.write("---")

        # If no heroes found, print a message
        if not latest_heroes:
            self.stdout.write(self.style.WARNING("No heroes with HERO status found."))

        self.stdout.write(self.style.SUCCESS(f"Command executed at {timezone.now()}"))