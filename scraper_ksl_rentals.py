"""
KSL Rentals Scraper - Rental Property Listings

Extracts rental property data from KSL Homes rental listings including:
- Rental details (monthly rent, bedrooms, sqft, etc.)
- Rental metrics (rent per sqft, annual rent)
- Pet policies and other rental-specific information
"""

from bs4 import BeautifulSoup
import pandas as pd
import requests
import time
import random
from typing import List, Dict, Optional
import json


class KSLRentalsScraper:
    """Scraper for KSL rental listings with polite rate limiting."""

    BASE_URL = "https://homes.ksl.com"

    def __init__(self, search_url: str, min_delay: float = 2.0, max_delay: float = 5.0):
        """
        Initialize rental scraper with search URL and delay settings.

        Args:
            search_url: Full URL to KSL rental search results
            min_delay: Minimum seconds between requests (default 2)
            max_delay: Maximum seconds between requests (default 5)
        """
        self.search_url = search_url
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.rentals_data = []

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

    def _extract_rental_detail_data(self, url: str) -> Optional[Dict]:
        """Extract rental data from detail page using Schema.org JSON-LD."""
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            rental_data = {}

            json_ld_scripts = soup.find_all("script", {"type": "application/ld+json"})

            for script in json_ld_scripts:
                try:
                    ld_data = json.loads(script.string)

                    if isinstance(ld_data, dict):
                        if ld_data.get('@type') == 'Product':
                            offers = ld_data.get('offers', {})
                            if isinstance(offers, dict):
                                if offers.get('@type') == 'AggregateOffer':
                                    low_price = offers.get('lowPrice')
                                    if low_price:
                                        rental_data['price'] = float(low_price)
                                elif offers.get('price'):
                                    rental_data['price'] = float(offers.get('price'))

                        if ld_data.get('@type') == 'RentAction':
                            price = ld_data.get('price')
                            if price and not rental_data.get('price'):
                                rental_data['price'] = float(price)

                        main_entity = ld_data.get('mainEntity', {})
                        entity_type = main_entity.get('@type', '')

                        # Handle both spellings (KSL has a typo: "Accomodation")
                        if entity_type in ['Accommodation', 'Accomodation']:
                            address = main_entity.get('address', {})
                            if isinstance(address, dict):
                                rental_data['address1'] = address.get('streetAddress')
                                rental_data['city'] = address.get('addressLocality')
                                rental_data['state'] = address.get('addressRegion')
                                rental_data['zip'] = address.get('postalCode')

                            if not rental_data.get('city'):
                                full_name = main_entity.get('name', '')
                                if full_name:
                                    parts = full_name.split(',')
                                    if len(parts) >= 3:
                                        rental_data['address1'] = parts[0].strip()
                                        rental_data['city'] = parts[1].strip()
                                        state_zip = parts[2].strip().split()
                                        if len(state_zip) >= 2:
                                            rental_data['state'] = state_zip[0]
                                            rental_data['zip'] = state_zip[1]

                            floor_size = main_entity.get('floorSize', {})
                            if isinstance(floor_size, dict):
                                rental_data['squareFoot'] = floor_size.get('value')

                            rental_data['bed'] = main_entity.get('numberOfRooms')
                            rental_data['petsAllowed'] = main_entity.get('petsAllowed')

                except json.JSONDecodeError:
                    continue

            return rental_data if rental_data else None

        except Exception as e:
            print(f"Error extracting rental data from {url}: {e}")
            return None

    def get_rental_urls(self, max_pages: Optional[int] = None) -> List[str]:
        """
        Get all rental listing URLs from search results.

        Args:
            max_pages: Maximum number of pages to scrape (None = all pages)

        Returns:
            List of rental detail page URLs
        """
        rental_urls = []
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
                link = listing.get('link')
                if link:
                    if not link.startswith('http'):
                        link = f"{self.BASE_URL}{link}"
                    rental_urls.append(link)

            print(f"Found {len(listings)} rentals on page {page}")

            total_count = data.get('totalCount', 0)
            current_count = page * 12
            has_more = current_count < total_count

            if not has_more:
                print("No more pages available")
                break

            page += 1
            self._polite_delay()

        # Remove duplicates while preserving order
        unique_urls = list(dict.fromkeys(rental_urls))
        print(f"\nTotal rentals found: {len(rental_urls)} ({len(unique_urls)} unique)")
        return unique_urls

    def scrape_rental(self, url: str) -> Optional[Dict]:
        """
        Scrape rental-specific data from individual listing page.

        Args:
            url: Rental detail page URL

        Returns:
            Dictionary with rental-specific data
        """
        print(f"Scraping: {url}")
        data = self._extract_rental_detail_data(url)

        if not data:
            print("No data extracted")
            return None

        rental_info = {
            'listing_id': url.split('/')[-1] if '/' in url else None,
            'address': data.get('address1'),
            'city': data.get('city'),
            'state': data.get('state'),
            'zip': data.get('zip'),
            'url': url,
            'monthly_rent': data.get('price'),
            'property_type': data.get('propertyType', 'Rental'),
            'sqft': self._parse_number(data.get('squareFoot', '0')),
            'bedrooms': data.get('bed'),
            'bathrooms': data.get('bath'),
            'pets_allowed': data.get('petsAllowed'),
        }

        rental_info.update(self._calculate_rental_metrics(rental_info))

        return rental_info

    def _parse_number(self, value) -> float:
        """Parse number from string with commas."""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            return float(value.replace(',', ''))
        return 0.0

    def _calculate_rental_metrics(self, rental: Dict) -> Dict:
        """Calculate rental-specific investment metrics."""
        metrics = {}

        if rental['monthly_rent']:
            metrics['annual_rent'] = rental['monthly_rent'] * 12
        else:
            metrics['annual_rent'] = None

        if rental['monthly_rent'] and rental['sqft'] and rental['sqft'] > 0:
            metrics['rent_per_sqft'] = round(rental['monthly_rent'] / rental['sqft'], 2)
        else:
            metrics['rent_per_sqft'] = None

        return metrics

    def scrape_all(self, max_pages: Optional[int] = None, max_rentals: Optional[int] = None) -> pd.DataFrame:
        """
        Main method to scrape all rental properties from search results.

        Args:
            max_pages: Limit number of search result pages to scrape (None = all)
            max_rentals: Limit total number of rentals to scrape (None = all)

        Returns:
            DataFrame with all scraped rental data
        """
        self.rentals_data = []
        rental_urls = self.get_rental_urls(max_pages=max_pages)

        if max_rentals:
            rental_urls = rental_urls[:max_rentals]

        print(f"\nScraping {len(rental_urls)} rental details...")
        for i, url in enumerate(rental_urls, 1):
            print(f"\n[{i}/{len(rental_urls)}]", end=" ")

            rental_data = self.scrape_rental(url)
            if rental_data:
                self.rentals_data.append(rental_data)

            if i < len(rental_urls):
                self._polite_delay()

        df = pd.DataFrame(self.rentals_data)
        print(f"\n\nSuccessfully scraped {len(df)} rentals")
        return df

    def save_to_csv(self, filename: str = 'ksl_rentals_data.csv'):
        """Save scraped rental data to CSV file."""
        if self.rentals_data:
            df = pd.DataFrame(self.rentals_data)
            df.to_csv(filename, index=False)
            print(f"Rental data saved to {filename}")
        else:
            print("No data to save")
