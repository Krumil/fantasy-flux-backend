from django.core.management.base import BaseCommand
from api.models import Hero, HeroScore
from django.db.models import Avg
from django.utils import timezone
from datetime import timedelta
import json

class Command(BaseCommand):
    help = 'Predict heroes star count swings and return JSON data for potential losers and gainers'

    def handle(self, *args, **options):
        return self.predict_star_swings()

    def predict_star_swings(self):
        heroes = Hero.objects.filter(status='HERO').order_by('current_rank')
        total_heroes = heroes.count()

        losers = []
        gainers = []
        for hero in heroes:
            if hero.current_rank is None:
                self.stdout.write(self.style.WARNING(f"Skipping hero {hero.name} due to missing current_rank"))
                continue

            current_stars = hero.stars
            current_percentile = (hero.current_rank / total_heroes) * 100
            predicted_stars = self.predict_new_stars(current_percentile)
            star_change = predicted_stars - current_stars

            if abs(star_change) >= 1:  # Include all changes, even small ones
                performance_change = self.get_performance_change(hero)
                recovery_potential = self.calculate_recovery_potential(hero)
                hero_data = {
                    'name': hero.name,
                    'current_rank': hero.current_rank,
                    'fantasy_score': hero.fantasy_score,
                    'current_stars': current_stars,
                    'predicted_stars': predicted_stars,
                    'star_change': star_change,
                    'performance_change': performance_change,
                    'recovery_potential': recovery_potential,
                    'median_7_days': hero.median_7_days,
                    'median_14_days': hero.median_14_days,
                    'change_1_day': hero.change_1_day,
                    'change_7_days': hero.change_7_days,
                }
                if star_change < 0:
                    losers.append(hero_data)
                else:
                    gainers.append(hero_data)

        # Sort predictions by the magnitude of star change and performance change
        losers.sort(key=lambda x: (abs(x['star_change']), -x['performance_change']), reverse=True)
        gainers.sort(key=lambda x: (abs(x['star_change']), -x['performance_change']), reverse=True)

        # Prepare JSON response
        response_data = {
            'potential_losers': losers[:20],  # Top 20 predictions
            'potential_gainers': gainers[:20]  # Top 20 predictions
        }

        return json.dumps(response_data, indent=2)

    def predict_new_stars(self, percentile):
        if percentile <= 15:
            return 7
        elif percentile <= 32:
            return 6
        elif percentile <= 50:
            return 5
        elif percentile <= 67:
            return 4
        elif percentile <= 82:
            return 3
        else:
            return 2

    def get_performance_change(self, hero):
        now = timezone.now()
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)

        seven_day_avg = HeroScore.objects.filter(
            hero=hero, 
            date__gte=seven_days_ago
        ).aggregate(Avg('score'))['score__avg'] or 0

        thirty_day_avg = HeroScore.objects.filter(
            hero=hero, 
            date__gte=thirty_days_ago
        ).aggregate(Avg('score'))['score__avg'] or 0

        return (seven_day_avg - thirty_day_avg) / thirty_day_avg if thirty_day_avg else 0

    def calculate_recovery_potential(self, hero):
        median_diff = hero.median_14_days - hero.median_7_days
        recent_trend = hero.change_1_day
        
        normalized_diff = median_diff / hero.median_14_days if hero.median_14_days else 0
        
        recovery_potential = (normalized_diff * 0.7) + (recent_trend * 0.3)
        
        return recovery_potential