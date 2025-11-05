"""
KSL Real Estate Scraper - Main Entry Point

This script scrapes KSL Homes listings for both for-sale and rental properties,
then calculates investment metrics to identify the best opportunities.

Usage:
    # Scrape default 20 homes and 20 rentals
    python main.py

    # Scrape specific number of homes and rentals
    python main.py --max-homes 10 --max-rentals 5

    # Scrape only homes
    python main.py --max-rentals 0

    # Scrape only rentals
    python main.py --max-homes 0
"""

import argparse
from ksl_homes_scraper import KSLHomesScraper
from ksl_rentals_scraper import KSLRentalsScraper
from investment_analyzer import calculate_investment_metrics, get_top_deals


def main():
    parser = argparse.ArgumentParser(
        description='Scrape KSL Homes listings and calculate investment metrics'
    )

    # Scraping limits
    parser.add_argument(
        '--max-homes',
        type=int,
        default=20,
        help='Maximum number of for-sale homes to scrape (default: 20)'
    )
    parser.add_argument(
        '--max-rentals',
        type=int,
        default=20,
        help='Maximum number of rentals to scrape (default: 20)'
    )

    # Search URLs
    parser.add_argument(
        '--homes-url',
        type=str,
        default='https://homes.ksl.com/search/herriman/UT/single-family-home;townhome-condo',
        help='URL for homes search'
    )
    parser.add_argument(
        '--rentals-url',
        type=str,
        default='https://homes.ksl.com/rent/search/ut/herriman/condo-multiplex;house;townhome',
        help='URL for rentals search'
    )

    # Rate limiting
    parser.add_argument(
        '--min-delay',
        type=float,
        default=2.0,
        help='Minimum delay between requests in seconds (default: 2.0)'
    )
    parser.add_argument(
        '--max-delay',
        type=float,
        default=5.0,
        help='Maximum delay between requests in seconds (default: 5.0)'
    )

    # Output
    parser.add_argument(
        '--output-prefix',
        type=str,
        default='herriman',
        help='Prefix for output CSV files (default: herriman)'
    )

    # Top deals
    parser.add_argument(
        '--top-deals',
        type=int,
        default=None,
        help='Number of top investment deals to display (default: min of homes/rentals scraped)'
    )

    args = parser.parse_args()

    # Scrape for-sale homes
    df_homes = None
    if args.max_homes > 0:
        print("=" * 80)
        print("SCRAPING FOR-SALE HOMES")
        print("=" * 80)

        homes_scraper = KSLHomesScraper(
            args.homes_url,
            min_delay=args.min_delay,
            max_delay=args.max_delay
        )

        df_homes = homes_scraper.scrape_all(max_properties=args.max_homes)

        if len(df_homes) > 0:
            homes_file = f'{args.output_prefix}_homes.csv'
            homes_scraper.save_to_csv(homes_file)
            print(f"\nSuccessfully scraped {len(df_homes)} homes")
        else:
            print("\nNo homes were scraped")
    else:
        print("Skipping homes scraping (--max-homes=0)")

    # Scrape rentals
    df_rentals = None
    if args.max_rentals > 0:
        print("\n" + "=" * 80)
        print("SCRAPING RENTALS")
        print("=" * 80)

        rentals_scraper = KSLRentalsScraper(
            args.rentals_url,
            min_delay=args.min_delay,
            max_delay=args.max_delay
        )

        df_rentals = rentals_scraper.scrape_all(max_rentals=args.max_rentals)

        if len(df_rentals) > 0:
            rentals_file = f'{args.output_prefix}_rentals.csv'
            rentals_scraper.save_to_csv(rentals_file)
            print(f"\nSuccessfully scraped {len(df_rentals)} rentals")
        else:
            print("\nNo rentals were scraped")
    else:
        print("Skipping rentals scraping (--max-rentals=0)")

    # Calculate investment metrics if both datasets exist
    if df_homes is not None and df_rentals is not None and len(df_homes) > 0 and len(df_rentals) > 0:
        print("\n" + "=" * 80)
        print("CALCULATING INVESTMENT METRICS")
        print("=" * 80)

        analysis_df = calculate_investment_metrics(df_homes, df_rentals)

        analysis_file = f'{args.output_prefix}_investment_analysis.csv'
        analysis_df.to_csv(analysis_file, index=False)
        print(f"\nInvestment analysis saved to {analysis_file}")

        # Determine number of top deals to display
        if args.top_deals is None:
            # Default to the smaller of homes or rentals count
            num_top_deals = min(len(df_homes), len(df_rentals))
        else:
            num_top_deals = args.top_deals

        # Display top deals
        print("\n" + "=" * 80)
        print(f"TOP {num_top_deals} INVESTMENT OPPORTUNITIES (BEST TO WORST)")
        print("=" * 80)
        top_deals = get_top_deals(analysis_df, top_n=num_top_deals)
        print(top_deals.to_string(index=False))

        print("\n" + "=" * 80)
        print("INVESTMENT METRICS LEGEND")
        print("=" * 80)
        print("cap_rate_pct: Capitalization Rate - Higher is better (target: >6%)")
        print("cash_on_cash_return_pct: Return on down payment - Higher is better (target: >8%)")
        print("grm: Gross Rent Multiplier - Lower is better (target: <12)")
        print("passes_1pct_rule: Monthly rent >= 1% of purchase price")
        print("investment_score: Overall score 0-4 (4 = best)")
    else:
        print("\n" + "=" * 80)
        print("INVESTMENT ANALYSIS SKIPPED")
        print("=" * 80)
        if df_homes is None or len(df_homes) == 0:
            print("No homes data available")
        if df_rentals is None or len(df_rentals) == 0:
            print("No rentals data available")
        print("Both homes and rentals data are required for investment analysis")

    print("\n" + "=" * 80)
    print("SCRAPING COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()
