"""
Realtor.com Homes Scraper - For-Sale Property Listings

Extracts property data from Realtor.com for-sale listings including:
- Property details (price, sqft, beds, baths, etc.)
- Investment metrics (price per sqft, 1% rule estimates)
- Market indicators (days on market, status)
"""

from bs4 import BeautifulSoup
import pandas as pd
import requests
import time
import random
from typing import List, Dict, Optional
import json
import re


class RealtorHomesScraper:
    """Scraper for Realtor.com for-sale listings with polite rate limiting."""

    BASE_URL = "https://www.realtor.com"

    def __init__(self, search_url: str, min_delay: float = 5.0, max_delay: float = 8.0):
        """
        Initialize scraper with search URL and delay settings.

        Args:
            search_url: Full URL to Realtor.com search results
            min_delay: Minimum seconds between requests (default 5)
            max_delay: Maximum seconds between requests (default 8)
        """
        self.search_url = search_url
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.properties_data = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

    def _polite_delay(self):
        """Random delay between requests to be respectful to the host."""
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)

    def _extract_search_page_data(self, url: str) -> Optional[Dict]:
        """Extract JSON data from search results page."""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # Look for script tag containing property data
            script_tags = soup.find_all("script", {"type": "application/json"})
            
            for script in script_tags:
                if script.string and "properties" in script.string:
                    try:
                        data = json.loads(script.string)
                        if "cat1" in data and "searchResults" in data["cat1"]:
                            return data["cat1"]["searchResults"]
                    except:
                        continue

            # Alternative: look for __NEXT_DATA__
            next_data_script = soup.find("script", {"id": "__NEXT_DATA__"})
            if next_data_script:
                try:
                    data = json.loads(next_data_script.string)
                    # Navigate through the structure to find properties
                    props = data.get("props", {}).get("pageProps", {})
                    if "searchResults" in props:
                        return props["searchResults"]
                except:
                    pass

            return None
        except Exception as e:
            print(f"Error extracting search data from {url}: {e}")
            return None

    def _extract_property_urls_from_page(self, url: str) -> List[str]:
        """Extract property URLs from a single search results page."""
        try:
            response = self.session.get(url)
            
            if response.status_code == 429:
                print("Rate limited - waiting longer...")
                time.sleep(30)  # Wait 30 seconds before retrying
                response = self.session.get(url)
            
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            
            property_urls = []
            
            # Look for property links
            property_links = soup.find_all("a", href=re.compile(r"/realestateandhomes-detail/"))
            
            for link in property_links:
                href = link.get("href")
                if href and "/realestateandhomes-detail/" in href:
                    if href.startswith("/"):
                        href = self.BASE_URL + href
                    property_urls.append(href)
            
            return list(set(property_urls))  # Remove duplicates
            
        except Exception as e:
            print(f"Error extracting property URLs from {url}: {e}")
            return []

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
                url = f"{self.search_url}{separator}pg={page}"

            print(f"Fetching page {page}...")
            page_urls = self._extract_property_urls_from_page(url)
            
            if not page_urls:
                print(f"No listings found on page {page}")
                break

            listing_urls.extend(page_urls)
            print(f"Found {len(page_urls)} listings on page {page}")

            # Check if there's a next page by looking for pagination
            try:
                response = self.session.get(url)
                soup = BeautifulSoup(response.content, "html.parser")
                next_page = soup.find("a", {"aria-label": "Go to next page"})
                if not next_page:
                    print("No more pages available")
                    break
            except:
                # If we can't determine pagination, try a few more pages
                if page >= 10:  # Reasonable limit
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
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Extract data from JSON-LD structured data
            json_ld_scripts = soup.find_all("script", {"type": "application/ld+json"})
            property_data = {}
            
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get("@type") == "SingleFamilyResidence":
                        property_data = data
                        break
                except:
                    continue
            
            # Extract from page content if JSON-LD not found
            if not property_data:
                property_data = self._extract_from_page_content(soup)
            
            if not property_data:
                return None

            # Extract and structure the property information
            property_info = self._structure_property_data(property_data, url, soup)
            property_info.update(self._calculate_metrics(property_info))
            
            return property_info
            
        except Exception as e:
            print(f"Error scraping property {url}: {e}")
            return None

    def _extract_from_page_content(self, soup: BeautifulSoup) -> Dict:
        """Extract property data from page content when JSON-LD is not available."""
        data = {}
        
        try:
            # Extract price
            price_elem = soup.find("span", {"data-testid": "property-meta-price"})
            if price_elem:
                price_text = price_elem.get_text().strip()
                data["price"] = self._parse_price(price_text)
            
            # Extract basic details
            details_section = soup.find("div", {"data-testid": "property-meta"})
            if details_section:
                # Look for bed/bath/sqft info
                meta_items = details_section.find_all("li")
                for item in meta_items:
                    text = item.get_text().lower()
                    if "bed" in text:
                        data["bedrooms"] = self._parse_number_from_text(text)
                    elif "bath" in text:
                        data["bathrooms"] = self._parse_number_from_text(text)
                    elif "sqft" in text or "sq ft" in text:
                        data["sqft"] = self._parse_number_from_text(text)
            
            # Extract address
            address_elem = soup.find("h1", {"data-testid": "property-street"})
            if address_elem:
                data["address"] = address_elem.get_text().strip()
            
            # Extract city, state, zip
            location_elem = soup.find("div", {"data-testid": "property-locality"})
            if location_elem:
                location_text = location_elem.get_text().strip()
                parts = location_text.split(",")
                if len(parts) >= 2:
                    data["city"] = parts[0].strip()
                    state_zip = parts[1].strip().split()
                    if state_zip:
                        data["state"] = state_zip[0]
                        if len(state_zip) > 1:
                            data["zip"] = state_zip[1]
            
        except Exception as e:
            print(f"Error extracting from page content: {e}")
        
        return data

    def _structure_property_data(self, data: Dict, url: str, soup: BeautifulSoup) -> Dict:
        """Structure the extracted data into standardized format."""
        
        # Handle both JSON-LD and scraped data formats
        if "@type" in data:  # JSON-LD format
            address_data = data.get("address", {})
            if isinstance(address_data, dict):
                street = address_data.get("streetAddress", "")
                city = address_data.get("addressLocality", "")
                state = address_data.get("addressRegion", "")
                zip_code = address_data.get("postalCode", "")
            else:
                street = city = state = zip_code = ""
            
            price = data.get("offers", {}).get("price")
            if isinstance(price, str):
                price = self._parse_price(price)
            
            floor_size = data.get("floorSize", {})
            if isinstance(floor_size, dict):
                sqft = floor_size.get("value", 0)
            else:
                sqft = self._parse_number(str(floor_size)) if floor_size else 0
            
        else:  # Scraped data format
            street = data.get("address", "")
            city = data.get("city", "")
            state = data.get("state", "")
            zip_code = data.get("zip", "")
            price = data.get("price", 0)
            sqft = data.get("sqft", 0)

        # Extract agent/agency info from page
        agent_info = self._extract_agent_info(soup)
        
        property_info = {
            'listing_id': self._extract_listing_id(url),
            'address': street,
            'city': city,
            'state': state,
            'zip': zip_code,
            'url': url,
            'property_type': data.get("@type", "SingleFamilyResidence").replace("Residence", " Home"),
            'price': price,
            'sqft': sqft,
            'bedrooms': data.get("numberOfRooms") or data.get("bedrooms", 0),
            'bathrooms': data.get("numberOfBathroomsTotal") or data.get("bathrooms", 0),
            'lot_size_acres': None,  # Not commonly available on Realtor.com
            'year_built': data.get("yearBuilt"),
            'garage': None,  # Extract if available
            'school_district': None,  # Extract if available
            'heating': None,
            'cooling': None,
            'status': self._extract_status(soup),
            'days_on_market': self._extract_days_on_market(soup),
            'mls_number': self._extract_mls_number(soup),
            'agent_name': agent_info.get('agent_name'),
            'agency_name': agent_info.get('agency_name'),
            'seller_type': 'Realtor',  # Default for Realtor.com
            'view_count': None,  # Not available
            'favorite_count': None,  # Not available
        }

        return property_info

    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parse price from text like '$450,000' or '$450K'."""
        if not price_text:
            return None
        
        # Remove $ and commas
        clean_price = re.sub(r'[,$]', '', price_text.upper())
        
        # Handle K/M suffixes
        if 'K' in clean_price:
            number = float(re.sub(r'[^0-9.]', '', clean_price))
            return number * 1000
        elif 'M' in clean_price:
            number = float(re.sub(r'[^0-9.]', '', clean_price))
            return number * 1000000
        else:
            try:
                return float(re.sub(r'[^0-9.]', '', clean_price))
            except:
                return None

    def _parse_number_from_text(self, text: str) -> Optional[float]:
        """Extract number from text like '3 bed' or '2,100 sqft'."""
        numbers = re.findall(r'[\d,]+\.?\d*', text.replace(',', ''))
        if numbers:
            try:
                return float(numbers[0])
            except:
                pass
        return None

    def _parse_number(self, value) -> float:
        """Parse number from string with commas."""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            return float(value.replace(',', ''))
        return 0.0

    def _extract_listing_id(self, url: str) -> Optional[str]:
        """Extract listing ID from URL."""
        match = re.search(r'/([^/]+)_M\d+', url)
        if match:
            return match.group(1)
        return None

    def _extract_agent_info(self, soup: BeautifulSoup) -> Dict:
        """Extract agent and agency information."""
        agent_info = {'agent_name': None, 'agency_name': None}
        
        try:
            # Look for agent name
            agent_elem = soup.find("div", {"data-testid": "agent-name"})
            if not agent_elem:
                agent_elem = soup.find("span", string=re.compile(r"Listed by"))
            
            if agent_elem:
                agent_text = agent_elem.get_text()
                # Extract agent name from "Listed by Agent Name"
                match = re.search(r"Listed by (.+)", agent_text)
                if match:
                    agent_info['agent_name'] = match.group(1).strip()
            
            # Look for agency name
            agency_elem = soup.find("div", {"data-testid": "agent-company"})
            if agency_elem:
                agent_info['agency_name'] = agency_elem.get_text().strip()
                
        except Exception as e:
            print(f"Error extracting agent info: {e}")
        
        return agent_info

    def _extract_status(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract property status."""
        try:
            status_elem = soup.find("span", {"data-testid": "property-status"})
            if status_elem:
                return status_elem.get_text().strip()
        except:
            pass
        return "For Sale"  # Default

    def _extract_days_on_market(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract days on market."""
        try:
            dom_elem = soup.find(string=re.compile(r"days? on market", re.I))
            if dom_elem:
                numbers = re.findall(r'\d+', dom_elem)
                if numbers:
                    return int(numbers[0])
        except:
            pass
        return None

    def _extract_mls_number(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract MLS number."""
        try:
            mls_elem = soup.find(string=re.compile(r"MLS", re.I))
            if mls_elem:
                # Look for pattern like "MLS# 12345"
                match = re.search(r"MLS[#\s]*(\w+)", mls_elem, re.I)
                if match:
                    return match.group(1)
        except:
            pass
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

    def save_to_csv(self, filename: str = 'realtor_homes_data.csv'):
        """Save scraped data to CSV file."""
        if self.properties_data:
            df = pd.DataFrame(self.properties_data)
            df.to_csv(filename, index=False)
            print(f"Data saved to {filename}")
        else:
            print("No data to save")