"""
Investment Analysis Module

Combines for-sale and rental data to calculate investment metrics including:
- Cap Rate (Capitalization Rate)
- Cash-on-Cash Return
- Gross Rent Multiplier (GRM)
- 1% Rule validation
- Investment scoring
"""

import pandas as pd
from typing import Dict


def calculate_investment_metrics(
    for_sale_df: pd.DataFrame,
    rental_df: pd.DataFrame,
    down_payment_pct: float = 0.20,
    interest_rate: float = 0.07,
    loan_years: int = 30,
    operating_expense_ratio: float = 0.40
) -> pd.DataFrame:
    """
    Combine for-sale and rental data to calculate investment KPIs.
    Matches properties by address to estimate rental income for purchase properties.

    Args:
        for_sale_df: DataFrame from KSLHomesScraper
        rental_df: DataFrame from KSLRentalsScraper
        down_payment_pct: Down payment percentage (default 20%)
        interest_rate: Annual interest rate (default 7%)
        loan_years: Loan term in years (default 30)
        operating_expense_ratio: Operating expenses as ratio of rental income (default 40%)

    Returns:
        DataFrame with calculated investment metrics
    """
    analysis_df = for_sale_df.copy()

    analysis_df['estimated_monthly_rent'] = None
    analysis_df['rent_data_source'] = None

    for idx, property in analysis_df.iterrows():
        matches = rental_df[
            (rental_df['city'] == property['city']) &
            (rental_df['bedrooms'] == property['bedrooms']) &
            (abs(rental_df['sqft'] - property['sqft']) / property['sqft'] < 0.15)
        ]

        if len(matches) > 0:
            avg_rent = matches['monthly_rent'].mean()
            analysis_df.at[idx, 'estimated_monthly_rent'] = avg_rent
            analysis_df.at[idx, 'rent_data_source'] = f'avg_of_{len(matches)}_similar'
        else:
            city_matches = rental_df[
                (rental_df['city'] == property['city']) &
                (rental_df['bedrooms'] == property['bedrooms'])
            ]
            if len(city_matches) > 0:
                avg_rent = city_matches['monthly_rent'].mean()
                analysis_df.at[idx, 'estimated_monthly_rent'] = avg_rent
                analysis_df.at[idx, 'rent_data_source'] = f'city_avg_{len(city_matches)}_props'

    def calc_cap_rate(row):
        """Cap Rate = (Annual Rental Income - Annual Operating Expenses) / Property Value"""
        if pd.isna(row['estimated_monthly_rent']) or pd.isna(row['price']):
            return None
        annual_income = row['estimated_monthly_rent'] * 12
        operating_expenses = annual_income * operating_expense_ratio
        noi = annual_income - operating_expenses
        return round((noi / row['price']) * 100, 2)

    def calc_grm(row):
        """Gross Rent Multiplier = Property Price / Gross Annual Rent"""
        if pd.isna(row['estimated_monthly_rent']) or pd.isna(row['price']):
            return None
        annual_rent = row['estimated_monthly_rent'] * 12
        return round(row['price'] / annual_rent, 2)

    def calc_cash_on_cash(row):
        """Cash-on-Cash Return = Annual Pre-Tax Cash Flow / Total Cash Invested"""
        if pd.isna(row['estimated_monthly_rent']) or pd.isna(row['price']):
            return None

        down_payment = row['price'] * down_payment_pct
        loan_amount = row['price'] - down_payment

        monthly_rate = interest_rate / 12
        n_payments = loan_years * 12
        monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate)**n_payments) / \
                         ((1 + monthly_rate)**n_payments - 1)

        annual_income = row['estimated_monthly_rent'] * 12
        annual_mortgage = monthly_payment * 12
        operating_expenses = annual_income * operating_expense_ratio

        annual_cash_flow = annual_income - annual_mortgage - operating_expenses

        return round((annual_cash_flow / down_payment) * 100, 2)

    def passes_one_percent_rule(row):
        """1% Rule: Monthly rent should be at least 1% of purchase price"""
        if pd.isna(row['estimated_monthly_rent']) or pd.isna(row['price']):
            return None
        one_percent = row['price'] * 0.01
        return row['estimated_monthly_rent'] >= one_percent

    analysis_df['cap_rate_pct'] = analysis_df.apply(calc_cap_rate, axis=1)
    analysis_df['grm'] = analysis_df.apply(calc_grm, axis=1)
    analysis_df['cash_on_cash_return_pct'] = analysis_df.apply(calc_cash_on_cash, axis=1)
    analysis_df['passes_1pct_rule'] = analysis_df.apply(passes_one_percent_rule, axis=1)

    def investment_score(row):
        """Simple scoring: Good cap rate (>6%), low GRM (<12), passes 1% rule, good CoC (>8%)"""
        score = 0
        if not pd.isna(row['cap_rate_pct']) and row['cap_rate_pct'] > 6:
            score += 1
        if not pd.isna(row['grm']) and row['grm'] < 12:
            score += 1
        if row['passes_1pct_rule'] == True:
            score += 1
        if not pd.isna(row['cash_on_cash_return_pct']) and row['cash_on_cash_return_pct'] > 8:
            score += 1
        return score

    analysis_df['investment_score'] = analysis_df.apply(investment_score, axis=1)

    return analysis_df


def get_top_deals(analysis_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Get the top investment opportunities sorted by investment score.

    Args:
        analysis_df: DataFrame with calculated investment metrics
        top_n: Number of top deals to return (default 10)

    Returns:
        DataFrame with top deals sorted by investment score
    """
    key_cols = [
        'address', 'city', 'price', 'sqft', 'bedrooms', 'bathrooms',
        'estimated_monthly_rent', 'cap_rate_pct', 'cash_on_cash_return_pct',
        'grm', 'passes_1pct_rule', 'investment_score', 'days_on_market', 'url'
    ]

    available_cols = [col for col in key_cols if col in analysis_df.columns]

    return analysis_df.sort_values('investment_score', ascending=False)[available_cols].head(top_n)
