# Market Analysis Dashboard

A dashboard for analyzing stocks and cryptocurrencies using Dash, Financial Modeling Prep API, CoinMarketCap API, and Plotly.

## Features

- View stock and cryptocurrency data side by side
- Compare price movements with candlestick charts
- Display key metrics (Open, High, Low, Previous Close, 50-Day Average)
- Switch between different stocks and cryptocurrencies

## Setup

1. Set up a virtual environment (recommended):
   ```
   # Create a virtual environment
   python -m venv venv
   
   # Activate the virtual environment
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows:
   venv\Scripts\activate
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up your API keys (optional if using mock data):
   - Get a Financial Modeling Prep API key from [financialmodelingprep.com](https://financialmodelingprep.com/developer/docs/)
   - Get a CoinMarketCap API key from [coinmarketcap.com/api](https://coinmarketcap.com/api/)
   - Add these keys to the `.env` file

4. Run the application:
   ```
   python app.py
   ```

5. Open your browser and navigate to `http://127.0.0.1:8050/`

## Project Structure

- `app.py`: Main application file with Dash layout and callbacks
- `config.py`: Configuration settings and environment variables
- `stock_fetcher.py`: Module for fetching stock data from Financial Modeling Prep API
- `crypto_fetcher.py`: Module for fetching cryptocurrency data from CoinMarketCap API
- `data_processor.py`: Module for processing and analyzing data
- `.env`: Environment variables (API keys)
- `requirements.txt`: Project dependencies

## Data Source

The application can use either real API data or mock data:

- **Real API Data**: Fetches live data from Financial Modeling Prep for stocks and CoinMarketCap for cryptocurrencies
- **Mock Data**: Provides realistic patterns without requiring API keys, useful for development and testing

To switch between real and mock data, modify the `DEFAULT_USE_MOCK_DATA` variable in `config.py`:
- Set to `True` to use mock data (no API keys required)
- Set to `False` to use real API data (requires valid API keys in the `.env` file)

For debugging API calls, you can enable verbose logging by setting `DEBUG = True` in `config.py`.
