from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CardViewSet,
    HeroViewSet,
    PlayerViewSet,
    hero_market_data,
    hero_performance,
    hero_tournament_scores,
    predict_star_swings,
    search_heroes_by_handle
)

router = DefaultRouter()
router.register(r'heroes', HeroViewSet)
router.register(r'cards', CardViewSet)
router.register(r'players', PlayerViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('predict-star-swings/', predict_star_swings, name='predict-star-swings'),
    path('hero-performance/<str:hero_id>/', hero_performance, name='hero-performance'),
    path('hero-market-data/<str:hero_id>/', hero_market_data, name='hero-market-data'),
    path('hero-tournament-scores/<str:hero_id>/', hero_tournament_scores, name='hero-tournament-scores'),
	path('search-heroes-by-handle/', search_heroes_by_handle, name='search-heroes-by-handle'),
]