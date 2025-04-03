import os
from dotenv import load_dotenv

# Configuration flag - set to True to use mock data, False to use real API data
DEFAULT_USE_MOCK_DATA = True

# Debug settings
DEBUG = False

# Only load environment variables and set API keys when not using mock data
if not DEFAULT_USE_MOCK_DATA:
    # Load environment variables
    load_dotenv()
    
    # API Keys
    FMP_API_KEY = os.getenv('FMP_API_KEY')  # For stock data
    CRYPTOCOMPARE_API_KEY = os.getenv('CRYPTOCOMPARE_API_KEY')  # For crypto data
else:
    # Set API keys to None when using mock data
    FMP_API_KEY = None
    CRYPTOCOMPARE_API_KEY = None
