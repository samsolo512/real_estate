"""
Combined Multi-Source Real Estate Scraper

Scrapes properties from multiple sources (KSL, Realtor.com) and ensures
that when a property count is specified, it applies to each source separately.

For example: scrape_properties(max_properties=10) will get 10 from KSL + 10 from Realtor.com
"""

import pandas as pd
from typing import Optional, List, Dict
import time
from scraper_ksl_homes import KSLHomesScraper
from scraper_realtor_homes import RealtorHomesScraper


class CombinedRealEstateScraper:
    """Combined scraper for multiple real estate sources."""
    
    def __init__(self, ksl_search_url: str, realtor_search_url: str):
        """
        Initialize with search URLs for both sources.
        
        Args:
            ksl_search_url: KSL homes search URL
            realtor_search_url: Realtor.com search URL
        """
        self.ksl_search_url = ksl_search_url
        self.realtor_search_url = realtor_search_url
        
    def scrape_properties(self, 
                         max_properties_per_source: Optional[int] = None,
                         max_pages_per_source: Optional[int] = None,
                         sources: List[str] = None) -> Dict[str, pd.DataFrame]:
        """
        Scrape properties from multiple sources.
        
        Args:
            max_properties_per_source: Max properties to scrape from EACH source
            max_pages_per_source: Max pages to scrape from EACH source
            sources: List of sources to scrape from ['ksl', 'realtor']. Default: both
            
        Returns:
            Dictionary with source names as keys and DataFrames as values
        """
        if sources is None:
            sources = ['ksl', 'realtor']
            
        results = {}
        
        # Scrape from KSL
        if 'ksl' in sources:
            print("=" * 60)
            print("SCRAPING FROM KSL HOMES")
            print("=" * 60)
            
            try:
                ksl_scraper = KSLHomesScraper(self.ksl_search_url)
                ksl_df = ksl_scraper.scrape_all(
                    max_pages=max_pages_per_source,
                    max_properties=max_properties_per_source
                )
                
                if not ksl_df.empty:
                    ksl_df['source'] = 'KSL'
                    results['ksl'] = ksl_df
                    print(f"✓ Successfully scraped {len(ksl_df)} properties from KSL")
                else:
                    print("✗ No properties scraped from KSL")
                    
            except Exception as e:
                print(f"✗ Error scraping KSL: {e}")
                
        # Scrape from Realtor.com
        if 'realtor' in sources:
            print("\n" + "=" * 60)
            print("SCRAPING FROM REALTOR.COM")
            print("=" * 60)
            
            try:
                realtor_scraper = RealtorHomesScraper(self.realtor_search_url)
                realtor_df = realtor_scraper.scrape_all(
                    max_pages=max_pages_per_source,
                    max_properties=max_properties_per_source
                )
                
                if not realtor_df.empty:
                    realtor_df['source'] = 'Realtor.com'
                    results['realtor'] = realtor_df
                    print(f"✓ Successfully scraped {len(realtor_df)} properties from Realtor.com")
                else:
                    print("✗ No properties scraped from Realtor.com")
                    
            except Exception as e:
                print(f"✗ Error scraping Realtor.com: {e}")
                
        return results
    
    def combine_results(self, results: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Combine results from all sources into a single DataFrame.
        
        Args:
            results: Dictionary of DataFrames from scrape_properties()
            
        Returns:
            Combined DataFrame with all properties
        """
        if not results:
            return pd.DataFrame()
            
        combined_df = pd.concat(results.values(), ignore_index=True)
        
        print(f"\n" + "=" * 60)
        print("COMBINED RESULTS SUMMARY")
        print("=" * 60)
        
        for source, df in results.items():
            print(f"{source.upper()}: {len(df)} properties")
            
        print(f"TOTAL: {len(combined_df)} properties")
        
        return combined_df
    
    def save_results(self, results: Dict[str, pd.DataFrame], 
                    save_individual: bool = True, 
                    save_combined: bool = True,
                    timestamp: bool = True):
        """
        Save scraping results to CSV files.
        
        Args:
            results: Dictionary of DataFrames from scrape_properties()
            save_individual: Save separate files for each source
            save_combined: Save combined file with all sources
            timestamp: Add timestamp to filenames
        """
        timestamp_str = ""
        if timestamp:
            from datetime import datetime
            timestamp_str = f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Save individual source files
        if save_individual:
            for source, df in results.items():
                filename = f"{source}_properties{timestamp_str}.csv"
                df.to_csv(filename, index=False)
                print(f"✓ Saved {source} data to {filename}")
        
        # Save combined file
        if save_combined and results:
            combined_df = self.combine_results(results)
            filename = f"combined_properties{timestamp_str}.csv"
            combined_df.to_csv(filename, index=False)
            print(f"✓ Saved combined data to {filename}")


def main():
    """Example usage of the combined scraper."""
    
    # Define search URLs for Utah
    ksl_utah_url = "https://homes.ksl.com/search?city=salt-lake-city,utah&state=utah"
    realtor_utah_url = "https://www.realtor.com/realestateandhomes-search/Utah"
    
    # Create combined scraper
    scraper = CombinedRealEstateScraper(ksl_utah_url, realtor_utah_url)
    
    # Scrape 5 properties from each source (10 total)
    print("Scraping 5 properties from each source...")
    results = scraper.scrape_properties(
        max_properties_per_source=5,
        max_pages_per_source=2
    )
    
    # Save results
    scraper.save_results(results)
    
    # Print summary
    if results:
        combined_df = scraper.combine_results(results)
        print(f"\nScraped {len(combined_df)} total properties")
        
        # Show sample data
        if not combined_df.empty:
            print("\nSample data:")
            sample_cols = ['address', 'city', 'price', 'bedrooms', 'bathrooms', 'sqft', 'source']
            available_cols = [col for col in sample_cols if col in combined_df.columns]
            print(combined_df[available_cols].head())
    else:
        print("No properties were scraped successfully")


if __name__ == "__main__":
    main()