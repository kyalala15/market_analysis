# Market Analysis Dashboard

A dashboard for analyzing stocks and cryptocurrencies using Dash, Financial Modeling Prep API, CoinMarketCap API, and Plotly.

## Features

- View stock and cryptocurrency data side by side
- Compare price movements with candlestick charts
- Display key metrics (Open, High, Low, Previous Close, 50-Day Average)
- Switch between different stocks and cryptocurrencies

## Setup

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Set up your API keys (optional if using mock data):
   - Get a Financial Modeling Prep API key from [financialmodelingprep.com](https://financialmodelingprep.com/developer/docs/)
   - Get a CoinMarketCap API key from [coinmarketcap.com/api](https://coinmarketcap.com/api/)
   - Add these keys to the `.env` file

3. Run the application:
   ```
   python app.py
   ```

4. Open your browser and navigate to `http://127.0.0.1:8050/`

## Project Structure

- `app.py`: Main application file
- `data_fetcher.py`: Module for fetching data from APIs
- `data_processor.py`: Module for processing and analyzing data
- `.env`: Environment variables (API keys)
- `requirements.txt`: Project dependencies

## Data Source

The application uses mock data by default, which provides realistic patterns without requiring API keys. This is useful for development, testing, or demonstration purposes.

To use real API data, modify the `DEFAULT_USE_MOCK_DATA` variable in `data_fetcher.py` to `False` and ensure you have valid API keys in the `.env` file.
