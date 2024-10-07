# api/models.py
from django.db import models

class Card(models.Model):
    id = models.CharField(primary_key=True, max_length=100)
    owner = models.CharField(max_length=42, null=False)  # Ethereum address length
    hero_id = models.CharField(max_length=50, null=False)
    rarity = models.IntegerField(null=False)
    hero_rarity_index = models.CharField(max_length=100, null=False)
    token_id = models.CharField(max_length=50, null=False)
    season = models.IntegerField(null=False)
    created_at = models.DateTimeField(null=False)
    updated_at = models.DateTimeField(null=False)
    tx_hash = models.CharField(max_length=66, null=False)  # 0x + 64 hex chars
    blocknumber = models.BigIntegerField(null=True)
    timestamp = models.DateTimeField(null=True)
    picture = models.URLField(max_length=500, null=True, blank=True)

    def __str__(self):
        return f"Card {self.id} ({self.hero_id})"

class Hero(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    can_be_packed = models.BooleanField(null=True)
    change_1_day = models.FloatField(null=True)
    change_7_days = models.FloatField(null=True)    
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    current_score = models.FloatField(null=True)
    default_profile_image = models.BooleanField(null=True)
    description = models.TextField(blank=True, null=True)
    fast_followers_count = models.IntegerField(null=True)
    favourites_count = models.BigIntegerField(null=True)
    followers_count = models.BigIntegerField(null=False)
    friends_count = models.IntegerField(null=True)
    handle = models.CharField(max_length=255, null=False)
    has_banner = models.BooleanField(null=True)
    is_blue_verified = models.BooleanField(null=True)
    is_player = models.BooleanField(null=False)
    listed_count = models.IntegerField(null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    media_count = models.IntegerField(null=True)
    median_14_days = models.FloatField(null=True)
    median_7_days = models.FloatField(null=True)
    name = models.CharField(max_length=255, null=False)
    player_address = models.CharField(max_length=42, blank=True, null=True)
    possibly_sensitive = models.BooleanField(null=True)
    previous_rank = models.IntegerField(null=True)
    previous_stars = models.IntegerField(null=True)
    profile_banner_url = models.URLField(max_length=500, blank=True, null=True)
    profile_image_url_https = models.URLField(max_length=500, blank=True, null=True)
    star_gain = models.IntegerField(null=True)
    stars = models.IntegerField(null=False)
    status = models.CharField(max_length=50, null=False)
    statuses_count = models.IntegerField(null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    verified = models.BooleanField(null=True)
    current_rank = models.IntegerField(null=True)
    fantasy_score = models.FloatField(null=True)
    tactic_image_prefix = models.CharField(max_length=255, null=True)
    volume = models.DecimalField(max_digits=40, decimal_places=0, null=True)
    last_sale = models.BigIntegerField(null=True)

    def __str__(self):
        return f"Hero {self.name} (@{self.handle})"
    
class HeroScore(models.Model):
    hero = models.ForeignKey(Hero, on_delete=models.CASCADE, related_name='scores')
    date = models.DateField()
    score = models.FloatField()

    class Meta:
        unique_together = ('hero', 'date')  # Ensure one score per hero per date

    def __str__(self):
        return f"{self.hero.name} - {self.date}: {self.score}"	

class Player(models.Model):
    id = models.CharField(primary_key=True, max_length=100)
    name = models.CharField(max_length=255, null=False)


class FloorPrice(models.Model):
    hero = models.ForeignKey(Hero, on_delete=models.CASCADE, related_name='floor_prices')
    price = models.FloatField(null=True)
    rarity = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.hero.name} - {self.rarity}: {self.price}"

class HighestBid(models.Model):
    hero = models.ForeignKey(Hero, on_delete=models.CASCADE, related_name='highest_bids')
    price = models.BigIntegerField()
    rarity = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.hero.name} - {self.rarity}: {self.price}"

class CardSupply(models.Model):
    hero = models.ForeignKey(Hero, on_delete=models.CASCADE, related_name='card_supplies')
    rarity = models.CharField(max_length=50)
    amount = models.IntegerField()
    burnt = models.IntegerField()
    total = models.IntegerField()
    

class TournamentScore(models.Model):
    hero = models.ForeignKey(Hero, on_delete=models.CASCADE, related_name='tournament_scores')
    index = models.IntegerField()  # This represents the position in the data array
    score = models.FloatField()

    class Meta:
        unique_together = ('hero', 'index')  # Ensure one score per hero per index

    def __str__(self):
        return f"{self.hero.name} - Score {self.index}: {self.score}"