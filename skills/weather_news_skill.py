import os
import requests
import logging
from typing import Optional
from geopy.geocoders import Nominatim

logger = logging.getLogger("jarvis.skills.weather_news")

class WeatherNewsSkill:
    def __init__(self):
        # 7Timer! doesn't need a key!
        self.news_key = os.getenv("NEWS_API_KEY")
        self.geolocator = Nominatim(user_agent="jarvis_ai_assistant")

    def get_weather(self, city: str = "Mumbai") -> str:
        """Fetch current weather for a city using 7Timer! (No API Key Required)."""
        try:
            # 1. Geocode city to Lat/Lon
            location = self.geolocator.geocode(city)
            if not location:
                return f"I couldn't find the location for {city}, Sir."

            lat = location.latitude
            lon = location.longitude

            # 2. Call 7Timer! API
            # Product 'civil' is good for general weather
            url = f"http://www.7timer.info/bin/api.pl?lon={lon}&lat={lat}&product=civil&output=json"
            response = requests.get(url, timeout=10)
            data = response.json()

            if "dataseries" in data and data["dataseries"]:
                # Get the first forecast point (current/near-term)
                current = data["dataseries"][0]
                temp = current["temp2m"]
                weather = current["weather"]
                
                # Simple mapping for 7Timer weather codes
                # You can expand this based on 7Timer documentation
                weather_map = {
                    "clearday": "clear skies",
                    "clearnight": "clear night skies",
                    "pcloudyday": "partly cloudy",
                    "pcloudynight": "partly cloudy night",
                    "mcloudyday": "mostly cloudy",
                    "mcloudynight": "mostly cloudy night",
                    "cloudyday": "cloudy",
                    "cloudynight": "cloudy night",
                    "humidday": "humid and cloudy",
                    "humidnight": "humid and cloudy night",
                    "lightrainday": "light rain",
                    "lightrainnight": "light rain night",
                    "oshowerday": "occasional showers",
                    "oshowernight": "occasional showers at night",
                    "ishowerday": "isolated showers",
                    "ishowernight": "isolated showers at night",
                    "lightsnowday": "light snow",
                    "lightsnownight": "light snow night",
                    "rainday": "rainy",
                    "rainnight": "rainy night",
                    "snowday": "snowy",
                    "snownight": "snowy night",
                    "rainsnowday": "rain and snow",
                    "rainsnownight": "rain and snow night"
                }
                
                desc = weather_map.get(weather, weather.replace("day", "").replace("night", ""))
                
                return f"According to 7Timer data for {city}, the temperature is approximately {temp} degrees Celsius with {desc}."
            else:
                return f"I received data for {city}, but the forecast series was empty, Sir."
                
        except Exception as e:
            logger.error(f"Weather (7Timer) failed: {e}")
            return "I'm having trouble reaching the 7Timer weather service at the moment, Sir."

    def get_news(self, query: Optional[str] = None) -> str:
        """Fetch latest news headlines from HackerNews (Free Public API, No Key Required)."""
        try:
            # 1. Get top story IDs
            top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
            response = requests.get(top_stories_url, timeout=5)
            story_ids = response.json()

            if response.status_code == 200 and story_ids:
                headlines = []
                # 2. Fetch details for the top 3 stories
                for story_id in story_ids[:3]:
                    story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                    story_resp = requests.get(story_url, timeout=5)
                    if story_resp.status_code == 200:
                        story_data = story_resp.json()
                        if story_data and "title" in story_data:
                            headlines.append(story_data["title"])
                
                if headlines:
                    report = "Here are the top tech headlines from Hacker News: " + " ... ".join(headlines)
                    return report
            
            return "I couldn't find any recent news updates, Sir."
        except Exception as e:
            logger.error(f"HackerNews API failed: {e}")
            return "The news service is currently unreachable."

# Singleton
weather_news = WeatherNewsSkill()
