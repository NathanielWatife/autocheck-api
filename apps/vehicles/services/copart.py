import requests
import os
from pathlib import Path
from dotenv import load_dotenv
import environ
import logging
import time
import random
from bs4 import BeautifulSoup
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Rotating user agents to avoid blocks
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

class CopartScraper:
    SEARCH_URL = os.getenv("COPART_SEARCH_URL")

    @classmethod
    def check_vin(cls, vin: str) -> dict:
        """
        Scrape Copart to check if VIN appears as salvage/auction.
        Returns: { found: bool, url: str, title_status: str, damage_type: str }
        """
        cache_key = f"copart:{vin}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        # Random delay to be polite and avoid rate limiting
        time.sleep(random.uniform(0.5, 1.5))

        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }

        params = {"query": vin}

        try:
            response = requests.get(cls.SEARCH_URL, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Search for VIN in page text
            page_text = soup.get_text()
            if vin.upper() not in page_text.upper():
                result = {"found": False}
                cache.set(cache_key, result, timeout=60*60*24*30)  # Cache 30 days
                return result

            # Try to extract title status and damage type
            # Copart often has "SALVAGE", "CERTIFICATE OF DESTRUCTION", "ENHANCED", etc.
            title_status = "Unknown"
            damage_type = "Unknown"
            keywords = {
                "SALVAGE": "Salvage",
                "CERTIFICATE OF DESTRUCTION": "Total_Loss",
                "ENHANCED": "Collision",
                "FLOOD": "Flood",
                "FIRE": "Fire",
                "HAIL": "Hail",
                "REBUILT": "Structural",
                "TOTAL LOSS": "Total_Loss",
            }
            for key, value in keywords.items():
                if key in page_text.upper():
                    title_status = key
                    damage_type = value
                    break

            result = {
                "found": True,
                "url": response.url,
                "title_status": title_status,
                "damage_type": damage_type,
                "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            cache.set(cache_key, result, timeout=60*60*24*30)
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Copart scrape error for VIN {vin}: {e}")
            return {"found": False, "error": str(e)}