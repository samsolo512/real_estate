# KSL Real Estate Scraper - Project Specifications

## Project Overview

This project scrapes real estate listings from KSL Homes (Utah's classifieds website) and calculates investment metrics to identify profitable rental property opportunities.

### Key Features
- Scrapes both for-sale homes and rental listings
- Calculates 5 key investment metrics automatically
- Matches rental comps to for-sale properties
- Generates investment scores to identify best deals
- Configurable scraping limits (scrape all or specific quantity)
- Polite rate limiting to respect server resources

## Project Structure

```
ksl_web_scraping/
├── main.py                      # Entry point with CLI arguments
├── ksl_homes_scraper.py        # For-sale property scraper
├── ksl_rentals_scraper.py      # Rental property scraper
├── investment_analyzer.py       # Investment metrics calculator
└── .claude/
    └── specifications.md        # This documentation file
```

## File Descriptions

### main.py
**Purpose**: Command-line interface and orchestration
**Key Functions**:
- Parse command-line arguments for scraping configuration
- Coordinate scraping of homes and rentals
- Generate investment analysis
- Display top investment opportunities (sorted best to worst)

**Default Behavior**:
- `--max-homes`: 20 properties (if not specified)
- `--max-rentals`: 20 properties (if not specified)
- `--top-deals`: Minimum of homes/rentals scraped (if not specified)
- Results are always displayed best deal first (highest investment score → lowest)

**Usage Examples**:
```bash
# Scrape 20 homes and 20 rentals (default behavior)
python main.py

# Scrape specific quantities
python main.py --max-homes 10 --max-rentals 5

# Scrape only homes
python main.py --max-rentals 0

# Scrape only rentals
python main.py --max-homes 0

# Use different locations (custom URLs)
python main.py --homes-url "https://homes.ksl.com/search/lehi/UT" --rentals-url "https://homes.ksl.com/rent/search/ut/lehi"

# Adjust rate limiting
python main.py --min-delay 3.0 --max-delay 7.0

# Change output prefix
python main.py --output-prefix lehi

# Display more deals (default shows min of homes/rentals)
python main.py --top-deals 50
```

### ksl_homes_scraper.py
**Purpose**: Scrape for-sale property listings
**Key Class**: `KSLHomesScraper`
**Data Extraction Method**:
- Search pages: Parses `__NEXT_DATA__` JSON from Next.js
- Detail pages: Extracts `window.ksl.listingData` JavaScript object

**Extracted Fields**:
- Property basics: address, city, state, zip, price, sqft, beds, baths
- Property details: year_built, lot_size_acres, garage, school_district
- Listing metadata: days_on_market, status, MLS number
- Agent info: agent_name, agency_name, seller_type
- Engagement: view_count, favorite_count
- Calculated metrics: price_per_sqft, one_percent_rule_rent, price_per_bedroom, price_per_acre

**Key Methods**:
- `get_listing_urls(max_pages)`: Paginate through search results
- `scrape_property(url)`: Extract data from single listing
- `scrape_all(max_pages, max_properties)`: Main scraping orchestrator
- `save_to_csv(filename)`: Export to CSV

### ksl_rentals_scraper.py
**Purpose**: Scrape rental property listings
**Key Class**: `KSLRentalsScraper`
**Data Extraction Method**:
- Search pages: Parses `__NEXT_DATA__` JSON
- Detail pages: Extracts Schema.org JSON-LD structured data

**Extracted Fields**:
- Location: address, city, state, zip
- Rental specifics: monthly_rent, pets_allowed
- Property basics: sqft, bedrooms, bathrooms
- Calculated metrics: annual_rent, rent_per_sqft

**Important Notes**:
- KSL has a typo in their schema: uses "Accomodation" (one 'm') instead of "Accommodation"
- The scraper handles both spellings for robustness

**Key Methods**:
- `get_rental_urls(max_pages)`: Paginate through rental search results
- `scrape_rental(url)`: Extract data from single rental listing
- `scrape_all(max_pages, max_rentals)`: Main rental scraping orchestrator
- `save_to_csv(filename)`: Export to CSV

### investment_analyzer.py
**Purpose**: Calculate investment metrics by matching rentals to for-sale properties
**Key Functions**:
- `calculate_investment_metrics(for_sale_df, rental_df, ...)`: Main analysis function
- `get_top_deals(analysis_df, top_n)`: Filter and sort best opportunities (highest score first)

**Investment Metrics Calculated**:

1. **Cap Rate (Capitalization Rate)**
   - Formula: `(Annual Rent - Operating Expenses) / Purchase Price × 100`
   - Target: >6% (higher is better)
   - Measures property's return on investment based on income

2. **Cash-on-Cash Return**
   - Formula: `Annual Cash Flow / Down Payment × 100`
   - Target: >8% (higher is better)
   - Measures actual return on cash invested (accounts for financing)
   - Assumptions: 20% down, 7% interest, 30-year loan

3. **Gross Rent Multiplier (GRM)**
   - Formula: `Purchase Price / Annual Rent`
   - Target: <12 (lower is better)
   - How many years of rent to equal purchase price

4. **1% Rule**
   - Formula: `Monthly Rent >= Purchase Price × 0.01`
   - Target: True (property passes the rule)
   - Quick filter: monthly rent should be ≥1% of purchase price

5. **Investment Score**
   - Range: 0-4 (4 is best)
   - Scoring criteria:
     - +1 if Cap Rate >6%
     - +1 if GRM <12
     - +1 if passes 1% rule
     - +1 if Cash-on-Cash Return >8%

**Rental Matching Logic**:
The analyzer matches for-sale properties to similar rentals to estimate potential rental income:
1. **Preferred match**: Same city + same bedrooms + sqft within 15%
2. **Fallback match**: Same city + same bedrooms (average all matches)
3. **No match**: Investment metrics cannot be calculated (returns None)

**Configurable Parameters**:
- `down_payment_pct`: Default 20% (0.20)
- `interest_rate`: Default 7% (0.07)
- `loan_years`: Default 30 years
- `operating_expense_ratio`: Default 40% of rental income (0.40)

## Web Scraping Implementation Details

### Rate Limiting
- Random delays between requests: 2-5 seconds (configurable)
- Prevents server overload
- Reduces risk of IP blocking
- Respectful to website resources

### Data Sources
**For-Sale Listings:**
- Search results: `__NEXT_DATA__` script tag (Next.js server-side props)
- Detail pages: `window.ksl.listingData` JavaScript variable (JSON object)

**Rental Listings:**
- Search results: `__NEXT_DATA__` script tag
- Detail pages: Schema.org JSON-LD structured data (multiple `<script type="application/ld+json">` tags)

### Error Handling
- Gracefully handles missing data (returns None/NaN)
- Continues scraping if individual listing fails
- Prints error messages for debugging
- Never crashes entire scrape due to single failure

## Dependencies

```python
beautifulsoup4  # HTML parsing
pandas         # Data manipulation
requests       # HTTP requests
```

Install with:
```bash
pip install beautifulsoup4 pandas requests
```

## Common Tasks & Examples

### Adding a New Location
```python
# In main.py or custom script
from ksl_homes_scraper import KSLHomesScraper

scraper = KSLHomesScraper(
    "https://homes.ksl.com/search/lehi/UT/single-family-home",
    min_delay=2.0,
    max_delay=5.0
)
df = scraper.scrape_all(max_properties=10)
scraper.save_to_csv('lehi_homes.csv')
```

### Adjusting Investment Criteria
```python
# In investment_analyzer.py or custom script
from investment_analyzer import calculate_investment_metrics

# More conservative assumptions
analysis = calculate_investment_metrics(
    homes_df,
    rentals_df,
    down_payment_pct=0.25,      # 25% down
    interest_rate=0.08,          # 8% interest
    operating_expense_ratio=0.45 # 45% expenses
)
```

### Adding New Data Fields

**For Homes (ksl_homes_scraper.py)**:
1. Find field in `window.ksl.listingData` JSON
2. Add to `property_info` dict in `scrape_property()` method
3. Example: `'hoa_fee': data.get('hoaFee')`

**For Rentals (ksl_rentals_scraper.py)**:
1. Find field in Schema.org JSON-LD data
2. Add to extraction in `_extract_rental_detail_data()` method
3. Add to `rental_info` dict in `scrape_rental()` method
4. Example: `'lease_term': main_entity.get('leaseTerm')`

### Adding New Investment Metrics

In `investment_analyzer.py`:

```python
def calc_new_metric(row):
    """Your metric calculation here"""
    if pd.isna(row['required_field']):
        return None
    # Calculate metric
    return result

# Add to calculate_investment_metrics function:
analysis_df['new_metric'] = analysis_df.apply(calc_new_metric, axis=1)
```

## Future Enhancement Ideas

### High Priority
- [ ] Add caching to avoid re-scraping same properties
- [ ] Support for additional Utah cities (automated)
- [ ] Export to Excel with formatted sheets
- [ ] Add property photos/image URLs

### Medium Priority
- [ ] Email alerts for new high-score properties
- [ ] Historical price tracking (scrape same listing over time)
- [ ] Neighborhood analysis (group by zip code)
- [ ] Add property tax data (public records)

### Advanced Features
- [ ] Machine learning price prediction
- [ ] Appreciation rate estimation
- [ ] Walk score / school rating integration
- [ ] Interactive dashboard (Streamlit/Plotly)
- [ ] Multi-threaded scraping for speed
- [ ] Database storage (SQLite/PostgreSQL)

## Troubleshooting

### No Data Extracted
**Symptoms**: "No data extracted" or empty DataFrames
**Causes**:
- KSL changed their HTML structure
- Network issues / rate limiting
- Invalid search URL

**Solutions**:
1. Check if URL works in browser
2. Verify JSON structure hasn't changed (inspect page source)
3. Increase delays (`--min-delay 5 --max-delay 10`)
4. Check for CAPTCHA or blocking

### Investment Metrics Show None/NaN
**Symptoms**: `cap_rate_pct`, `grm`, etc. are None
**Causes**:
- No matching rental comps found
- Missing required fields (price, bedrooms, sqft)

**Solutions**:
1. Scrape more rentals to increase match probability
2. Adjust matching criteria (increase sqft tolerance in `investment_analyzer.py`)
3. Check if rental data has `monthly_rent` field populated

### Rate Limiting / IP Blocking
**Symptoms**: Lots of "Error extracting data" messages
**Causes**:
- Too many requests too quickly
- Scraping for extended time

**Solutions**:
1. Increase delays: `--min-delay 5 --max-delay 10`
2. Scrape in smaller batches: `--max-homes 10`
3. Wait 30-60 minutes between large scrapes
4. Use VPN or rotate IP addresses (advanced)

## Best Practices

### Scraping Etiquette
- Always use rate limiting (min 2-second delays)
- Don't scrape during peak hours (9am-5pm MST)
- Limit to reasonable quantities for testing
- Only scrape publicly available data
- Respect robots.txt

### Code Maintenance
- Update scraper if KSL changes HTML structure
- Test with small samples (`--max-homes 3`) before full scrapes
- Keep dependencies updated
- Version control your modifications
- Document any customizations

### Data Quality
- Manually verify a few scraped records
- Check for outliers (price_per_sqft >$1000)
- Validate investment metrics make sense
- Cross-reference with actual listings

## Notes for AI Assistants

When working with this codebase:

1. **Adding Features**: Always test with small sample first (`max_properties=3`)
2. **Changing Scrapers**: KSL uses different data sources for different pages - inspect page source first
3. **Investment Metrics**: All metrics handle None/NaN gracefully - don't remove these checks
4. **Rate Limiting**: NEVER remove or reduce delays below 2 seconds
5. **File Structure**: Keep scrapers, analyzers, and main entry point separate
6. **Error Handling**: Always catch exceptions and continue scraping (don't fail entire run)

### Common Modifications
- **New locations**: Change URLs in `main.py` or via CLI args
- **New metrics**: Add to `investment_analyzer.py` following existing pattern
- **New data fields**: Update scraper classes' `scrape_property()`/`scrape_rental()` methods
- **Export formats**: Add new methods to scraper classes (e.g., `save_to_json()`)

### Testing Checklist
When modifying code:
- [ ] Test with `--max-homes 3 --max-rentals 3` first
- [ ] Verify CSV outputs are generated
- [ ] Check investment metrics calculate correctly
- [ ] Ensure no errors in console output
- [ ] Validate data quality (spot check actual listings)

## License & Legal

This scraper is for educational and personal research purposes only. Users are responsible for:
- Complying with KSL.com Terms of Service
- Respecting rate limits and robots.txt
- Not using data for commercial purposes without permission
- Following applicable laws and regulations

Always scrape responsibly and ethically.
