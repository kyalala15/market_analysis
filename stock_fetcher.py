import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import time

from config import DEFAULT_USE_MOCK_DATA, FMP_API_KEY, DEBUG

class StockDataFetcher:
    """
    Class to fetch stock data from Financial Modeling Prep API
    """
    def __init__(self, use_mock_data=None):
        self.api_key = FMP_API_KEY
        self.use_mock_data = DEFAULT_USE_MOCK_DATA if use_mock_data is None else use_mock_data
        self.remaining_calls = None  # Will store remaining API calls
    
    def get_remaining_calls(self):
        """
        Get the number of remaining API calls for Financial Modeling Prep
        """
        if self.use_mock_data:
            return "∞ (using mock data)"
        
        try:
            url = f"https://financialmodelingprep.com/api/v3/profile/AAPL?apikey={self.api_key}"
            response = requests.get(url)
            
            # Check headers for rate limit information
            if 'X-Rate-Limit-Remaining' in response.headers:
                self.remaining_calls = response.headers['X-Rate-Limit-Remaining']
                return self.remaining_calls
            else:
                # FMP doesn't consistently provide rate limit headers, so we'll estimate
                # Free tier typically has 250-500 calls per day
                return "Unknown (FMP doesn't provide rate limit info)"
        except Exception as e:
            print(f"Error checking FMP API rate limit: {e}")
            return "Unknown (error checking)"
    
    def get_stock_data(self, symbol, days=30):
        """
        Fetch historical stock data for the specified symbol
        """
        if self.use_mock_data:
            return self._generate_mock_stock_data(symbol, days)
        
        try:
            # Fetch historical data from Financial Modeling Prep API
            url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?timeseries={days}&apikey={self.api_key}"
            response = requests.get(url)
            
            # Check for rate limit headers
            if 'X-Rate-Limit-Remaining' in response.headers:
                self.remaining_calls = response.headers['X-Rate-Limit-Remaining']
                if DEBUG:
                    print(f"FMP API calls remaining: {self.remaining_calls}")
            
            data = response.json()
            
            if 'historical' not in data:
                print(f"No historical data found for {symbol}. Using mock data...")
                return self._generate_mock_stock_data(symbol, days)
            
            # Process the data into a pandas DataFrame
            historical_data = data['historical']
            df = pd.DataFrame(historical_data)
            
            # Rename columns to match our expected format
            df = df.rename(columns={
                'date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
            
            # Convert date strings to datetime objects and then to YYYY-MM-DD string format
            # This ensures consistency with the crypto data format
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            
            # Sort by date (oldest to newest)
            df = df.sort_values('date')
            
            return df
            
        except Exception as e:
            print(f"Error fetching stock data: {e}")
            return self._generate_mock_stock_data(symbol, days)
    
    def get_stock_quote(self, symbol):
        """
        Fetch current stock quote data for the specified symbol
        """
        if self.use_mock_data:
            # Use the last row of mock data as the current quote
            mock_data = self._generate_mock_stock_data(symbol, days=30)
            return mock_data.iloc[-1].to_dict() if not mock_data.empty else {}
        
        try:
            # Fetch quote data from Financial Modeling Prep API
            url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey={self.api_key}"
            response = requests.get(url)
            data = response.json()
            
            if not data or not isinstance(data, list) or len(data) == 0:
                print(f"No quote data found for {symbol}. Using mock data...")
                mock_data = self._generate_mock_stock_data(symbol, days=30)
                return mock_data.iloc[-1].to_dict() if not mock_data.empty else {}
            
            quote_data = data[0]
            
            # Convert to our expected format
            formatted_quote = {
                'symbol': quote_data.get('symbol'),
                'name': quote_data.get('name'),
                'price': quote_data.get('price'),
                'open': quote_data.get('open'),
                'high': quote_data.get('dayHigh'),
                'low': quote_data.get('dayLow'),
                'close': quote_data.get('previousClose'),
                'volume': quote_data.get('volume'),
                'change': quote_data.get('change'),
                'change_percent': quote_data.get('changesPercentage'),
                'market_cap': quote_data.get('marketCap'),
                'pe_ratio': quote_data.get('pe')
            }
            
            return formatted_quote
            
        except Exception as e:
            print(f"Error fetching stock quote: {e}")
            mock_data = self._generate_mock_stock_data(symbol, days=30)
            return mock_data.iloc[-1].to_dict() if not mock_data.empty else {}
    
    def _generate_mock_stock_data(self, symbol, days=30):
        """
        Generate mock stock data for demonstration purposes
        """
        print(f"Generating mock stock data for {symbol}...")
        
        # Set base price based on symbol
        base_prices = {
            # Individual stocks
            'AAPL': 180.0,
            'MSFT': 420.0,
            'AMZN': 185.0,
            'GOOGL': 175.0,
            'META': 485.0,
            'TSLA': 175.0,
            'NVDA': 880.0,
            'JPM': 195.0,
            'JNJ': 150.0,
            'V': 275.0,
            # Index funds
            'SPY': 500.0,  # S&P 500 ETF
            'QQQ': 420.0,  # Nasdaq 100 ETF
            'DIA': 380.0,  # Dow Jones Industrial Average ETF
            'IWM': 200.0,  # Russell 2000 ETF
            'VTI': 240.0   # Vanguard Total Stock Market ETF
        }
        base_price = base_prices.get(symbol, 100.0)  # Default to 100 if symbol not found
        
        # Generate dates - ensure we have consistent dates for all symbols
        # Use a fixed end date to ensure consistency between stock and crypto
        end_date = datetime(2025, 4, 1)  # Fixed end date
        dates = []
        for i in range(days):
            date = end_date - timedelta(days=i)
            # Only include weekdays for stocks
            if date.weekday() < 5:  # 0-4 are Monday to Friday
                dates.append(date)
        dates.reverse()
        
        # Set seed for reproducibility but make it different for each symbol
        seed = 42  # Fixed seed for more consistent results
        np.random.seed(seed)
        
        # Create base market trend that will be shared between stocks and crypto
        # This creates correlation between assets
        market_trend = np.cumsum(np.random.normal(0.001, 0.01, len(dates)))
        
        # Create price trend with some randomness
        volatility = 0.02
        momentum = 0.001 * np.random.randn()
        
        # Combine market trend with symbol-specific trend
        symbol_specific = np.random.normal(momentum, volatility, len(dates))
        combined_changes = 0.7 * market_trend + 0.3 * symbol_specific  # 70% market, 30% specific
        
        # Generate prices
        prices = [base_price]
        for change in combined_changes:
            prices.append(prices[-1] * (1 + change))
        prices = prices[1:]  # Remove the first element
        
        # Create OHLC data
        data = []
        for i, date in enumerate(dates):
            close = prices[i]
            daily_volatility = volatility * close
            
            # Generate OHLC data
            high = close + abs(np.random.normal(0, daily_volatility))
            low = close - abs(np.random.normal(0, daily_volatility))
            open_price = np.random.uniform(low, high)
            
            # Ensure high is the highest and low is the lowest
            high = max(high, open_price, close)
            low = min(low, open_price, close)
            
            volume = int(np.random.uniform(1000000, 10000000))
            
            data.append({
                'date': date.strftime('%Y-%m-%d'),  # Convert to string format for consistency
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def get_available_stocks(self):
        """
        Get a list of available stock symbols
        """
        if self.use_mock_data:
            # Return a predefined list of popular stocks
            return [
                {'symbol': 'AAPL', 'name': 'Apple Inc.'},
                {'symbol': 'MSFT', 'name': 'Microsoft Corporation'},
                {'symbol': 'AMZN', 'name': 'Amazon.com Inc.'},
                {'symbol': 'GOOGL', 'name': 'Alphabet Inc.'},
                {'symbol': 'META', 'name': 'Meta Platforms Inc.'},
                {'symbol': 'TSLA', 'name': 'Tesla Inc.'},
                {'symbol': 'NVDA', 'name': 'NVIDIA Corporation'},
                {'symbol': 'JPM', 'name': 'JPMorgan Chase & Co.'},
                {'symbol': 'JNJ', 'name': 'Johnson & Johnson'},
                {'symbol': 'V', 'name': 'Visa Inc.'},
                # Index funds
                {'symbol': 'SPY', 'name': 'SPDR S&P 500 ETF Trust'},
                {'symbol': 'QQQ', 'name': 'Invesco QQQ Trust'},
                {'symbol': 'DIA', 'name': 'SPDR Dow Jones Industrial Average ETF'},
                {'symbol': 'IWM', 'name': 'iShares Russell 2000 ETF'},
                {'symbol': 'VTI', 'name': 'Vanguard Total Stock Market ETF'}
            ]
        
        try:
            url = f"https://financialmodelingprep.com/api/v3/stock/list?apikey={self.api_key}"
            response = requests.get(url)
            data = response.json()
            
            if data and isinstance(data, list):
                # Filter for common stocks and return symbol and name
                stocks = [{'symbol': item['symbol'], 'name': item['name']} 
                          for item in data if 'symbol' in item and 'name' in item]
                return stocks
            return []
        except Exception as e:
            print(f"Error fetching available stocks: {e}")
            # Return a predefined list of popular stocks as fallback
            return [
                {'symbol': 'AAPL', 'name': 'Apple Inc.'},
                {'symbol': 'MSFT', 'name': 'Microsoft Corporation'},
                {'symbol': 'AMZN', 'name': 'Amazon.com Inc.'},
                {'symbol': 'GOOGL', 'name': 'Alphabet Inc.'},
                {'symbol': 'META', 'name': 'Meta Platforms Inc.'}
            ]
