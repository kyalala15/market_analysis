import os
import requests
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime, timedelta
import time
import numpy as np

# Load environment variables
load_dotenv()

# Configuration flag - set to True to use mock data, False to use real API data
# To use real API data, set this to False and ensure you have valid API keys in your .env file
# To use mock data (no API keys required), set this to True
# Default to using mock data
DEFAULT_USE_MOCK_DATA = True  # Using mock data to avoid API quota issues

class StockDataFetcher:
    """
    Class to fetch stock data from Financial Modeling Prep API
    """
    def __init__(self, use_mock_data=None):
        self.api_key = os.getenv('FMP_API_KEY')
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
                'date': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
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
    
    def get_available_stocks(self):
        """
        Get a list of available stock symbols
        """
        url = f"https://financialmodelingprep.com/api/v3/stock/list?apikey={self.api_key}"
        response = requests.get(url)
        data = response.json()
        
        if data and isinstance(data, list):
            # Filter for common stocks and return symbol and name
            stocks = [{'symbol': item['symbol'], 'name': item['name']} 
                      for item in data if 'symbol' in item and 'name' in item]
            return stocks
        return []


class CryptoDataFetcher:
    """
    Class to fetch cryptocurrency data from CoinMarketCap API
    """
    def __init__(self, use_mock_data=None):
        self.api_key = os.getenv('CMC_API_KEY')
        self.use_mock_data = DEFAULT_USE_MOCK_DATA if use_mock_data is None else use_mock_data
        self.remaining_calls = None  # Will store remaining API calls
        self.base_url = "https://pro-api.coinmarketcap.com/v1"  # Base URL for CoinMarketCap API
    
    def get_remaining_calls(self):
        """
        Get the number of remaining API calls for CoinMarketCap
        """
        if self.use_mock_data:
            return "∞ (using mock data)"
        
        try:
            url = f"{self.base_url}/cryptocurrency/quotes/latest"
            parameters = {
                'symbol': 'BTC',
                'convert': 'USD'
            }
            headers = {
                'Accepts': 'application/json',
                'X-CMC_PRO_API_KEY': self.api_key
            }
            
            response = requests.get(url, headers=headers, params=parameters)
            
            # Check headers for rate limit information
            if 'X-CMC_PRO_API_CALLS_REMAINING' in response.headers:
                self.remaining_calls = response.headers['X-CMC_PRO_API_CALLS_REMAINING']
                return self.remaining_calls
            elif response.status_code == 200 and 'status' in response.json():
                # Try to get from response body
                status = response.json()['status']
                if 'credit_count' in status:
                    used = status['credit_count']
                    # Free tier typically has 10,000 credits per month
                    remaining = 10000 - used
                    self.remaining_calls = str(remaining)
                    return self.remaining_calls
            
            return "Unknown (couldn't retrieve from headers)"
        except Exception as e:
            print(f"Error checking CMC API rate limit: {e}")
            return "Unknown (error checking)"
        
    def get_crypto_data(self, symbol, days=30):
        """
        Fetch historical cryptocurrency data for the specified symbol
        """
        if self.use_mock_data:
            return self._generate_mock_crypto_data(symbol, days)
        
        try:
            # Get the cryptocurrency ID from the symbol
            crypto_id = self._get_crypto_id(symbol)
            if not crypto_id:
                print(f"Could not find ID for symbol {symbol}. Using mock data...")
                return self._generate_mock_crypto_data(symbol, days)
            
            # Calculate time range
            end_time = int(datetime.now().timestamp())
            # CMC Hobbyist plan allows historical data up to 1 month back
            start_time = end_time - (days * 24 * 60 * 60)
            
            # Fetch historical data using the v2 historical quotes endpoint
            url = f"{self.base_url}/cryptocurrency/quotes/historical"
            params = {
                'id': crypto_id,
                'time_start': datetime.fromtimestamp(start_time).strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                'time_end': datetime.fromtimestamp(end_time).strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                'interval': '1d',  # Daily intervals
                'convert': 'USD'
            }
            headers = {
                'X-CMC_PRO_API_KEY': self.api_key
            }
            
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if 'data' not in data or 'quotes' not in data['data']:
                print(f"No historical data found for {symbol}. Using mock data...")
                return self._generate_mock_crypto_data(symbol, days)
            
            # Process the data into a pandas DataFrame
            quotes = data['data']['quotes']
            processed_data = []
            
            for quote in quotes:
                timestamp = quote['timestamp']
                quote_data = quote['quote']['USD']
                
                # Parse the timestamp and convert to date string in YYYY-MM-DD format
                # to match the format used by stock data
                date_obj = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.000Z')
                date_str = date_obj.strftime('%Y-%m-%d')
                
                processed_data.append({
                    'date': date_str,  # Store as string to match stock data format
                    'open': quote_data.get('open', quote_data['price']),
                    'high': quote_data.get('high', quote_data['price']),
                    'low': quote_data.get('low', quote_data['price']),
                    'close': quote_data['price'],
                    'volume': quote_data.get('volume_24h', 0)
                })
            
            df = pd.DataFrame(processed_data)
            df = df.sort_values('date')  # Ensure data is sorted by date
            
            print(f"Successfully fetched historical data for {symbol} from CoinMarketCap")
            return df
            
        except Exception as e:
            print(f"Error fetching historical crypto data for {symbol}: {e}")
            print("Falling back to mock data...")
            return self._generate_mock_crypto_data(symbol, days)
    
    def get_crypto_quote(self, symbol):
        """
        Fetch current cryptocurrency quote data for the specified symbol
        """
        if self.use_mock_data:
            # Use the last row of mock data as the current quote
            mock_data = self._generate_mock_crypto_data(symbol, days=30)
            return mock_data.iloc[-1].to_dict() if not mock_data.empty else {}
        
        try:
            # Fetch quote data from CoinMarketCap API
            url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
            parameters = {
                'symbol': symbol,
                'convert': 'USD'
            }
            headers = {
                'Accepts': 'application/json',
                'X-CMC_PRO_API_KEY': self.api_key
            }
            
            response = requests.get(url, headers=headers, params=parameters)
            
            # Check for rate limit headers
            if 'X-CMC_PRO_API_CALLS_REMAINING' in response.headers:
                self.remaining_calls = response.headers['X-CMC_PRO_API_CALLS_REMAINING']
                print(f"CMC API calls remaining: {self.remaining_calls}")
            elif response.status_code == 200 and 'status' in response.json():
                # Try to get from response body
                status = response.json()['status']
                if 'credit_count' in status:
                    used = status['credit_count']
                    # Free tier typically has 10,000 credits per month
                    remaining = 10000 - used
                    self.remaining_calls = str(remaining)
                    print(f"CMC API credits remaining (estimate): {self.remaining_calls}")
            
            data = response.json()
            
            if 'data' not in data or symbol not in data['data']:
                print(f"No quote data found for {symbol}. Using mock data...")
                mock_data = self._generate_mock_crypto_data(symbol, days=30)
                return mock_data.iloc[-1].to_dict() if not mock_data.empty else {}
            
            quote_data = data['data'][symbol]
            usd_quote = quote_data['quote']['USD']
            
            # Convert to our expected format
            formatted_quote = {
                'symbol': quote_data.get('symbol'),
                'name': quote_data.get('name'),
                'price': usd_quote.get('price'),
                'open': usd_quote.get('price') / (1 + usd_quote.get('percent_change_24h', 0) / 100),  # Estimate open price
                'high': usd_quote.get('price') * 1.05,  # Estimate high (5% above current)
                'low': usd_quote.get('price') * 0.95,   # Estimate low (5% below current)
                'close': usd_quote.get('price'),
                'volume': usd_quote.get('volume_24h'),
                'change': usd_quote.get('percent_change_24h'),
                'market_cap': usd_quote.get('market_cap'),
                'circulating_supply': quote_data.get('circulating_supply'),
                'total_supply': quote_data.get('total_supply')
            }
            
            return formatted_quote
            
        except Exception as e:
            print(f"Error fetching crypto quote: {e}")
            mock_data = self._generate_mock_crypto_data(symbol, days=30)
            return mock_data.iloc[-1].to_dict() if not mock_data.empty else {}
    
    def _generate_mock_crypto_data(self, symbol, days=30):
        """
        Generate mock cryptocurrency data for demonstration purposes
        """
        print(f"Generating mock crypto data for {symbol}...")
        
        # Set base price based on symbol
        base_prices = {
            'BTC': 68000.0,
            'ETH': 3500.0,
            'BNB': 600.0,
            'SOL': 150.0,
            'XRP': 0.50,
            'ADA': 0.45,
            'DOGE': 0.15,
            'DOT': 7.0,
            'LINK': 15.0,
            'LTC': 80.0
        }
        base_price = base_prices.get(symbol, 100.0)  # Default to 100 if symbol not found
        
        # Generate dates - ensure we have consistent dates for all symbols
        # Use a fixed end date to ensure consistency between stock and crypto
        end_date = datetime(2025, 4, 1)  # Fixed end date - same as stocks
        dates = [end_date - timedelta(days=i) for i in range(days)]
        dates.reverse()
        
        # Set seed for reproducibility
        seed = 42  # Fixed seed for more consistent results - same as stocks
        np.random.seed(seed)
        
        # Create base market trend that will be shared between stocks and crypto
        # This creates correlation between assets
        market_trend = np.cumsum(np.random.normal(0.001, 0.01, len(dates)))
        
        # Crypto is more volatile than stocks
        volatility = 0.04
        momentum = 0.002 * np.random.randn()
        
        # Combine market trend with symbol-specific trend
        symbol_specific = np.random.normal(momentum, volatility, len(dates))
        combined_changes = 0.6 * market_trend + 0.4 * symbol_specific  # 60% market, 40% specific (more volatile)
        
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
            
            # Generate OHLC data with higher volatility for crypto
            high = close + abs(np.random.normal(0, daily_volatility * 1.5))
            low = close - abs(np.random.normal(0, daily_volatility * 1.5))
            open_price = np.random.uniform(low, high)
            
            # Ensure high is the highest and low is the lowest
            high = max(high, open_price, close)
            low = min(low, open_price, close)
            
            volume = int(np.random.uniform(5000000, 50000000))
            
            data.append({
                'date': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def get_crypto_quote(self, symbol):
        """
        Fetch current quote for the specified cryptocurrency symbol
        """
        if self.use_mock_data:
            return self._generate_mock_crypto_quote(symbol)
        
        url = f"{self.base_url}/cryptocurrency/quotes/latest"
        params = {
            'symbol': symbol,
            'convert': 'USD'
        }
        headers = {
            'X-CMC_PRO_API_KEY': self.api_key
        }
        
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if 'data' in data and symbol in data['data']:
                crypto_data = data['data'][symbol]
                quote = crypto_data['quote']['USD']
                
                return {
                    'symbol': symbol,
                    'name': crypto_data['name'],
                    'price': quote['price'],
                    'volume_24h': quote['volume_24h'],
                    'percent_change_24h': quote['percent_change_24h'],
                    'market_cap': quote['market_cap'],
                    'last_updated': quote['last_updated']
                }
            return {}
        except Exception as e:
            print(f"Error fetching crypto quote for {symbol}: {e}")
            print("Falling back to mock data...")
            return self._generate_mock_crypto_quote(symbol)
    
    def _generate_mock_crypto_quote(self, symbol):
        """
        Generate mock cryptocurrency quote data
        """
        # Base prices for common cryptocurrencies
        base_prices = {
            'BTC': 68000.0,
            'ETH': 3500.0,
            'BNB': 600.0,
            'SOL': 150.0,
            'XRP': 0.50,
            'ADA': 0.45,
            'DOGE': 0.15,
            'DOT': 7.0,
            'LINK': 15.0,
            'LTC': 80.0
        }
        price = base_prices.get(symbol, 100.0)  # Default to 100 if symbol not found
        
        # Names for common cryptocurrencies
        names = {
            'BTC': 'Bitcoin',
            'ETH': 'Ethereum',
            'BNB': 'Binance Coin',
            'SOL': 'Solana',
            'XRP': 'XRP',
            'ADA': 'Cardano',
            'DOGE': 'Dogecoin',
            'DOT': 'Polkadot',
            'LINK': 'Chainlink',
            'LTC': 'Litecoin'
        }
        name = names.get(symbol, symbol)
        
        # Add some randomness to the price
        np.random.seed(int(time.time()) % 1000)  # Different seed each time
        price_variation = np.random.uniform(-0.05, 0.05)  # ±5%
        price = price * (1 + price_variation)
        
        # Generate other metrics
        volume_24h = np.random.uniform(1000000, 5000000000)  # $1M to $5B
        percent_change_24h = np.random.uniform(-10, 10)  # -10% to +10%
        market_cap = price * np.random.uniform(10000000, 1000000000)  # Based on price
        
        return {
            'symbol': symbol,
            'name': name,
            'price': price,
            'volume_24h': volume_24h,
            'percent_change_24h': percent_change_24h,
            'market_cap': market_cap,
            'last_updated': datetime.now().isoformat()
        }
    
    def _get_crypto_id(self, symbol):
        """
        Get the CoinMarketCap ID for a cryptocurrency symbol
        """
        try:
            # Use the cryptocurrency/map endpoint to get the ID
            url = f"{self.base_url}/cryptocurrency/map"
            params = {
                'symbol': symbol
            }
            headers = {
                'X-CMC_PRO_API_KEY': self.api_key
            }
            
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if 'data' in data and len(data['data']) > 0:
                # Return the ID of the first matching cryptocurrency
                return data['data'][0]['id']
            return None
        except Exception as e:
            print(f"Error getting crypto ID for {symbol}: {e}")
            return None
    
    def get_available_cryptos(self):
        """
        Get a list of available cryptocurrency symbols
        """
        url = f"{self.base_url}/cryptocurrency/listings/latest"
        params = {
            'limit': 100,
            'convert': 'USD'
        }
        headers = {
            'X-CMC_PRO_API_KEY': self.api_key
        }
        
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if 'data' in data:
                cryptos = [{'symbol': item['symbol'], 'name': item['name']} 
                           for item in data['data']]
                return cryptos
            return []
        except Exception as e:
            print(f"Error fetching crypto list: {e}")
            return []
