import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import numpy as np

from config import DEFAULT_USE_MOCK_DATA, CMC_API_KEY, DEBUG

class CryptoDataFetcher:
    """
    Class to fetch cryptocurrency data from CoinMarketCap API
    """
    def __init__(self, use_mock_data=None):
        self.api_key = CMC_API_KEY
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
                if DEBUG:
                    print(f"CMC API calls remaining: {self.remaining_calls}")
            elif response.status_code == 200 and 'status' in response.json():
                # Try to get from response body
                status = response.json()['status']
                if 'credit_count' in status:
                    used = status['credit_count']
                    # Free tier typically has 10,000 credits per month
                    remaining = 10000 - used
                    self.remaining_calls = str(remaining)
                    if DEBUG:
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
                'date': date.strftime('%Y-%m-%d'),  # Convert to string format for consistency
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
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
        if self.use_mock_data:
            # Return a predefined list of popular cryptocurrencies
            return [
                {'symbol': 'BTC', 'name': 'Bitcoin'},
                {'symbol': 'ETH', 'name': 'Ethereum'},
                {'symbol': 'BNB', 'name': 'Binance Coin'},
                {'symbol': 'SOL', 'name': 'Solana'},
                {'symbol': 'XRP', 'name': 'XRP'},
                {'symbol': 'ADA', 'name': 'Cardano'},
                {'symbol': 'DOGE', 'name': 'Dogecoin'},
                {'symbol': 'DOT', 'name': 'Polkadot'},
                {'symbol': 'LINK', 'name': 'Chainlink'},
                {'symbol': 'LTC', 'name': 'Litecoin'}
            ]
            
        try:
            url = f"{self.base_url}/cryptocurrency/listings/latest"
            params = {
                'limit': 100,
                'convert': 'USD'
            }
            headers = {
                'X-CMC_PRO_API_KEY': self.api_key
            }
            
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
            
    def get_available_crypto_indexes(self):
        """
        Get a list of available cryptocurrency indexes
        Note: These are composite indexes representing the broader crypto market
        """
        # Use Global Market Cap as the crypto index
        return [
            {'symbol': 'GLOBAL_MCAP', 'name': 'Global Market Cap'}
        ]
        
    def get_crypto_index_data(self, index_symbol, days=30):
        """
        Get historical data for a cryptocurrency index
        """
        if index_symbol == 'GLOBAL_MCAP' and not self.use_mock_data and self.api_key:
            try:
                # Use the Global Metrics endpoint which is available in the Hobbyist plan
                url = 'https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/historical'
                
                # Calculate the start and end dates
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                # Format dates for the API (Global Metrics uses date strings)
                start_str = start_date.strftime('%Y-%m-%d')
                end_str = end_date.strftime('%Y-%m-%d')
                
                # Set up parameters for the API call
                parameters = {
                    'time_start': start_str,
                    'time_end': end_str,
                    'interval': 'daily'  # Daily interval
                }
                
                headers = {
                    'X-CMC_PRO_API_KEY': self.api_key,
                    'Accept': 'application/json'
                }
                
                # Make the API call
                response = requests.get(url, headers=headers, params=parameters)
                
                # Only print debugging info if DEBUG is enabled
                if DEBUG:
                    print(f"Global Market Cap API Response Status Code: {response.status_code}")
                    print(f"Global Market Cap API Request URL: {url}")
                    print(f"Global Market Cap API Request Parameters: {parameters}")
                
                data = response.json()
                
                # Check for API errors
                if 'status' in data and 'error_code' in data['status']:
                    error_code = data['status']['error_code']
                    if error_code != 0:
                        error_message = data['status'].get('error_message', 'Unknown error')
                        print(f"Global Market Cap API Error: {error_message}")
                        if error_code == 1006:
                            print("The Global Market Cap endpoint requires a higher CoinMarketCap plan tier")
                        return self._generate_mock_crypto_index_data(index_symbol, days)
                
                # Process data if valid
                if response.status_code == 200 and 'data' in data and 'quotes' in data['data']:
                    quotes = data['data']['quotes']
                    
                    dates = []
                    opens = []
                    highs = []
                    lows = []
                    closes = []
                    volumes = []
                    
                    for quote in quotes:
                        # Parse the timestamp
                        timestamp = quote['timestamp']
                        date_obj = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')
                        date_str = date_obj.strftime('%Y-%m-%d')
                        
                        # Get the market cap data in USD
                        market_cap = quote['quote']['USD']['total_market_cap']
                        volume = quote['quote']['USD']['total_volume_24h']
                        
                        # For Global Metrics, we don't have OHLC data directly
                        # We'll use market cap as the price and create simulated OHLC values
                        dates.append(date_str)
                        opens.append(market_cap)
                        # Simulate high/low as +/- 1% of market cap for visual effect
                        highs.append(market_cap * 1.01)  
                        lows.append(market_cap * 0.99)
                        closes.append(market_cap)
                        volumes.append(volume)
                    
                    # Create DataFrame
                    df = pd.DataFrame({
                        'date': dates,
                        'open': opens,
                        'high': highs,
                        'low': lows,
                        'close': closes,
                        'volume': volumes
                    })
                    
                    # Sort by date
                    df = df.sort_values('date')
                    
                    print(f"Successfully fetched Global Market Cap data from CoinMarketCap")
                    return df
                else:
                    if DEBUG:
                        print(f"Invalid data format received from Global Market Cap API")
                    return self._generate_mock_crypto_index_data(index_symbol, days)
                    
            except Exception as e:
                if DEBUG:
                    print(f"Error fetching Global Market Cap data: {str(e)}")
                return self._generate_mock_crypto_index_data(index_symbol, days)
        
        # Fall back to mock data if we can't get real data
        print(f"Generating mock data for crypto index {index_symbol}...")
        return self._generate_mock_crypto_index_data(index_symbol, days)
        
    def _generate_mock_crypto_index_data(self, index_symbol, days=30):
        """
        Generate mock data for cryptocurrency indexes
        """
        # Base values for different indexes
        base_values = {
            'GLOBAL_MCAP': 2500000000000,  # $2.5T for Global Market Cap
            'TOTAL': 2500000000000,   # $2.5T for total market cap
            'TOTAL2': 1500000000000,  # $1.5T excluding BTC
            'TOTAL3': 800000000000,   # $800B excluding BTC & ETH
            'DEFI': 100000000000,     # $100B for DeFi
            'NFT': 25000000000,       # $25B for NFT
            'DEX': 50000000000,       # $50B for DEX
            'CEX': 80000000000,       # $80B for CEX tokens
            'PRIVACY': 15000000000    # $15B for privacy coins
        }
        base_value = base_values.get(index_symbol, 50000000000)  # Default to $50B
        
        # Generate dates - ensure we have consistent dates for all symbols
        end_date = datetime(2025, 4, 1)  # Fixed end date
        dates = [end_date - timedelta(days=i) for i in range(days)]
        dates.reverse()
        
        # Convert dates to string format to match crypto data
        date_strings = [date.strftime('%Y-%m-%d') for date in dates]
        
        # Set seed for reproducibility but with some variation between indexes
        seed = hash(index_symbol) % 1000
        np.random.seed(seed)
        
        # Create market trend
        market_trend = np.cumsum(np.random.normal(0.001, 0.01, len(dates)))
        
        # For indexes, use lower volatility than individual cryptos
        volatility = 0.02
        
        # Generate prices
        prices = [base_value]
        for change in market_trend:
            prices.append(prices[-1] * (1 + change))
        prices = prices[1:]  # Remove the first element
        
        # Create OHLC data
        data = []
        for i, date in enumerate(date_strings):
            close = prices[i]
            daily_volatility = volatility * close
            
            # Generate OHLC data
            high = close + abs(np.random.normal(0, daily_volatility))
            low = close - abs(np.random.normal(0, daily_volatility))
            open_price = np.random.uniform(low, high)
            
            # Ensure high is the highest and low is the lowest
            high = max(high, open_price, close)
            low = min(low, open_price, close)
            
            volume = int(np.random.uniform(10000000, 100000000))
            
            data.append({
                'date': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        return pd.DataFrame(data)
