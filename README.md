# KSL Real Estate Scraper

A Python-based web scraper for KSL Homes listings that extracts property data and calculates investment metrics to identify profitable rental property opportunities.

## Features

- Scrapes both for-sale homes and rental listings from KSL.com
- Calculates 5 key investment metrics (Cap Rate, Cash-on-Cash Return, GRM, 1% Rule, Investment Score)
- Matches rental comps to for-sale properties automatically
- **Configurable scraping limits**: Scrape all properties or specify exact quantities
- Polite rate limiting to respect server resources
- Exports to CSV for further analysis

## Installation

```bash
pip install beautifulsoup4 pandas requests
```

## Quick Start

```bash
# Scrape 20 homes and 20 rentals (default behavior)
python main.py

# Scrape specific quantities
python main.py --max-homes 10 --max-rentals 5

# Quick test with small sample
python main.py --max-homes 2 --max-rentals 2

# Scrape only homes
python main.py --max-rentals 0

# Scrape only rentals
python main.py --max-homes 0
```

## Usage Options

```bash
python main.py [OPTIONS]

Options:
  --max-homes N          Maximum number of homes to scrape (default: 20)
  --max-rentals N        Maximum number of rentals to scrape (default: 20)
  --homes-url URL        Custom URL for homes search
  --rentals-url URL      Custom URL for rentals search
  --min-delay SECONDS    Minimum delay between requests (default: 2.0)
  --max-delay SECONDS    Maximum delay between requests (default: 5.0)
  --output-prefix NAME   Prefix for output CSV files (default: herriman)
  --top-deals N          Number of top deals to display (default: min of homes/rentals)
```

## Examples

### Different Location
```bash
python main.py \
  --homes-url "https://homes.ksl.com/search/lehi/UT" \
  --rentals-url "https://homes.ksl.com/rent/search/ut/lehi" \
  --output-prefix lehi
```

### More Conservative Rate Limiting
```bash
python main.py --min-delay 5.0 --max-delay 10.0
```

### Quick Sample for Testing
```bash
python main.py --max-homes 3 --max-rentals 3
```

## Output Files

The script generates three CSV files:

1. **`{prefix}_homes.csv`** - All scraped for-sale properties
2. **`{prefix}_rentals.csv`** - All scraped rental properties
3. **`{prefix}_investment_analysis.csv`** - Combined data with investment metrics

## Investment Metrics

- **Cap Rate**: Capitalization Rate (target: >6%)
- **Cash-on-Cash Return**: Return on down payment (target: >8%)
- **GRM**: Gross Rent Multiplier (target: <12)
- **1% Rule**: Monthly rent ≥ 1% of purchase price
- **Investment Score**: Overall score 0-4 (4 = best opportunity)

## Project Structure

```
ksl_web_scraping/
├── main.py                      # Entry point with CLI
├── ksl_homes_scraper.py        # For-sale property scraper
├── ksl_rentals_scraper.py      # Rental property scraper
├── investment_analyzer.py       # Investment metrics calculator
├── .claude/
│   └── specifications.md        # Detailed documentation
└── README.md                    # This file
```

## Documentation

For detailed documentation, see [.claude/specifications.md](.claude/specifications.md) which includes:
- Architecture details
- How to add new features
- Troubleshooting guide
- Future enhancement ideas
- Best practices

## Legal Notice

This scraper is for educational and personal research purposes only. Users are responsible for complying with KSL.com Terms of Service and applicable laws. Always scrape responsibly and ethically.
