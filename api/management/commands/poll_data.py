# api/management/commands/poll_data.py
import requests
from django.core.management.base import BaseCommand
from api.models import Card, Hero, Player, HeroScore, FloorPrice, HighestBid, CardSupply, TournamentScore
from dotenv import load_dotenv
from datetime import datetime
import os
import time
import logging
from django.db import IntegrityError
from decimal import Decimal
from playwright.sync_api import sync_playwright

load_dotenv()

FANTASY_TOP_API_KEY = os.getenv('FANTASY_TOP_API_KEY')
HUDDLE_API_TOKEN = os.getenv('HUDDLE_API_TOKEN')
TWITTER_USERNAME = os.getenv('TWITTER_USERNAME')
TWITTER_PASSWORD = os.getenv('TWITTER_PASSWORD')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Command(BaseCommand):
	help = 'Poll data from fantasy.top API and save it to the database'

	def handle(self, *args, **kwargs):
		HUDDLE_API_TOKEN = None
		while True:
			try:
				self.stdout.write(self.style.SUCCESS('Starting data polling...'))
				
				HUDDLE_API_TOKEN = self.check_and_refresh_huddle_token(HUDDLE_API_TOKEN)
				# self.poll_cards()
				# self.poll_players()
				self.poll_heroes()
				self.fetch_hero_scores(HUDDLE_API_TOKEN)
				self.fetch_tournament_scores(HUDDLE_API_TOKEN)
				
				self.stdout.write(self.style.SUCCESS('Data polling completed. Waiting for 1 minute before next run...'))
				time.sleep(60)  # Wait for 60 seconds (1 minute)
			except KeyboardInterrupt:
				self.stdout.write(self.style.WARNING('Polling interrupted by user. Exiting...'))
				break
			except Exception as e:
				self.stdout.write(self.style.ERROR(f'An error occurred: {str(e)}'))
				self.stdout.write(self.style.WARNING('Retrying in 1 minute...'))
				time.sleep(60)

	def check_and_refresh_huddle_token(self, HUDDLE_API_TOKEN):
		url = "https://api.huddle.wtf/api/analytics/heroes-scores"
		headers = {
			"accept": "application/json, text/plain, */*",
			"authorization": f"Bearer {HUDDLE_API_TOKEN}",
			"cache-control": "no-cache",
			"expires": "0",
			"pragma": "no-cache",
		}

		try:
			response = requests.get(url, headers=headers)
			response.raise_for_status()
		except requests.exceptions.HTTPError as e:
			if e.response.status_code == 401 or e.response.status_code == 403:
				self.stdout.write(self.style.WARNING('HUDDLE token expired. Refreshing...'))
				HUDDLE_API_TOKEN =self.refresh_huddle_token(HUDDLE_API_TOKEN)
			else:
				raise

		return HUDDLE_API_TOKEN

	def refresh_huddle_token(self, headless=False, HUDDLE_API_TOKEN=None):
		with sync_playwright() as p:
			browser = p.chromium.launch(headless=headless)
			context = browser.new_context()
			page = context.new_page()

			try:
				logging.info("Navigating to Huddle website")
				page.goto("https://www.huddle.wtf/")
				page.wait_for_load_state('networkidle')

				page.click('button:has-text("Twitter")')

				logging.info("Waiting for Privy popup")
				privy_popup = page.locator('#privy-modal-content')
				privy_popup.wait_for(state="visible", timeout=10000)

				logging.info("Clicking Twitter login button in Privy popup")
				twitter_button = privy_popup.locator("button:has-text('Twitter')")
				twitter_button.click()

				# Wait for the Twitter popup to appear
				page.wait_for_load_state('networkidle')

				logging.info("Waiting for username field")
				page.wait_for_selector('input[autocomplete="username"]', state="visible", timeout=10000)
				logging.info("Filling username")
				page.fill('input[autocomplete="username"]', TWITTER_USERNAME)

				logging.info("Waiting before clicking 'Next' button")
				time.sleep(2)  # Add a 2-second delay

				logging.info("Attempting to click 'Next' button")
				next_button_selectors = [
					'div[role="button"]:has-text("Next")',
					'span:has-text("Next")',
					'button:has-text("Next")'
				]
				for selector in next_button_selectors:
					try:
						next_button = page.wait_for_selector(selector, state="visible", timeout=5000)
						if next_button:
							next_button.click()
							logging.info(f"Clicked 'Next' button using selector: {selector}")
							break
					except Exception as e:
						logging.warning(f"Failed to find 'Next' button with selector: {selector}")
				else:
					logging.error("Failed to find and click 'Next' button with any selector")
					raise Exception("Unable to proceed past username entry")

				logging.info("Waiting for password field")
				page.wait_for_selector('input[name="password"]', state="visible", timeout=10000)
				logging.info("Filling password")
				page.fill('input[name="password"]', TWITTER_PASSWORD)

				logging.info("Waiting before clicking 'Log in' button")
				time.sleep(2)  # Add a 2-second delay

				logging.info("Clicking 'Log in' button")
				login_button = page.locator('div[role="button"]:has-text("Log in")')
				if login_button.is_visible():
					login_button.click()
				else:
					logging.warning("'Log in' button not visible")
					# Try to find and click the button by its text content
					page.click('text="Log in"', timeout=5000)

				logging.info("Waiting for authorization page")
				page.wait_for_selector('text="Authorize app"', state="visible", timeout=30000)

				logging.info("Scrolling to the bottom of the page")
				page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

				logging.info("Clicking 'Authorize app' button")
				authorize_button = page.locator('text="Authorize app"')
				authorize_button.click()

				logging.info("Waiting for login to complete")
				page.wait_for_url("https://www.huddle.wtf/", timeout=30000)

				time.sleep(5)

				logging.info("Extracting new token")
				new_token = page.evaluate("() => localStorage.getItem('authToken')")

				if new_token:
					logging.info(f"New token: {new_token}")
					self.stdout.write(self.style.SUCCESS('HUDDLE token refreshed successfully'))
					# remove first and last character from new_token
					HUDDLE_API_TOKEN = new_token[1:-1]
				else:
					self.stdout.write(self.style.ERROR('Failed to retrieve new HUDDLE token'))

			except Exception as e:
				logging.error(f"An error occurred: {str(e)}")
				# Capture and log the page content when an error occurs
				logging.error(f"Page content at error: {page.content()}")
				# Take a screenshot for visual debugging
				page.screenshot(path="error_screenshot.png")
				logging.info("Screenshot saved as error_screenshot.png")
			finally:
				logging.info("Closing browser")
				browser.close()
				return HUDDLE_API_TOKEN

	def poll_cards(self):
		url = 'https://portal.fantasy.top/card'
		headers = {'x-api-key': FANTASY_TOP_API_KEY}
		params = {'$limit': 100, '$skip': 0}
		total_cards = 0

		while True:
			response = requests.get(url, headers=headers, params=params)
			data = response.json()
			cards = data.get('data', [])
			
			if not cards:
				break

			for card_data in cards:
				# Convert string dates to datetime objects if necessary
				card_data['created_at'] = card_data.get('created_at')
				card_data['updated_at'] = card_data.get('updated_at')
				card_data['timestamp'] = card_data.get('timestamp')

				# Ensure all required fields are present
				card_defaults = {
					'owner': card_data.get('owner', ''),
					'hero_id': card_data.get('hero_id', ''),
					'rarity': card_data.get('rarity', 0),
					'hero_rarity_index': card_data.get('hero_rarity_index', ''),
					'token_id': card_data.get('token_id', ''),
					'season': card_data.get('season', 0),
					'created_at': card_data.get('created_at'),
					'updated_at': card_data.get('updated_at'),
					'tx_hash': card_data.get('tx_hash', ''),
					'blocknumber': card_data.get('blocknumber', 0),
					'timestamp': card_data.get('timestamp'),
					'picture': card_data.get('picture', ''),
				}

				Card.objects.update_or_create(
					id=card_data['id'],
					defaults=card_defaults
				)

			total_cards += len(cards)
			self.stdout.write(f'Processed {total_cards} cards so far.')
			params['$skip'] += params['$limit']
			time.sleep(1)  # Wait for 1 second before the next API call

		self.stdout.write(f'All cards data updated. Total cards: {total_cards}')

	def poll_heroes(self):
		url = 'https://portal.fantasy.top/hero'
		headers = {'x-api-key': FANTASY_TOP_API_KEY}
		params = {'$skip': 0}
		total_heroes = 0
		status_counts = {}

		# Get initial response to get the total number of heroes
		response = requests.get(url, headers=headers, params=params)
		data = response.json()
		total = data.get('total', 0)

		def safe_decimal(value, default=Decimal('0')):
			if value is None:
				return Decimal('0')
			try:
				return Decimal(str(value).replace(',', '') or default)
			except (ValueError, TypeError):
				return default

		while params['$skip'] < total:
			heroes = data.get('data', [])
			
			for hero_data in heroes:
				# Convert string counts to integers
				hero_data['favourites_count'] = int(hero_data.get('favourites_count', '0').replace(',', '') or 0)
				hero_data['followers_count'] = int(hero_data.get('followers_count', '0').replace(',', '') or 0)
				hero_data['fast_followers_count'] = int(hero_data.get('fast_followers_count', 0) or 0)
				hero_data['friends_count'] = int(hero_data.get('friends_count', 0) or 0)
				hero_data['listed_count'] = int(hero_data.get('listed_count', 0) or 0)
				hero_data['media_count'] = int(hero_data.get('media_count', 0) or 0)
				hero_data['statuses_count'] = int(hero_data.get('statuses_count', 0) or 0)
				hero_data['stars'] = int(hero_data.get('stars', 0) or 0)
				hero_data['previous_stars'] = int(hero_data.get('previous_stars', 0) or 0)
				hero_data['star_gain'] = int(hero_data.get('star_gain', 0) or 0)

				# Fetch additional data only for heroes with status "HERO"
				hero_detail_data = {}
				if hero_data.get('status') == "HERO":
					hero_detail_url = f'https://portal.fantasy.top/hero/{hero_data["id"]}'
					hero_detail_response = requests.get(hero_detail_url, headers=headers)
					hero_detail_data = hero_detail_response.json()
					time.sleep(1)  # Wait for 1 second before the next API call


				hero_defaults = {
					'handle': hero_data.get('handle', ''),
					'name': hero_data.get('name', ''),
					'previous_rank': hero_data.get('previous_rank', 0),
					'is_player': hero_data.get('is_player', False),
					'is_blue_verified': hero_data.get('is_blue_verified', False),
					'default_profile_image': hero_data.get('default_profile_image', False),
					'description': hero_data.get('description', ''),
					'fast_followers_count': hero_data.get('fast_followers_count', 0),
					'favourites_count': hero_data.get('favourites_count', 0),
					'followers_count': hero_data.get('followers_count', 0),
					'friends_count': hero_data.get('friends_count', 0),
					'listed_count': hero_data.get('listed_count', 0),
					'location': hero_data.get('location', ''),
					'media_count': hero_data.get('media_count', 0),
					'possibly_sensitive': hero_data.get('possibly_sensitive', False),
					'profile_banner_url': hero_data.get('profile_banner_url', ''),
					'profile_image_url_https': hero_data.get('profile_image_url_https', ''),
					'has_banner': hero_data.get('has_banner', False),
					'verified': hero_data.get('verified', False),
					'created_at': hero_data.get('created_at'),
					'updated_at': hero_data.get('updated_at'),
					'statuses_count': hero_data.get('statuses_count', 0),
					'stars': hero_data.get('stars', 0),
					'player_address': hero_data.get('player_address', ''),
					'can_be_packed': hero_data.get('can_be_packed', False),
					'previous_stars': hero_data.get('previous_stars', 0),
					'star_gain': hero_data.get('star_gain', 0),
					'status': hero_data.get('status', ''),
					'current_rank': hero_detail_data.get('current_rank'),
					'fantasy_score': float(hero_detail_data.get('fantasy_score', 0)),
					'tactic_image_prefix': hero_detail_data.get('tactic_image_prefix', ''),
					'volume': safe_decimal(hero_detail_data.get('volume')),
					'last_sale': int(hero_detail_data.get('last_sale', 0)),
				}

				# Get the status and update the count
				status = hero_data.get('status', 'Unknown')
				status_counts[status] = status_counts.get(status, 0) + 1

				# Print the status for each hero
				self.stdout.write(f"Hero {hero_data['id']} status: {status}")				

				for field, value in hero_defaults.items():
					try:
						Hero.objects.filter(id=hero_data['id']).update(**{field: value})
					except Exception as e:
						self.stdout.write(self.style.ERROR(f"Error updating field '{field}' with value '{value}': {str(e)}"))
						self.stdout.write(self.style.ERROR(f"Type of value: {type(value)}"))
						self.stdout.write(self.style.ERROR(f"Hero ID: {hero_data['id']}"))

				try:
					hero, created = Hero.objects.update_or_create(
						id=hero_data['id'],
						defaults=hero_defaults
					)
				except IntegrityError as e:
					self.stdout.write(self.style.ERROR(f"IntegrityError for hero {hero_data['id']}: {str(e)}"))
					self.stdout.write(self.style.ERROR(f"Hero data: {hero_defaults}"))
				except Exception as e:
					self.stdout.write(self.style.ERROR(f"Unexpected error for hero {hero_data['id']}: {str(e)}"))
					self.stdout.write(self.style.ERROR(f"Hero data: {hero_defaults}"))

				# Update or create FloorPrice instances
				for floor_price_data in hero_detail_data.get('floor_prices', []):
					FloorPrice.objects.update_or_create(
						hero=hero,
						rarity=floor_price_data['rarity'],
						defaults={'price': floor_price_data['price']}
					)

				# Update or create HighestBid instances
				for highest_bid_data in hero_detail_data.get('highest_bids', []):
					HighestBid.objects.update_or_create(
						hero=hero,
						rarity=highest_bid_data['rarity'],
						defaults={'price': int(highest_bid_data['price'])}
					)

				# Update or create CardSupply instances
				for card_supply_data in hero_detail_data.get('card_supply', []):
					CardSupply.objects.update_or_create(
						hero=hero,
						rarity=card_supply_data['rarity'],
						defaults={
							'amount': card_supply_data['amount'],
							'burnt': card_supply_data['burnt'],
							'total': card_supply_data['total']
						}
					)

			total_heroes += len(heroes)
			self.stdout.write(f'Processed {total_heroes} heroes out of {total}.')
			params['$skip'] += len(heroes)
			
			if params['$skip'] < total:
				response = requests.get(url, headers=headers, params=params)
				data = response.json()
			
			time.sleep(1)  # Wait for 1 second before the next API call

		self.stdout.write("\nStatus Summary:")
		for status, count in status_counts.items():
			self.stdout.write(f"{status}: {count}")

		self.stdout.write(f'All heroes data updated. Total heroes: {total_heroes}')

	def poll_players(self):
		url = 'https://portal.fantasy.top/players'
		headers = {'x-api-key': FANTASY_TOP_API_KEY}
		response = requests.get(url, headers=headers)
		players = response.json()
		for player_data in players:
			Player.objects.update_or_create(id=player_data['id'], defaults=player_data)
		self.stdout.write('Players data updated.')
		

	def fetch_hero_scores(self, HUDDLE_API_TOKEN):
		url = "https://api.huddle.wtf/api/analytics/heroes-scores"
		headers = {
			"accept": "application/json, text/plain, */*",
			"authorization": f"Bearer {HUDDLE_API_TOKEN}",
			"cache-control": "no-cache",
			"expires": "0",
			"pragma": "no-cache",
		}

		try:
			response = requests.get(url, headers=headers)
			response.raise_for_status()
			hero_data_list = response.json()  # Assuming the API returns a list of hero data

			for hero_data in hero_data_list:
				hero_id = hero_data.get('hero_id')
				name = hero_data.get('name')

				# Convert string fields to float, handling None values
				def safe_float(value, default=0.0):
					try:
						return float(value) if value is not None else default
					except ValueError:
						logging.warning(f"Could not convert {value} to float for hero {hero_id}")
						return default

				current_score = safe_float(hero_data.get('current_score'))
				median_7_days = safe_float(hero_data.get('median_7_days'))
				median_14_days = safe_float(hero_data.get('median_14_days'))
				change_1_day = safe_float(hero_data.get('change_1_day'))
				change_7_days = safe_float(hero_data.get('change_7_days'))

				# Get the Hero instance
				try:
					hero = Hero.objects.get(id=hero_id)
				except Hero.DoesNotExist:
					logging.warning(f"Hero not found: id={hero_id}, name={name}")
					continue

				# Update Hero fields
				hero.name = name
				hero.current_score = current_score
				hero.median_7_days = median_7_days
				hero.median_14_days = median_14_days
				hero.change_1_day = change_1_day
				hero.change_7_days = change_7_days
				hero.save()

				# Process historical scores
				dates = hero_data.get('dates', [])
				data_scores = hero_data.get('data', [])

				for date_str, score_str in zip(dates, data_scores):
					# Parse the date and score
					try:
						date = datetime.strptime(date_str[:10], '%Y-%m-%d').date()
						score = safe_float(score_str)

						# Update or create HeroScore instance
						HeroScore.objects.update_or_create(
							hero=hero,
							date=date,
							defaults={'score': score}
						)
					except ValueError as e:
						logging.warning(f"Error processing date or score for hero {hero_id}: {e}")

		except requests.exceptions.HTTPError as http_err:
			logging.error(f"HTTP error occurred: {http_err}")
		except Exception as err:
			logging.error(f"An error occurred: {err}")


	# Add this method to the Command class
	def fetch_tournament_scores(self, HUDDLE_API_TOKEN):
		url = "https://api.huddle.wtf/api/analytics/tournament-scores"
		headers = {
			"accept": "application/json, text/plain, */*",
			"authorization": f"Bearer {HUDDLE_API_TOKEN}",
			"cache-control": "no-cache",
			"expires": "0",
			"pragma": "no-cache",
		}

		try:
			response = requests.get(url, headers=headers)
			response.raise_for_status()
			tournament_data = response.json()

			for item in tournament_data.get('data', []):
				hero_id = item.get('hero_id')
				name = item.get('name')
				scores = item.get('data', [])

				# Get or create the Hero instance
				hero, created = Hero.objects.get_or_create(id=hero_id, defaults={'name': name})

				# Create or update TournamentScore instances
				for index, score in enumerate(scores):
					TournamentScore.objects.update_or_create(
						hero=hero,
						index=index,
						defaults={'score': score}
					)

			self.stdout.write(self.style.SUCCESS('Tournament scores updated successfully'))

		except requests.exceptions.RequestException as e:
			self.stdout.write(self.style.ERROR(f'Error fetching tournament scores: {e}'))