"""
KSL Homes Scraper - For-Sale Property Listings

Extracts property data from KSL Homes for-sale listings including:
- Property details (price, sqft, beds, baths, etc.)
- Investment metrics (price per sqft, 1% rule estimates)
- Market indicators (days on market, view counts)
"""

from bs4 import BeautifulSoup
import pandas as pd
import requests
import time
import random
from typing import List, Dict, Optional
from json import JSONDecoder
import json


class KSLHomesScraper:
    """Scraper for KSL Homes for-sale listings with polite rate limiting."""

    BASE_URL = "https://homes.ksl.com"

    def __init__(self, search_url: str, min_delay: float = 2.0, max_delay: float = 5.0):
        """
        Initialize scraper with search URL and delay settings.

        Args:
            search_url: Full URL to KSL search results
            min_delay: Minimum seconds between requests (default 2)
            max_delay: Maximum seconds between requests (default 5)
        """
        self.search_url = search_url
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.properties_data = []

    def _polite_delay(self):
        """Random delay between requests to be respectful to the host."""
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)

    def _extract_search_page_json(self, url: str) -> Optional[Dict]:
        """Extract JSON data from search results page using __NEXT_DATA__."""
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            script_tag = soup.find("script", {"id": "__NEXT_DATA__", "type": "application/json"})

            if script_tag:
                data = json.loads(script_tag.string)
                return data.get('props', {}).get('pageProps', {})
            return None
        except Exception as e:
            print(f"Error extracting search data from {url}: {e}")
            return None

    def _extract_listing_json(self, url: str) -> Optional[Dict]:
        """Extract JSON data from individual listing page."""
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            script_tag = soup.find("script", string=lambda t: t and "window.ksl.listingData" in t)

            if script_tag:
                script_text = script_tag.string
                start_marker = "window.ksl.listingData = "
                start = script_text.find(start_marker) + len(start_marker)
                decoder = JSONDecoder()
                data, _ = decoder.raw_decode(script_text[start:])
                return data
            return None
        except Exception as e:
            print(f"Error extracting data from {url}: {e}")
            return None

    def get_listing_urls(self, max_pages: Optional[int] = None) -> List[str]:
        """
        Get all property listing URLs from search results.

        Args:
            max_pages: Maximum number of pages to scrape (None = all pages)

        Returns:
            List of property detail page URLs
        """
        listing_urls = []
        page = 1

        while True:
            if max_pages and page > max_pages:
                break

            if page == 1:
                url = self.search_url
            else:
                separator = '&' if '?' in self.search_url else '?'
                url = f"{self.search_url}{separator}page={page}"

            print(f"Fetching page {page}...")
            data = self._extract_search_page_json(url)

            if not data or 'listings' not in data:
                print(f"No data found on page {page}")
                break

            listings = data.get('listings', [])
            if not listings:
                print(f"No listings found on page {page}")
                break

            for listing in listings:
                listing_id = listing.get('id')
                if listing_id:
                    listing_urls.append(f"{self.BASE_URL}/listing/{listing_id}")

            print(f"Found {len(listings)} listings on page {page}")

            total_count = data.get('totalCount', 0)
            current_count = page * 12
            has_more = current_count < total_count

            if not has_more:
                print("No more pages available")
                break

            page += 1
            self._polite_delay()

        # Remove duplicates while preserving order
        unique_urls = list(dict.fromkeys(listing_urls))
        print(f"\nTotal listings found: {len(listing_urls)} ({len(unique_urls)} unique)")
        return unique_urls

    def scrape_property(self, url: str) -> Optional[Dict]:
        """
        Scrape detailed property data from individual listing page.

        Args:
            url: Property detail page URL

        Returns:
            Dictionary with extracted property data and calculated metrics
        """
        print(f"Scraping: {url}")
        data = self._extract_listing_json(url)

        if not data:
            return None

        property_info = {
            'listing_id': data.get('id'),
            'address': data.get('address1'),
            'city': data.get('city'),
            'state': data.get('state'),
            'zip': data.get('zip'),
            'url': url,
            'property_type': data.get('propertyType'),
            'price': data.get('price'),
            'sqft': self._parse_number(data.get('squareFoot', '0')),
            'bedrooms': data.get('bed'),
            'bathrooms': data.get('bath'),
            'lot_size_acres': data.get('acre'),
            'year_built': data.get('buildYear'),
            'garage': data.get('garage'),
            'school_district': data.get('schoolDistrict'),
            'heating': data.get('heating'),
            'cooling': data.get('cooling'),
            'status': data.get('status'),
            'days_on_market': self._calculate_days_on_market(data),
            'mls_number': data.get('mlsNumber'),
            'agent_name': data.get('name'),
            'agency_name': data.get('agencyName'),
            'seller_type': data.get('sellerType'),
            'view_count': data.get('statsAggregated', {}).get('hdpViewCount', 0),
            'favorite_count': data.get('statsAggregated', {}).get('favoriteCount', 0),
        }

        property_info.update(self._calculate_metrics(property_info))

        return property_info

    def _parse_number(self, value) -> float:
        """Parse number from string with commas."""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            return float(value.replace(',', ''))
        return 0.0

    def _calculate_days_on_market(self, data: Dict) -> Optional[int]:
        """Calculate days on market from listing timestamps."""
        create_time = data.get('createTime', {}).get('sec')
        if create_time:
            current_time = time.time()
            days = int((current_time - create_time) / 86400)
            return days
        return None

    def _calculate_metrics(self, prop: Dict) -> Dict:
        """Calculate investment KPIs."""
        metrics = {}

        if prop['price'] and prop['sqft'] and prop['sqft'] > 0:
            metrics['price_per_sqft'] = round(prop['price'] / prop['sqft'], 2)
        else:
            metrics['price_per_sqft'] = None

        if prop['price']:
            metrics['one_percent_rule_rent'] = round(prop['price'] * 0.01, 2)
        else:
            metrics['one_percent_rule_rent'] = None

        if prop['price'] and prop['bedrooms'] and prop['bedrooms'] > 0:
            metrics['price_per_bedroom'] = round(prop['price'] / prop['bedrooms'], 2)
        else:
            metrics['price_per_bedroom'] = None

        if prop['lot_size_acres'] and prop['lot_size_acres'] > 0:
            metrics['price_per_acre'] = round(prop['price'] / prop['lot_size_acres'], 2)
        else:
            metrics['price_per_acre'] = None

        return metrics

    def scrape_all(self, max_pages: Optional[int] = None, max_properties: Optional[int] = None) -> pd.DataFrame:
        """
        Main method to scrape all properties from search results.

        Args:
            max_pages: Limit number of search result pages to scrape (None = all)
            max_properties: Limit total number of properties to scrape (None = all)

        Returns:
            DataFrame with all scraped property data
        """
        self.properties_data = []
        listing_urls = self.get_listing_urls(max_pages=max_pages)

        if max_properties:
            listing_urls = listing_urls[:max_properties]

        print(f"\nScraping {len(listing_urls)} property details...")
        for i, url in enumerate(listing_urls, 1):
            print(f"\n[{i}/{len(listing_urls)}]", end=" ")

            property_data = self.scrape_property(url)
            if property_data:
                self.properties_data.append(property_data)

            if i < len(listing_urls):
                self._polite_delay()

        df = pd.DataFrame(self.properties_data)
        print(f"\n\nSuccessfully scraped {len(df)} properties")
        return df

    def save_to_csv(self, filename: str = 'ksl_homes_data.csv'):
        """Save scraped data to CSV file."""
        if self.properties_data:
            df = pd.DataFrame(self.properties_data)
            df.to_csv(filename, index=False)
            print(f"Data saved to {filename}")
        else:
            print("No data to save")
