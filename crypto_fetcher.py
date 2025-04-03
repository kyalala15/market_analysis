import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import numpy as np

from config import DEFAULT_USE_MOCK_DATA, CRYPTOCOMPARE_API_KEY, DEBUG

class CryptoDataFetcher:
    """
    Class to fetch cryptocurrency data from CryptoCompare API
    """
    def __init__(self, use_mock_data=None):
        self.api_key = CRYPTOCOMPARE_API_KEY  # CryptoCompare API key
        self.use_mock_data = DEFAULT_USE_MOCK_DATA if use_mock_data is None else use_mock_data
        self.remaining_calls = None  # Will store remaining API calls
        self.base_url = "https://min-api.cryptocompare.com/data"  # Base URL for CryptoCompare API
    
    def get_remaining_calls(self):
        """
        Get the number of remaining API calls for CryptoCompare
        """
        if self.use_mock_data:
            return "∞ (using mock data)"
        
        try:
            # CryptoCompare provides rate limit info in their /stats endpoint
            url = "https://min-api.cryptocompare.com/stats/rate/limit"
            headers = {}
            if self.api_key:
                headers['authorization'] = f"Apikey {self.api_key}"
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Debug the structure of the response
            if DEBUG:
                print(f"CryptoCompare rate limit response: {data}")
                
            # Try to extract rate limit information safely
            if 'Data' in data:
                # Different possible structures based on API key tier
                if 'calls_left' in data['Data']:
                    calls_left = data['Data']['calls_left']
                    # Try to get minute limit first, then hour, then day
                    if isinstance(calls_left, dict):
                        if 'Minute' in calls_left:
                            self.remaining_calls = f"{calls_left['Minute']}/minute"
                        elif 'Hour' in calls_left:
                            self.remaining_calls = f"{calls_left['Hour']}/hour"
                        elif 'Day' in calls_left:
                            self.remaining_calls = f"{calls_left['Day']}/day"
                        else:
                            # Just take the first value if we can't find specific time periods
                            first_key = next(iter(calls_left))
                            self.remaining_calls = f"{calls_left[first_key]}/{first_key.lower()}"
                        return self.remaining_calls
                # Fallback if structure is different
                return "CryptoCompare rate limit available"
            
            return "CryptoCompare rate limit unknown"
        except Exception as e:
            print(f"Error checking CryptoCompare API rate limit: {e}")
            return "CryptoCompare rate limit unknown"
        
    def get_crypto_data(self, symbol, days=30):
        """
        Fetch historical cryptocurrency data for the specified symbol using CryptoCompare API
        """
        if self.use_mock_data:
            return self._generate_mock_crypto_data(symbol, days)
        
        try:
            # CryptoCompare API endpoint for daily OHLC data
            url = f"{self.base_url}/v2/histoday"
            params = {
                'fsym': symbol,  # From Symbol
                'tsym': 'USD',   # To Symbol
                'limit': days,   # Number of days
            }
            
            # Add API key if available
            headers = {}
            if self.api_key:
                headers['authorization'] = f"Apikey {self.api_key}"
            
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if 'Data' not in data or 'Data' not in data['Data']:
                print(f"No historical data found for {symbol}. Using mock data...")
                return self._generate_mock_crypto_data(symbol, days)
            
            # Process the data into a pandas DataFrame
            ohlc_data = data['Data']['Data']
            processed_data = []
            
            for item in ohlc_data:
                # Skip entries with zero values (sometimes occurs at the beginning of the data)
                if item['open'] == 0 or item['close'] == 0:
                    continue
                    
                date_str = datetime.fromtimestamp(item['time']).strftime('%Y-%m-%d')
                
                processed_data.append({
                    'date': date_str,
                    'open': item['open'],
                    'high': item['high'],
                    'low': item['low'],
                    'close': item['close'],
                    'volume': item['volumefrom']
                })
            
            df = pd.DataFrame(processed_data)
            df = df.sort_values('date')  # Ensure data is sorted by date
            
            print(f"Successfully fetched historical data for {symbol} from CryptoCompare")
            return df
            
        except Exception as e:
            print(f"Error fetching historical crypto data for {symbol}: {e}")
            print("Falling back to mock data...")
            return self._generate_mock_crypto_data(symbol, days)
    
    def get_crypto_quote(self, symbol):
        """
        Fetch current cryptocurrency quote data for the specified symbol using CryptoCompare API
        """
        if self.use_mock_data:
            # Use the last row of mock data as the current quote
            mock_data = self._generate_mock_crypto_data(symbol, days=30)
            return mock_data.iloc[-1].to_dict() if not mock_data.empty else {}
        
        try:
            # Fetch current price data from CryptoCompare API
            url = f"{self.base_url}/pricemultifull"
            params = {
                'fsyms': symbol,  # From Symbol
                'tsyms': 'USD'    # To Symbol
            }
            
            # Add API key if available
            headers = {}
            if self.api_key:
                headers['authorization'] = f"Apikey {self.api_key}"
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'RAW' not in data or symbol not in data['RAW'] or 'USD' not in data['RAW'][symbol]:
                print(f"No quote data found for {symbol}. Using mock data...")
                mock_data = self._generate_mock_crypto_data(symbol, days=30)
                return mock_data.iloc[-1].to_dict() if not mock_data.empty else {}
            
            # Get the raw data for the symbol
            quote_data = data['RAW'][symbol]['USD']
            
            # Also get the display data for formatted values
            display_data = data['DISPLAY'][symbol]['USD'] if 'DISPLAY' in data and symbol in data['DISPLAY'] and 'USD' in data['DISPLAY'][symbol] else {}
            
            # Get 24h OHLC data for better accuracy
            ohlc_url = f"{self.base_url}/v2/histohour"
            ohlc_params = {
                'fsym': symbol,
                'tsym': 'USD',
                'limit': 24  # Last 24 hours
            }
            
            ohlc_response = requests.get(ohlc_url, headers=headers, params=ohlc_params)
            ohlc_response.raise_for_status()
            ohlc_data = ohlc_response.json()
            
            # Extract OHLC values if available
            if 'Data' in ohlc_data and 'Data' in ohlc_data['Data'] and len(ohlc_data['Data']['Data']) > 0:
                hourly_data = ohlc_data['Data']['Data']
                # Filter out entries with zero values
                hourly_data = [h for h in hourly_data if h['open'] > 0 and h['close'] > 0]
                
                if hourly_data:
                    open_price = hourly_data[0]['open']
                    high_price = max(h['high'] for h in hourly_data)
                    low_price = min(h['low'] for h in hourly_data)
                    # Use current price from the quote for the most up-to-date close
                    close_price = quote_data['PRICE']
                else:
                    # Fallback if hourly data is empty
                    open_price = quote_data.get('OPEN24HOUR', quote_data['PRICE'] * 0.99)
                    high_price = quote_data.get('HIGH24HOUR', quote_data['PRICE'] * 1.01)
                    low_price = quote_data.get('LOW24HOUR', quote_data['PRICE'] * 0.98)
                    close_price = quote_data['PRICE']
            else:
                # Fallback to quote data
                open_price = quote_data.get('OPEN24HOUR', quote_data['PRICE'] * 0.99)
                high_price = quote_data.get('HIGH24HOUR', quote_data['PRICE'] * 1.01)
                low_price = quote_data.get('LOW24HOUR', quote_data['PRICE'] * 0.98)
                close_price = quote_data['PRICE']
            
            # Calculate percent change
            percent_change = ((close_price - open_price) / open_price) * 100 if open_price > 0 else 0
            
            # Convert to our expected format
            formatted_quote = {
                'symbol': symbol,
                'name': display_data.get('FROMSYMBOL', symbol),
                'price': quote_data['PRICE'],
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': quote_data.get('VOLUME24HOUR', 0),
                'change': percent_change,
                'market_cap': quote_data.get('MKTCAP', 0),
                'circulating_supply': quote_data.get('SUPPLY', 0),
                'total_supply': quote_data.get('SUPPLY', 0)  # CryptoCompare doesn't always provide total supply
            }
            
            return formatted_quote
            
        except Exception as e:
            print(f"Error fetching crypto quote from CryptoCompare: {e}")
            mock_data = self._generate_mock_crypto_data(symbol, days=30)
            return mock_data.iloc[-1].to_dict() if not mock_data.empty else {}
    
    def _generate_mock_crypto_data(self, symbol, days=30):
        """
        Generate mock cryptocurrency data for demonstration purposes
        """
        # Base values for different cryptocurrencies
        base_values = {
            'BTC': 60000,
            'ETH': 3000,
            'BNB': 500,
            'SOL': 150,
            'XRP': 0.5,
            'ADA': 0.6,
            'DOGE': 0.15,
            'DOT': 20,
            'AVAX': 30,
            'SHIB': 0.00005
        }
        base_value = base_values.get(symbol, 100)  # Default to $100 for unknown symbols
        
        # Generate dates - ensure we have consistent dates for all symbols
        end_date = datetime(2025, 4, 1)  # Fixed end date
        dates = [end_date - timedelta(days=i) for i in range(days)]
        dates.reverse()
        
        # Convert dates to string format
        date_strings = [date.strftime('%Y-%m-%d') for date in dates]
        
        # Set seed for reproducibility but with some variation between symbols
        seed = hash(symbol) % 1000
        np.random.seed(seed)
        
        # Create market trend
        market_trend = np.cumsum(np.random.normal(0.001, 0.02, len(dates)))
        
        # Generate prices
        prices = [base_value]
        for change in market_trend:
            prices.append(prices[-1] * (1 + change))
        prices = prices[1:]  # Remove the first element
        
        # Create OHLC data
        data = []
        for i, date in enumerate(date_strings):
            close = prices[i]
            daily_volatility = 0.03 * close
            
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
    
    def _generate_mock_crypto_quote(self, symbol):
        """
        Generate mock cryptocurrency quote data
        """
        mock_data = self._generate_mock_crypto_data(symbol, days=30)
        if mock_data.empty:
            return {}
        
        # Get the last row as the current quote
        last_row = mock_data.iloc[-1]
        
        # Base values for different cryptocurrencies
        market_caps = {
            'BTC': 1000000000000,  # $1T
            'ETH': 350000000000,   # $350B
            'BNB': 80000000000,    # $80B
            'SOL': 50000000000,    # $50B
            'XRP': 25000000000,    # $25B
            'ADA': 20000000000,    # $20B
            'DOGE': 15000000000,   # $15B
            'DOT': 10000000000,    # $10B
            'AVAX': 8000000000,    # $8B
            'SHIB': 5000000000     # $5B
        }
        market_cap = market_caps.get(symbol, 1000000000)  # Default to $1B
        
        # Calculate percent change
        percent_change = ((last_row['close'] - last_row['open']) / last_row['open']) * 100
        
        # Generate mock quote data
        return {
            'symbol': symbol,
            'name': f"{symbol} Mock",
            'price': last_row['close'],
            'open': last_row['open'],
            'high': last_row['high'],
            'low': last_row['low'],
            'close': last_row['close'],
            'volume': last_row['volume'],
            'change': percent_change,
            'market_cap': market_cap,
            'circulating_supply': market_cap / last_row['close'],
            'total_supply': market_cap / last_row['close'] * 1.2,
            'last_updated': datetime.now().isoformat()
        }
    
    # Removed _get_crypto_id method as it's no longer needed with CryptoCompare API
            
    def get_available_cryptos(self):
        """
        Get a list of available cryptocurrency symbols using CryptoCompare API
        """
        # Define a list of popular cryptocurrencies that should always be included
        popular_cryptos = [
            {'symbol': 'BTC', 'name': 'Bitcoin'},
            {'symbol': 'ETH', 'name': 'Ethereum'},
            {'symbol': 'BNB', 'name': 'Binance Coin'},
            {'symbol': 'SOL', 'name': 'Solana'},
            {'symbol': 'XRP', 'name': 'XRP'},
            {'symbol': 'ADA', 'name': 'Cardano'},
            {'symbol': 'DOGE', 'name': 'Dogecoin'},
            {'symbol': 'DOT', 'name': 'Polkadot'},
            {'symbol': 'AVAX', 'name': 'Avalanche'},
            {'symbol': 'SHIB', 'name': 'Shiba Inu'}
        ]
        
        if self.use_mock_data:
            # Return the list of popular cryptocurrencies for mock data
            return popular_cryptos
        
        try:
            # Fetch list of top cryptocurrencies from CryptoCompare API
            url = f"{self.base_url}/top/mktcapfull"
            params = {
                'limit': 100,  # Get top 100 cryptocurrencies
                'tsym': 'USD'  # Quote in USD
            }
            
            # Add API key if available
            headers = {}
            if self.api_key:
                headers['authorization'] = f"Apikey {self.api_key}"
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'Data' not in data or not data['Data']:
                print("No cryptocurrency data found from API. Using popular list...")
                return popular_cryptos
            
            # Process the data into a list of dictionaries
            cryptos = []
            api_symbols = set()  # Keep track of symbols we've added from the API
            
            for crypto in data['Data']:
                coin_info = crypto.get('CoinInfo', {})
                symbol = coin_info.get('Name')  # CryptoCompare uses 'Name' for symbol
                if symbol:
                    cryptos.append({
                        'symbol': symbol,
                        'name': coin_info.get('FullName', symbol)
                    })
                    api_symbols.add(symbol)
            
            # Add any popular cryptocurrencies that weren't in the API response
            for crypto in popular_cryptos:
                if crypto['symbol'] not in api_symbols:
                    cryptos.append(crypto)
                    # Only print this message in debug mode to avoid duplicate messages
                    if DEBUG:
                        print(f"Adding popular crypto not found in API: {crypto['symbol']}")
            
            return cryptos
            
        except Exception as e:
            print(f"Error fetching cryptocurrency list from CryptoCompare: {e}")
            print("Falling back to mock list...")
            # Return mock data if API call fails
            return self.get_available_cryptos()
            
    def get_available_crypto_indexes(self):
        """
        Get a list of available cryptocurrency indexes
        Note: These are composite indexes representing the broader crypto market
        """
        # CryptoCompare indices
        return [
            {'symbol': 'TOTAL', 'name': 'Total Crypto Market Cap'},
            {'symbol': 'CCMVDA', 'name': 'CryptoCompare Market Value Index'},
            {'symbol': 'CCCAGG', 'name': 'CryptoCompare Aggregate Index'}
        ]
        
    def get_crypto_index_data(self, index_symbol, days=30):
        """
        Get historical data for a cryptocurrency index
        """
        if self.use_mock_data:
            return self._generate_mock_crypto_index_data(index_symbol, days)
            
        try:
            # Store original symbol for logging purposes
            original_symbol = index_symbol
            
            # Initialize headers here so it's available for all code paths
            headers = {}
            if self.api_key:
                headers['authorization'] = f"Apikey {self.api_key}"
                
            # For TOTAL, go straight to the alternative approach since it works better
            if index_symbol == 'TOTAL':
                print(f"Using alternative approach for {index_symbol}...")
            else:
                # First try to get data using the direct index API
                print(f"Fetching index data for {index_symbol} from CryptoCompare...")
                url = f"{self.base_url}/index/historical/values"
                params = {
                    'indexName': index_symbol,
                    'limit': days,
                    'aggregate': 1,
                    'currency': 'USD'
                }
                
                response = requests.get(url, headers=headers, params=params)
                
                # Check if we got valid data
                if response.status_code == 200:
                    data = response.json()
                    
                    if DEBUG:
                        print(f"CryptoCompare index response status: {response.status_code}")
                        print(f"CryptoCompare index response data: {data}")
                    
                    # If we get valid data, process it
                    if 'Data' in data and isinstance(data['Data'], list) and len(data['Data']) > 0:
                        processed_data = []
                        for item in data['Data']:
                            # Convert timestamp to date
                            date_str = datetime.fromtimestamp(item['time']).strftime('%Y-%m-%d')
                            value = item['value']
                            
                            # For market cap data, we often only get a single value per day
                            # Create synthetic OHLC with small variations
                            variation = value * 0.01  # 1% variation
                            
                            processed_data.append({
                                'date': date_str,
                                'open': value - variation/2,
                                'high': value + variation,
                                'low': value - variation,
                                'close': value,
                                'volume': 0  # Volume not available for index
                            })
                        
                        df = pd.DataFrame(processed_data)
                        if not df.empty:
                            df = df.sort_values('date')  # Ensure data is sorted by date
                            print(f"Successfully fetched index data for {index_symbol} from CryptoCompare")
                            return df
            
            # If we reach here, we couldn't get the index data directly
            # Try the alternative approach using the top list API
            if index_symbol in ['TOTAL', 'CCCAGG']:
                print(f"Trying alternative approach for {index_symbol}...")
                # For TOTAL market cap, we can use the top list endpoint
                alt_url = f"{self.base_url}/v2/histoday"
                alt_params = {
                    'fsym': 'BTC',  # Use BTC as reference
                    'tsym': 'USD',
                    'limit': days,
                    'toTs': int(datetime.now().timestamp())
                }
                
                alt_response = requests.get(alt_url, headers=headers, params=alt_params)
                if alt_response.status_code == 200:
                    alt_data = alt_response.json()
                    
                    if 'Data' in alt_data and 'Data' in alt_data['Data'] and len(alt_data['Data']['Data']) > 0:
                        # Now get the total market cap data
                        top_url = f"{self.base_url}/top/totalvolfull"
                        top_params = {
                            'limit': 10,
                            'tsym': 'USD'
                        }
                        
                        top_response = requests.get(top_url, headers=headers, params=top_params)
                        if top_response.status_code == 200:
                            top_data = top_response.json()
                            
                            if 'Data' in top_data and len(top_data['Data']) > 0:
                                # Get the total market cap
                                total_mcap = sum(coin['RAW']['USD']['MKTCAP'] for coin in top_data['Data'] if 'RAW' in coin and 'USD' in coin['RAW'] and 'MKTCAP' in coin['RAW']['USD'])
                                
                                # Use BTC price history as a template but scale to total market cap
                                btc_history = alt_data['Data']['Data']
                                processed_data = []
                                
                                for item in btc_history:
                                    if item['time'] == 0 or item['close'] == 0:
                                        continue
                                        
                                    date_str = datetime.fromtimestamp(item['time']).strftime('%Y-%m-%d')
                                    # Scale BTC price to total market cap
                                    scaling_factor = total_mcap / (item['close'] * 10)
                                    
                                    processed_data.append({
                                        'date': date_str,
                                        'open': item['open'] * scaling_factor,
                                        'high': item['high'] * scaling_factor,
                                        'low': item['low'] * scaling_factor,
                                        'close': item['close'] * scaling_factor,
                                        'volume': item['volumefrom'] * scaling_factor
                                    })
                                
                                df = pd.DataFrame(processed_data)
                                if not df.empty:
                                    df = df.sort_values('date')
                                    print(f"Successfully created scaled index data for {index_symbol}")
                                    return df
            
            # Fallback: Use BTC as a proxy for the market
            print(f"Using BTC as a proxy for {original_symbol}...")
            btc_data = self.get_crypto_data('BTC', days)
            
            # Scale the values to be more representative of market cap
            if not btc_data.empty:
                # Multiply by a factor to simulate market cap (BTC is ~40% of total market)
                scaling_factor = 2.5  # Roughly 1/0.4 to estimate total market from BTC
                for col in ['open', 'high', 'low', 'close']:
                    btc_data[col] = btc_data[col] * scaling_factor * 1000000000  # Convert to billions
                
                print(f"Created proxy index data for {original_symbol} based on BTC")
                return btc_data
                
        except Exception as e:
            print(f"Error creating crypto index data: {e}")
        
        # Fall back to mock data if all else fails
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
