from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Hero, HeroScore, Card, Player, FloorPrice, HighestBid, CardSupply, TournamentScore
from .serializers import HeroSerializer, CardSerializer, PlayerSerializer
from django.db.models import Avg, Subquery
from django.utils import timezone
from datetime import timedelta
from .management.commands.predict_star_swings import Command as PredictStarSwingsCommand
from rest_framework.permissions import AllowAny
from rest_framework.decorators import permission_classes
import json

@permission_classes([AllowAny])
class HeroViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = Hero.objects.all()
	serializer_class = HeroSerializer

@permission_classes([AllowAny])
class CardViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = Card.objects.all()
	serializer_class = CardSerializer

@permission_classes([AllowAny])
class PlayerViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = Player.objects.all()
	serializer_class = PlayerSerializer

@api_view(['GET'])
@permission_classes([AllowAny])
def predict_star_swings(request):
	command = PredictStarSwingsCommand()
	json_data = command.handle()
	data = json.loads(json_data)
	return Response(data)

@api_view(['GET'])
@permission_classes([AllowAny])
def hero_performance(request, hero_id):
	try:
		hero = Hero.objects.get(id=hero_id)
	except Hero.DoesNotExist:
		return Response({'error': 'Hero not found'}, status=status.HTTP_404_NOT_FOUND)

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

	performance_change = (seven_day_avg - thirty_day_avg) / thirty_day_avg if thirty_day_avg else 0

	return Response({
		'hero_id': hero.id,
		'name': hero.name,
		'seven_day_avg': seven_day_avg,
		'thirty_day_avg': thirty_day_avg,
		'performance_change': performance_change
	})

@api_view(['GET'])
@permission_classes([AllowAny])
def hero_market_data(request, hero_id):
	try:
		hero = Hero.objects.get(id=hero_id)
	except Hero.DoesNotExist:
		return Response({'error': 'Hero not found'}, status=status.HTTP_404_NOT_FOUND)

	floor_prices = FloorPrice.objects.filter(hero=hero)
	highest_bids = HighestBid.objects.filter(hero=hero)
	card_supplies = CardSupply.objects.filter(hero=hero)

	return Response({
		'hero_id': hero.id,
		'name': hero.name,
		'floor_prices': [{'rarity': fp.rarity, 'price': fp.price} for fp in floor_prices],
		'highest_bids': [{'rarity': hb.rarity, 'price': hb.price} for hb in highest_bids],
		'card_supplies': [{'rarity': cs.rarity, 'amount': cs.amount, 'burnt': cs.burnt, 'total': cs.total} for cs in card_supplies],
		'volume': hero.volume,
		'last_sale': hero.last_sale
	})

@api_view(['GET'])
@permission_classes([AllowAny])
def hero_tournament_scores(request, hero_id):
	try:
		hero = Hero.objects.get(id=hero_id)
	except Hero.DoesNotExist:
		return Response({'error': 'Hero not found'}, status=status.HTTP_404_NOT_FOUND)
	
	tournament_scores = TournamentScore.objects.filter(hero=hero).order_by('index')

	# Create the tournament_scores object
	tournament_scores_data = [{'tournament_label': len(tournament_scores) - ts.index - 7, 'score': ts.score} for ts in tournament_scores]
	tournament_scores_data = tournament_scores_data[:-11]

	return Response({
		'hero_id': hero.id,
		'name': hero.name,
		'tournament_scores': tournament_scores_data
	})

@api_view(['GET'])
@permission_classes([AllowAny])
def search_heroes_by_handle(request):
	handle = request.query_params.get('handle', None)
	if not handle:
		return Response({'error': 'Handle parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

	heroes = Hero.objects.filter(handle__icontains=handle)
	
	if not heroes.exists():
		return Response({'error': 'No heroes found with the given handle'}, status=status.HTTP_404_NOT_FOUND)

	serializer = HeroSerializer(heroes, many=True)

	return Response({
		'heroes': serializer.data
	})