import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration flag - set to True to use mock data, False to use real API data
DEFAULT_USE_MOCK_DATA = False  

# API Keys
FMP_API_KEY = os.getenv('FMP_API_KEY')
CMC_API_KEY = os.getenv('CMC_API_KEY')

# Debug settings
DEBUG = False  
