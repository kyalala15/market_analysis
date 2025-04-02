import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta

class DataProcessor:
    """
    Class to process and analyze financial data
    """
    @staticmethod
    def calculate_metrics(df):
        """
        Calculate key metrics from historical price data
        """
        if df.empty:
            return {
                'open': 0,
                'high': 0,
                'low': 0,
                'close': 0,
                'volume': 0,
                'previous_close': 0,
                'fifty_day_avg': 0,
                'two_hundred_day_avg': 0,
                'year_high': 0,
                'year_low': 0
            }
        
        # Get the most recent data point
        latest = df.iloc[-1]
        
        # Calculate previous close (second most recent)
        previous_close = df.iloc[-2]['close'] if len(df) > 1 else 0
        
        # Calculate moving averages
        fifty_day_avg = df['close'].tail(min(50, len(df))).mean()
        two_hundred_day_avg = df['close'].tail(min(200, len(df))).mean()
        
        # Calculate 52-week high and low
        year_data = df.tail(min(252, len(df)))  # Approximately 252 trading days in a year
        year_high = year_data['high'].max()
        year_low = year_data['low'].min()
        
        return {
            'open': latest['open'],
            'high': latest['high'],
            'low': latest['low'],
            'close': latest['close'],
            'volume': latest['volume'],
            'previous_close': previous_close,
            'fifty_day_avg': fifty_day_avg,
            'two_hundred_day_avg': two_hundred_day_avg,
            'year_high': year_high,
            'year_low': year_low
        }
    
    @staticmethod
    def calculate_metrics_from_quote(quote_data):
        """
        Calculate key metrics from quote data
        """
        if not quote_data:
            return {
                'open': 0,
                'high': 0,
                'low': 0,
                'close': 0,
                'volume': 0,
                'previous_close': 0,
                'fifty_day_avg': 0,
                'two_hundred_day_avg': 0,
                'year_high': 0,
                'year_low': 0
            }
        
        # Extract available metrics from quote data
        return {
            'open': quote_data.get('open', 0),
            'high': quote_data.get('high', 0),
            'low': quote_data.get('low', 0),
            'close': quote_data.get('price', 0),  # Current price is the close
            'volume': quote_data.get('volume', 0),
            'previous_close': quote_data.get('close', 0),  # Previous day's close
            'fifty_day_avg': quote_data.get('fifty_day_avg', quote_data.get('price', 0)),  # Use price if not available
            'two_hundred_day_avg': quote_data.get('two_hundred_day_avg', quote_data.get('price', 0)),
            'year_high': quote_data.get('year_high', quote_data.get('high', 0)),
            'year_low': quote_data.get('year_low', quote_data.get('low', 0))
        }
    
    @staticmethod
    def prepare_candlestick_data(df):
        """
        Prepare data for candlestick chart
        """
        if df.empty:
            return []
        
        # Format data for plotly candlestick
        candlestick_data = []
        for _, row in df.iterrows():
            candlestick_data.append({
                'x': row['date'],
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close']
            })
        
        return candlestick_data
    
    @staticmethod
    def get_market_sentiment(symbol, is_crypto=False):
        """
        Get market sentiment using web scraping
        This is a simplified example and would need to be expanded for production use
        """
        if is_crypto:
            # For crypto, we might scrape a site like CoinDesk or CoinTelegraph
            url = f"https://www.coindesk.com/search?s={symbol}"
        else:
            # For stocks, we might scrape a site like MarketWatch or Yahoo Finance
            url = f"https://www.marketwatch.com/investing/stock/{symbol}"
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # This is a placeholder - actual implementation would depend on the website structure
            # and would require more sophisticated analysis
            
            # For demonstration, return a random sentiment
            sentiments = ['Bullish', 'Bearish', 'Neutral']
            return np.random.choice(sentiments)
            
        except Exception as e:
            print(f"Error fetching market sentiment: {e}")
            return "Neutral"
    
    @staticmethod
    def compare_assets(df1, df2):
        """
        Compare two assets and calculate correlation and other metrics
        """
        if df1.empty or df2.empty:
            return {
                'correlation': 0,
                'relative_performance': 0,
                'volatility_ratio': 0
            }
        
        # Ensure both dataframes have the same dates
        common_dates = pd.merge(df1, df2, on='date', how='inner')
        
        if len(common_dates) < 2:
            return {
                'correlation': 0,
                'relative_performance': 0,
                'volatility_ratio': 0
            }
        
        # Calculate daily returns
        returns1 = common_dates['close_x'].pct_change().dropna()
        returns2 = common_dates['close_y'].pct_change().dropna()
        
        # Calculate correlation
        correlation = returns1.corr(returns2)
        
        # Calculate relative performance (asset1 / asset2)
        try:
            first_day_ratio = common_dates.iloc[0]['close_x'] / common_dates.iloc[0]['close_y']
            last_day_ratio = common_dates.iloc[-1]['close_x'] / common_dates.iloc[-1]['close_y']
            relative_performance = (last_day_ratio / first_day_ratio) - 1
        except Exception:
            relative_performance = 0
        
        # Calculate volatility ratio
        try:
            volatility1 = returns1.std()
            volatility2 = returns2.std()
            volatility_ratio = volatility1 / volatility2 if volatility2 != 0 else 0
        except Exception:
            volatility_ratio = 0
        
        return {
            'correlation': round(correlation, 2),
            'relative_performance': round(relative_performance * 100, 2),  # as percentage
            'volatility_ratio': round(volatility_ratio, 2)
        }
    
        
    @staticmethod
    def compare_assets_from_quotes(quote1, quote2):
        """
        Compare two assets using quote data instead of historical data
        """
        if not quote1 or not quote2:
            return {
                'correlation': 0,
                'relative_performance': 0,
                'volatility_ratio': 0
            }
        
        # For correlation, we need historical data, so we'll use a default value or estimate
        correlation = 0.3  # Default low-moderate correlation between stock and crypto
        
        # For relative performance, we can use the daily change percentages
        asset1_change = quote1.get('change_percent', 0) if 'change_percent' in quote1 else 0
        asset2_change = quote2.get('change_percent', 0) if 'change_percent' in quote2 else 0
        relative_performance = asset1_change - asset2_change
        
        # For volatility ratio, we can use the magnitude of daily changes
        asset1_volatility = abs(asset1_change) if asset1_change != 0 else 0.01
        asset2_volatility = abs(asset2_change) if asset2_change != 0 else 0.01
        volatility_ratio = asset1_volatility / asset2_volatility if asset2_volatility != 0 else 1.0
        
        return {
            'correlation': round(correlation, 2),
            'relative_performance': round(relative_performance, 2),  # already as percentage
            'volatility_ratio': round(volatility_ratio, 2)
        }
        
    @staticmethod
    def compare_stock_to_index(stock_df, index_df):
        """
        Compare a stock to an index and calculate alpha, beta, and correlation
        """
        if stock_df.empty or index_df.empty:
            return {
                'correlation': 0,
                'alpha': 0,
                'beta': 0
            }
        
        # Ensure both dataframes have the same dates
        common_dates = pd.merge(stock_df, index_df, on='date', how='inner')
        
        if len(common_dates) < 2:
            return {
                'correlation': 0,
                'alpha': 0,
                'beta': 0
            }
        
        # Calculate daily returns
        stock_returns = common_dates['close_x'].pct_change().dropna()
        index_returns = common_dates['close_y'].pct_change().dropna()
        
        # Calculate correlation
        correlation = stock_returns.corr(index_returns)
        
        # Calculate beta (measure of volatility/systematic risk)
        # Beta = Covariance(stock, index) / Variance(index)
        covariance = stock_returns.cov(index_returns)
        variance = index_returns.var()
        beta = covariance / variance if variance != 0 else 0
        
        # Calculate alpha (excess return)
        # Alpha = Stock Return - (Risk-Free Rate + Beta * (Index Return - Risk-Free Rate))
        # For simplicity, assume risk-free rate is 0
        stock_total_return = (common_dates.iloc[-1]['close_x'] / common_dates.iloc[0]['close_x']) - 1
        index_total_return = (common_dates.iloc[-1]['close_y'] / common_dates.iloc[0]['close_y']) - 1
        alpha = stock_total_return - (beta * index_total_return)
        
        return {
            'correlation': round(correlation, 2),
            'alpha': round(alpha * 100, 2),  # as percentage
            'beta': round(beta, 2)
        }
    
    @staticmethod
    def compare_stock_to_index_from_quotes(stock_quote, index_quote):
        """
        Compare a stock to an index using quote data instead of historical data
        """
        if not stock_quote or not index_quote:
            return {
                'correlation': 0,
                'alpha': 0,
                'beta': 0
            }
        
        # For correlation, we need historical data, so we'll use a default value or estimate
        # In a real application, you might want to store this value or use a more sophisticated method
        correlation = 0.5  # Default moderate correlation
        
        # For beta, we can use the ratio of volatilities as a rough estimate
        # In a real application, you would use historical data for a more accurate beta
        stock_volatility = abs(stock_quote.get('change_percent', 0)) / 100 if 'change_percent' in stock_quote else 0.02
        index_volatility = abs(index_quote.get('change_percent', 0)) / 100 if 'change_percent' in index_quote else 0.01
        beta = stock_volatility / index_volatility if index_volatility != 0 else 1.0
        
        # For alpha, we can use the difference in daily returns
        stock_return = stock_quote.get('change_percent', 0) / 100 if 'change_percent' in stock_quote else 0
        index_return = index_quote.get('change_percent', 0) / 100 if 'change_percent' in index_quote else 0
        alpha = stock_return - (beta * index_return)
        
        return {
            'correlation': round(correlation, 2),
            'alpha': round(alpha * 100, 2),  # as percentage
            'beta': round(beta, 2)
        }
