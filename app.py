import dash
from dash import dcc, html, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import os
from dotenv import load_dotenv
from datetime import datetime

from data_fetcher import StockDataFetcher, CryptoDataFetcher, DEFAULT_USE_MOCK_DATA
from data_processor import DataProcessor

# Load environment variables
load_dotenv()

# Set to use mock data by default
USE_MOCK_DATA = DEFAULT_USE_MOCK_DATA

# Initialize data fetchers
stock_fetcher = StockDataFetcher(use_mock_data=USE_MOCK_DATA)
crypto_fetcher = CryptoDataFetcher(use_mock_data=USE_MOCK_DATA)

# Initialize app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Market Analytics"

# Check initial API call limits
fmp_calls_remaining = "Unknown" if USE_MOCK_DATA else stock_fetcher.get_remaining_calls()
cmc_calls_remaining = "Unknown" if USE_MOCK_DATA else crypto_fetcher.get_remaining_calls()
print(f"Initial FMP API calls remaining: {fmp_calls_remaining}")
print(f"Initial CMC API calls remaining: {cmc_calls_remaining}")

# Define default symbols
DEFAULT_STOCK = "AAPL"
DEFAULT_CRYPTO = "BTC"
DEFAULT_INDEX = "SPY"

# Cache for data
STOCK_DATA = {}
CRYPTO_DATA = {}
INDEX_DATA = {}

# Cache for dropdown options
STOCK_LIST = []
CRYPTO_LIST = []
INDEX_LIST = []

# Cache for stock and crypto data (to avoid repeated API calls)
STOCK_DATA = {}
CRYPTO_DATA = {}

# Layout
app.layout = html.Div([
    html.H1("Market Analytics", className="text-center my-4"),
    
    # Refresh button
    dbc.Row([
        dbc.Col([
            dbc.Button(
                "Refresh Data", 
                id="refresh-button", 
                color="primary", 
                className="mb-3",
                n_clicks=0
            ),
            html.Span(id="refresh-status", className="ml-2")
        ], width={"size": 6, "offset": 3}, className="text-center")
    ]),
    
    # No API call counters in the UI - only print to console
    
    # Tabs for different views
    dbc.Tabs(
        [
            dbc.Tab(label="Comparison", tab_id="comparison"),
            dbc.Tab(label="Stocks", tab_id="stocks"),
            dbc.Tab(label="Crypto", tab_id="crypto"),
        ],
        id="tabs",
        active_tab="comparison",
        className="mb-3"
    ),
    
    # Main content - Tab-specific content
    html.Div([
        # Comparison Tab Content
        html.Div(id="comparison-tab-content", children=[

        dbc.Row([
            # Stock section
            dbc.Col([
                html.H3("Stock", className="mt-4"),
                dcc.Dropdown(
                    id="stock-dropdown",
                    options=[],
                    value=DEFAULT_STOCK,
                    clearable=False,
                    className="mb-3"
                ),
                html.Div(id="stock-price-display", className="mb-2"),
                dcc.Graph(id="stock-chart"),
                
                # Stock metrics table
                html.Div([
                    dbc.Table([
                        html.Thead([
                            html.Tr([
                                html.Th("Open"),
                                html.Th("$0"),
                            ], id="stock-open-row")
                        ]),
                        html.Tbody([
                            html.Tr([
                                html.Td("Day High"),
                                html.Td("$0"),
                            ], id="stock-high-row"),
                            html.Tr([
                                html.Td("Day Low"),
                                html.Td("$0"),
                            ], id="stock-low-row"),
                            html.Tr([
                                html.Td("Previous Close"),
                                html.Td("$0"),
                            ], id="stock-prev-close-row"),
                            html.Tr([
                                html.Td("Fifty Day Avg"),
                                html.Td("$0"),
                            ], id="stock-fifty-day-row"),
                        ])
                    ], bordered=True, hover=True, responsive=True, className="mt-3")
                ])
            ], width=6),
            
            # Crypto section
            dbc.Col([
                html.H3("Crypto", className="mt-4"),
                dcc.Dropdown(
                    id="crypto-dropdown",
                    options=[],
                    value=DEFAULT_CRYPTO,
                    clearable=False,
                    className="mb-3"
                ),
                html.Div(id="crypto-price-display", className="mb-2"),
                dcc.Graph(id="crypto-chart"),
                
                # Crypto metrics table
                html.Div([
                    dbc.Table([
                        html.Thead([
                            html.Tr([
                                html.Th("Open"),
                                html.Th("$0"),
                            ], id="crypto-open-row")
                        ]),
                        html.Tbody([
                            html.Tr([
                                html.Td("Day High"),
                                html.Td("$0"),
                            ], id="crypto-high-row"),
                            html.Tr([
                                html.Td("Day Low"),
                                html.Td("$0"),
                            ], id="crypto-low-row"),
                            html.Tr([
                                html.Td("Previous Close"),
                                html.Td("$0"),
                            ], id="crypto-prev-close-row"),
                            html.Tr([
                                html.Td("Fifty Day Avg"),
                                html.Td("$0"),
                            ], id="crypto-fifty-day-row"),
                        ])
                    ], bordered=True, hover=True, responsive=True, className="mt-3")
                ])
            ], width=6),
        ]),
        
        # Comparison metrics (only shown in comparison tab)
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.H3("Comparison Metrics", className="mt-4"),
                    dbc.Card([
                        dbc.CardHeader(html.H5("Correlation", className="card-title")),
                        dbc.CardBody([
                            html.Div([
                                html.P("0.00", id="correlation-value", className="card-text mb-0"),
                                dbc.Button("What does this mean?", id="correlation-info-button", color="link", className="p-0 mt-2"),
                                dbc.Collapse(
                                    dbc.Card(
                                        dbc.CardBody(
                                            "Measures how the daily returns of the two assets move together. Values range from -1.0 to 1.0. A value of 1.0 indicates perfect positive correlation (assets move in the same direction), 0.0 indicates no correlation (assets move independently), and -1.0 indicates perfect negative correlation (assets move in opposite directions)."
                                        ),
                                        className="mt-2"
                                    ),
                                    id="correlation-info-collapse",
                                    is_open=False,
                                ),
                            ])
                        ])
                    ], className="mb-3"),
                    dbc.Card([
                        dbc.CardHeader(html.H5("Relative Performance", className="card-title")),
                        dbc.CardBody([
                            html.Div([
                                html.P("0.00%", id="rel-performance-value", className="card-text mb-0"),
                                dbc.Button("What does this mean?", id="rel-performance-info-button", color="link", className="p-0 mt-2"),
                                dbc.Collapse(
                                    dbc.Card(
                                        dbc.CardBody(
                                            "Measures how one asset has performed relative to the other over the time period. A positive value indicates the stock has outperformed the cryptocurrency, while a negative value indicates the cryptocurrency has outperformed the stock."
                                        ),
                                        className="mt-2"
                                    ),
                                    id="rel-performance-info-collapse",
                                    is_open=False,
                                ),
                            ])
                        ])
                    ], className="mb-3"),
                    dbc.Card([
                        dbc.CardHeader(html.H5("Volatility Ratio", className="card-title")),
                        dbc.CardBody([
                            html.Div([
                                html.P("0.00", id="volatility-ratio-value", className="card-text mb-0"),
                                dbc.Button("What does this mean?", id="volatility-ratio-info-button", color="link", className="p-0 mt-2"),
                                dbc.Collapse(
                                    dbc.Card(
                                        dbc.CardBody(
                                            "Ratio of the standard deviation of daily returns. Measures how much more or less volatile one asset is compared to the other. A value greater than 1.0 indicates the stock is more volatile than the cryptocurrency, while a value less than 1.0 indicates the cryptocurrency is more volatile than the stock."
                                        ),
                                        className="mt-2"
                                    ),
                                    id="volatility-ratio-info-collapse",
                                    is_open=False,
                                ),
                            ])
                        ])
                    ]),
                ], width=12)
            ])
        ], id="comparison-metrics"),
        
        # Stocks comparison (only shown in stocks tab)
        html.Div([
            dbc.Row([
                # Stock selection
                dbc.Col([
                    html.H3("Select Stock", className="mt-4"),
                    dcc.Dropdown(
                        id="stock-comparison-dropdown",
                        options=[],
                        value=DEFAULT_STOCK,
                        clearable=False,
                        className="mb-3"
                    ),
                    dcc.Graph(id="stock-index-chart"),
                ], width=6),
                
                # Index selection
                dbc.Col([
                    html.H3("Select Index", className="mt-4"),
                    dcc.Dropdown(
                        id="index-dropdown",
                        options=[],
                        value=DEFAULT_INDEX,
                        clearable=False,
                        className="mb-3"
                    ),
                    dcc.Graph(id="index-chart"),
                ], width=6),
            ]),
            
            # Stock-Index comparison metrics
            dbc.Row([
                dbc.Col([
                    html.H3("Stock vs Index Metrics", className="mt-4"),
                    dbc.Card([
                        dbc.CardHeader(html.H5("Correlation", className="card-title")),
                        dbc.CardBody([
                            html.Div([
                                html.P("0.00", id="stock-index-correlation-value", className="card-text mb-0"),
                                dbc.Button("What does this mean?", id="stock-index-correlation-info-button", color="link", className="p-0 mt-2"),
                                dbc.Collapse(
                                    dbc.Card(
                                        dbc.CardBody(
                                            "Measures how the daily returns of the stock and index move together. Values range from -1.0 to 1.0. A value of 1.0 indicates perfect positive correlation (assets move in the same direction), 0.0 indicates no correlation (assets move independently), and -1.0 indicates perfect negative correlation (assets move in opposite directions)."
                                        ),
                                        className="mt-2"
                                    ),
                                    id="stock-index-correlation-info-collapse",
                                    is_open=False,
                                ),
                            ])
                        ])
                    ], className="mb-3"),
                    dbc.Card([
                        dbc.CardHeader(html.H5("Alpha", className="card-title")),
                        dbc.CardBody([
                            html.Div([
                                html.P("0.00%", id="alpha-value", className="card-text mb-0"),
                                dbc.Button("What does this mean?", id="alpha-info-button", color="link", className="p-0 mt-2"),
                                dbc.Collapse(
                                    dbc.Card(
                                        dbc.CardBody(
                                            "Alpha measures the excess return of the stock compared to the index. A positive alpha indicates the stock has outperformed the index, while a negative alpha indicates the stock has underperformed the index."
                                        ),
                                        className="mt-2"
                                    ),
                                    id="alpha-info-collapse",
                                    is_open=False,
                                ),
                            ])
                        ])
                    ], className="mb-3"),
                    dbc.Card([
                        dbc.CardHeader(html.H5("Beta", className="card-title")),
                        dbc.CardBody([
                            html.Div([
                                html.P("0.00", id="beta-value", className="card-text mb-0"),
                                dbc.Button("What does this mean?", id="beta-info-button", color="link", className="p-0 mt-2"),
                                dbc.Collapse(
                                    dbc.Card(
                                        dbc.CardBody(
                                            "Beta measures the volatility of a stock compared to the index. A beta of 1.0 means the stock moves with the market. A beta greater than 1.0 indicates the stock is more volatile than the market, while a beta less than 1.0 indicates the stock is less volatile than the market."
                                        ),
                                        className="mt-2"
                                    ),
                                    id="beta-info-collapse",
                                    is_open=False,
                                ),
                            ])
                        ])
                    ]),
                ], width=12)
            ])
        ], id="stocks-comparison-metrics", style={"display": "none"}),
        
        ], style={"display": "block"}),
        
        # Stocks Tab Content
        html.Div(id="stocks-tab-content", children=[
            # Stocks comparison
            html.Div([
                dbc.Row([
                    # Stock selection
                    dbc.Col([
                        html.H3("Stock", className="mt-4"),
                        dcc.Dropdown(
                            id="stock-comparison-dropdown",
                            options=[],
                            value=DEFAULT_STOCK,
                            clearable=False,
                            className="mb-3"
                        ),
                        html.Div(id="stock-index-price-display", className="mb-2"),
                        dcc.Graph(id="stock-index-chart"),
                        
                        # Stock metrics table
                        html.Div([
                            dbc.Table([
                                html.Thead([
                                    html.Tr([
                                        html.Th("Open"),
                                        html.Th("$0"),
                                    ], id="stock-index-open-row")
                                ]),
                                html.Tbody([
                                    html.Tr([
                                        html.Td("Day High"),
                                        html.Td("$0"),
                                    ], id="stock-index-high-row"),
                                    html.Tr([
                                        html.Td("Day Low"),
                                        html.Td("$0"),
                                    ], id="stock-index-low-row"),
                                    html.Tr([
                                        html.Td("Previous Close"),
                                        html.Td("$0"),
                                    ], id="stock-index-prev-close-row"),
                                    html.Tr([
                                        html.Td("Fifty Day Avg"),
                                        html.Td("$0"),
                                    ], id="stock-index-fifty-day-row"),
                                ])
                            ], bordered=True, hover=True, responsive=True, className="mt-3")
                        ])
                    ], width=6),
                    
                    # Index selection
                    dbc.Col([
                        html.H3("Index", className="mt-4"),
                        dcc.Dropdown(
                            id="index-dropdown",
                            options=[],
                            value=DEFAULT_INDEX,
                            clearable=False,
                            className="mb-3"
                        ),
                        html.Div(id="index-price-display", className="mb-2"),
                        dcc.Graph(id="index-chart"),
                        
                        # Index metrics table
                        html.Div([
                            dbc.Table([
                                html.Thead([
                                    html.Tr([
                                        html.Th("Open"),
                                        html.Th("$0"),
                                    ], id="index-open-row")
                                ]),
                                html.Tbody([
                                    html.Tr([
                                        html.Td("Day High"),
                                        html.Td("$0"),
                                    ], id="index-high-row"),
                                    html.Tr([
                                        html.Td("Day Low"),
                                        html.Td("$0"),
                                    ], id="index-low-row"),
                                    html.Tr([
                                        html.Td("Previous Close"),
                                        html.Td("$0"),
                                    ], id="index-prev-close-row"),
                                    html.Tr([
                                        html.Td("Fifty Day Avg"),
                                        html.Td("$0"),
                                    ], id="index-fifty-day-row"),
                                ])
                            ], bordered=True, hover=True, responsive=True, className="mt-3")
                        ])
                    ], width=6),
                ]),
                
                # Stock-Index comparison metrics
                dbc.Row([
                    dbc.Col([
                        html.H3("Stock vs Index Metrics", className="mt-4"),
                        dbc.Card([
                            dbc.CardHeader(html.H5("Correlation", className="card-title")),
                            dbc.CardBody([
                                html.Div([
                                    html.P("0.00", id="stock-index-correlation-value", className="card-text mb-0"),
                                    dbc.Button("What does this mean?", id="stock-index-correlation-info-button", color="link", className="p-0 mt-2"),
                                    dbc.Collapse(
                                        dbc.Card(
                                            dbc.CardBody(
                                                "Measures how the daily returns of the stock and index move together. Values range from -1.0 to 1.0. A value of 1.0 indicates perfect positive correlation (assets move in the same direction), 0.0 indicates no correlation (assets move independently), and -1.0 indicates perfect negative correlation (assets move in opposite directions)."
                                            ),
                                            className="mt-2"
                                        ),
                                        id="stock-index-correlation-info-collapse",
                                        is_open=False,
                                    ),
                                ])
                            ])
                        ], className="mb-3"),
                        dbc.Card([
                            dbc.CardHeader(html.H5("Alpha", className="card-title")),
                            dbc.CardBody([
                                html.Div([
                                    html.P("0.00%", id="alpha-value", className="card-text mb-0"),
                                    dbc.Button("What does this mean?", id="alpha-info-button", color="link", className="p-0 mt-2"),
                                    dbc.Collapse(
                                        dbc.Card(
                                            dbc.CardBody(
                                                "Alpha measures the excess return of the stock compared to the index. A positive alpha indicates the stock has outperformed the index, while a negative alpha indicates the stock has underperformed the index."
                                            ),
                                            className="mt-2"
                                        ),
                                        id="alpha-info-collapse",
                                        is_open=False,
                                    ),
                                ])
                            ])
                        ], className="mb-3"),
                        dbc.Card([
                            dbc.CardHeader(html.H5("Beta", className="card-title")),
                            dbc.CardBody([
                                html.Div([
                                    html.P("0.00", id="beta-value", className="card-text mb-0"),
                                    dbc.Button("What does this mean?", id="beta-info-button", color="link", className="p-0 mt-2"),
                                    dbc.Collapse(
                                        dbc.Card(
                                            dbc.CardBody(
                                                "Beta measures the volatility of a stock compared to the index. A beta of 1.0 means the stock moves with the market. A beta greater than 1.0 indicates the stock is more volatile than the market, while a beta less than 1.0 indicates the stock is less volatile than the market."
                                            ),
                                            className="mt-2"
                                        ),
                                        id="beta-info-collapse",
                                        is_open=False,
                                    ),
                                ])
                            ])
                        ]),
                    ], width=12)
                ])
            ])
        ], style={"display": "none"}),
        
        # Crypto Tab Content
        html.Div(id="crypto-tab-content", children=[
            html.H3("Cryptocurrency Analysis", className="mt-4 text-center"),
            html.P("This tab will show detailed cryptocurrency analysis.", className="text-center")
        ], style={"display": "none"}),
        
        # No interval component to avoid frequent API calls
    ], className="container")
])

# Callbacks
@app.callback(
    Output("stock-dropdown", "options"),
    Input("tabs", "active_tab")
)
def update_stock_options(active_tab):
    global STOCK_LIST
    if not STOCK_LIST:
        # For demo purposes, use a limited list of popular stocks
        STOCK_LIST = [
            {"label": "Apple Inc. (AAPL)", "value": "AAPL"},
            {"label": "Microsoft Corp. (MSFT)", "value": "MSFT"},
            {"label": "Amazon.com Inc. (AMZN)", "value": "AMZN"},
            {"label": "Alphabet Inc. (GOOGL)", "value": "GOOGL"},
            {"label": "Meta Platforms Inc. (META)", "value": "META"},
            {"label": "Tesla Inc. (TSLA)", "value": "TSLA"},
            {"label": "NVIDIA Corp. (NVDA)", "value": "NVDA"},
            {"label": "JPMorgan Chase & Co. (JPM)", "value": "JPM"},
            {"label": "Johnson & Johnson (JNJ)", "value": "JNJ"},
            {"label": "Visa Inc. (V)", "value": "V"}
        ]
    return STOCK_LIST


@app.callback(
    Output("index-dropdown", "options"),
    Input("tabs", "active_tab")
)
def update_index_options(active_tab):
    global INDEX_LIST
    if not INDEX_LIST:
        # For demo purposes, use a limited list of popular index funds
        INDEX_LIST = [
            {"label": "S&P 500 ETF (SPY)", "value": "SPY"},
            {"label": "Nasdaq 100 ETF (QQQ)", "value": "QQQ"},
            {"label": "Dow Jones Industrial Average ETF (DIA)", "value": "DIA"},
            {"label": "Russell 2000 ETF (IWM)", "value": "IWM"},
            {"label": "Vanguard Total Stock Market ETF (VTI)", "value": "VTI"}
        ]
    return INDEX_LIST


@app.callback(
    Output("stock-comparison-dropdown", "options"),
    Input("tabs", "active_tab")
)
def update_stock_index_options(active_tab):
    # Use the same stock list for both dropdowns
    return update_stock_options(active_tab)

@app.callback(
    Output("crypto-dropdown", "options"),
    Input("tabs", "active_tab")
)
def update_crypto_options(active_tab):
    global CRYPTO_LIST
    if not CRYPTO_LIST:
        # For demo purposes, use a limited list of popular cryptocurrencies
        CRYPTO_LIST = [
            {"label": "Bitcoin (BTC)", "value": "BTC"},
            {"label": "Ethereum (ETH)", "value": "ETH"},
            {"label": "Binance Coin (BNB)", "value": "BNB"},
            {"label": "Solana (SOL)", "value": "SOL"},
            {"label": "XRP (XRP)", "value": "XRP"},
            {"label": "Cardano (ADA)", "value": "ADA"},
            {"label": "Dogecoin (DOGE)", "value": "DOGE"},
            {"label": "Polkadot (DOT)", "value": "DOT"},
            {"label": "Chainlink (LINK)", "value": "LINK"},
            {"label": "Litecoin (LTC)", "value": "LTC"}
        ]
    return CRYPTO_LIST

@app.callback(
    [
        Output("stock-chart", "figure"),
        Output("stock-price-display", "children"),
        Output("stock-open-row", "children"),
        Output("stock-high-row", "children"),
        Output("stock-low-row", "children"),
        Output("stock-prev-close-row", "children"),
        Output("stock-fifty-day-row", "children")
    ],
    [
        Input("stock-dropdown", "value"),
        Input("refresh-button", "n_clicks")
    ]
)
def update_stock_data(symbol, n_clicks):
    global STOCK_DATA
    
    # Get the context that triggered the callback
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else ''
    
    # Check if we already have data for this symbol or if refresh button was clicked
    if symbol not in STOCK_DATA or trigger_id == "refresh-button":
        print(f"Fetching new stock data for {symbol}...")
        STOCK_DATA[symbol] = stock_fetcher.get_stock_data(symbol)
    
    stock_data = STOCK_DATA[symbol]
    
    # Create candlestick chart
    fig = go.Figure(data=[go.Candlestick(
        x=stock_data['date'],
        open=stock_data['open'],
        high=stock_data['high'],
        low=stock_data['low'],
        close=stock_data['close'],
        increasing_line_color='green',
        decreasing_line_color='red'
    )])
    
    # Get current price (last closing price) and opening price
    current_price = stock_data['close'].iloc[-1] if not stock_data.empty else 0
    opening_price = stock_data['open'].iloc[-1] if not stock_data.empty else 0
    
    # Determine price color based on comparison with opening price
    price_color = "green" if current_price >= opening_price else "red"
    
    fig.update_layout(
        title="",  # Remove title to avoid duplication
        xaxis_title="Date",
        yaxis_title="Price ($)",
        xaxis_rangeslider_visible=False,
        height=400,
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    # No annotation for current price as requested
    
    # Format date to remove year
    fig.update_xaxes(tickformat='%b %d')
    
    # Calculate metrics
    metrics = DataProcessor.calculate_metrics(stock_data)
    
    # Create colored price display
    price_display = html.H5(
        children=[
            f"{symbol} Stock Price - Current: ",
            html.Span(f"${current_price:,.2f}", style={"color": price_color})
        ],
        className="text-center"
    )
    
    # Update table rows
    open_row = [html.Th("Open"), html.Th(f"${metrics['open']:,.2f}")]
    high_row = [html.Td("Day High"), html.Td(f"${metrics['high']:,.2f}")]
    low_row = [html.Td("Day Low"), html.Td(f"${metrics['low']:,.2f}")]
    prev_close_row = [html.Td("Previous Close"), html.Td(f"${metrics['previous_close']:,.2f}")]
    fifty_day_row = [html.Td("Fifty Day Avg"), html.Td(f"${metrics['fifty_day_avg']:,.2f}")]
    
    return fig, price_display, open_row, high_row, low_row, prev_close_row, fifty_day_row

@app.callback(
    [
        Output("crypto-chart", "figure"),
        Output("crypto-price-display", "children"),
        Output("crypto-open-row", "children"),
        Output("crypto-high-row", "children"),
        Output("crypto-low-row", "children"),
        Output("crypto-prev-close-row", "children"),
        Output("crypto-fifty-day-row", "children")
    ],
    [
        Input("crypto-dropdown", "value"),
        Input("refresh-button", "n_clicks")
    ]
)
def update_crypto_data(symbol, n_clicks):
    global CRYPTO_DATA
    
    # Get the context that triggered the callback
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else ''
    
    # Check if we already have data for this symbol or if refresh button was clicked
    if symbol not in CRYPTO_DATA or trigger_id == "refresh-button":
        print(f"Fetching new crypto data for {symbol}...")
        CRYPTO_DATA[symbol] = crypto_fetcher.get_crypto_data(symbol)
    
    crypto_data = CRYPTO_DATA[symbol]
    
    # Create candlestick chart
    fig = go.Figure(data=[go.Candlestick(
        x=crypto_data['date'],
        open=crypto_data['open'],
        high=crypto_data['high'],
        low=crypto_data['low'],
        close=crypto_data['close'],
        increasing_line_color='green',
        decreasing_line_color='red'
    )])
    
    # Get current price (last closing price) and opening price
    current_price = crypto_data['close'].iloc[-1] if not crypto_data.empty else 0
    opening_price = crypto_data['open'].iloc[-1] if not crypto_data.empty else 0
    
    # Determine price color based on comparison with opening price
    price_color = "green" if current_price >= opening_price else "red"
    
    fig.update_layout(
        title="",  # Remove title to avoid duplication
        xaxis_title="Date",
        yaxis_title="Price ($)",
        xaxis_rangeslider_visible=False,
        height=400,
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    # No annotation for current price as requested
    
    # Format date to remove year
    fig.update_xaxes(tickformat='%b %d')
    
    # Calculate metrics
    metrics = DataProcessor.calculate_metrics(crypto_data)
    
    # Create colored price display
    price_display = html.H5(
        children=[
            f"{symbol}-USD Price - Current: ",
            html.Span(f"${current_price:,.2f}", style={"color": price_color})
        ],
        className="text-center"
    )
    
    # Update table rows
    open_row = [html.Th("Open"), html.Th(f"${metrics['open']:,.2f}")]
    high_row = [html.Td("Day High"), html.Td(f"${metrics['high']:,.2f}")]
    low_row = [html.Td("Day Low"), html.Td(f"${metrics['low']:,.2f}")]
    prev_close_row = [html.Td("Previous Close"), html.Td(f"${metrics['previous_close']:,.2f}")]
    fifty_day_row = [html.Td("Fifty Day Avg"), html.Td(f"${metrics['fifty_day_avg']:,.2f}")]
    
    return fig, price_display, open_row, high_row, low_row, prev_close_row, fifty_day_row

@app.callback(
    [
        Output("comparison-metrics", "style"),
        Output("correlation-value", "children"),
        Output("rel-performance-value", "children"),
        Output("volatility-ratio-value", "children")
    ],
    [
        Input("tabs", "active_tab"),
        Input("stock-dropdown", "value"),
        Input("crypto-dropdown", "value"),
        Input("refresh-button", "n_clicks")
    ]
)
def update_comparison_metrics(active_tab, stock_symbol, crypto_symbol, n_clicks):
    global STOCK_DATA, CRYPTO_DATA
    
    # Show comparison metrics only in comparison tab
    if active_tab != "comparison":
        return {"display": "none"}, "0.00", "0.00%", "0.00"
    
    # Get the context that triggered the callback
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else ''
    
    # Get data from cache or refresh if button was clicked
    if stock_symbol not in STOCK_DATA or trigger_id == "refresh-button":
        print(f"Fetching new stock data for {stock_symbol} (comparison)...")
        STOCK_DATA[stock_symbol] = stock_fetcher.get_stock_data(stock_symbol)
    
    if crypto_symbol not in CRYPTO_DATA or trigger_id == "refresh-button":
        print(f"Fetching new crypto data for {crypto_symbol} (comparison)...")
        CRYPTO_DATA[crypto_symbol] = crypto_fetcher.get_crypto_data(crypto_symbol)
    
    stock_data = STOCK_DATA[stock_symbol]
    crypto_data = CRYPTO_DATA[crypto_symbol]
    
    # Calculate comparison metrics
    comparison = DataProcessor.compare_assets(stock_data, crypto_data)
    
    # Format values
    correlation = f"{comparison['correlation']:.2f}"
    rel_performance = f"{comparison['relative_performance']:.2f}%"
    volatility_ratio = f"{comparison['volatility_ratio']:.2f}"
    
    return {"display": "block"}, correlation, rel_performance, volatility_ratio


# Callback to update refresh status and API calls remaining
# Single callback for refresh status that logs API calls to console
@app.callback(
    Output("refresh-status", "children"),
    Input("refresh-button", "n_clicks")
)
def update_refresh_status(n_clicks):
    if n_clicks > 0:
        # Log API calls to console for debugging
        if not USE_MOCK_DATA:
            fmp_calls = stock_fetcher.get_remaining_calls() or "Unknown"
            cmc_calls = crypto_fetcher.get_remaining_calls() or "Unknown"
            print(f"FMP API Calls remaining: {fmp_calls}")
            print(f"CMC API Calls remaining: {cmc_calls}")
            return html.Span("Data refreshed!", style={"color": "green"})
        else:
            print("Using mock data - no API calls made")
            return html.Span("Data refreshed! (using mock data)", style={"color": "green"})
    return ""


# Callback to show/hide tab content based on active tab
@app.callback(
    [
        Output("comparison-tab-content", "style"),
        Output("stocks-tab-content", "style"),
        Output("crypto-tab-content", "style")
    ],
    Input("tabs", "active_tab")
)
def update_tab_content(active_tab):
    comparison_style = {"display": "block"} if active_tab == "comparison" else {"display": "none"}
    stocks_style = {"display": "block"} if active_tab == "stocks" else {"display": "none"}
    crypto_style = {"display": "block"} if active_tab == "crypto" else {"display": "none"}
    
    return comparison_style, stocks_style, crypto_style


# Callback to update stock and index charts and metrics
@app.callback(
    [
        Output("stock-index-chart", "figure"),
        Output("index-chart", "figure"),
        Output("stock-index-price-display", "children"),
        Output("index-price-display", "children"),
        Output("stock-index-correlation-value", "children"),
        Output("alpha-value", "children"),
        Output("beta-value", "children"),
        # Stock metrics table outputs
        Output("stock-index-open-row", "children"),
        Output("stock-index-high-row", "children"),
        Output("stock-index-low-row", "children"),
        Output("stock-index-prev-close-row", "children"),
        Output("stock-index-fifty-day-row", "children"),
        # Index metrics table outputs
        Output("index-open-row", "children"),
        Output("index-high-row", "children"),
        Output("index-low-row", "children"),
        Output("index-prev-close-row", "children"),
        Output("index-fifty-day-row", "children")
    ],
    [
        Input("stock-comparison-dropdown", "value"),
        Input("index-dropdown", "value"),
        Input("refresh-button", "n_clicks")
    ]
)
def update_stock_index_comparison(stock_symbol, index_symbol, n_clicks):
    global STOCK_DATA, INDEX_DATA
    
    # Get the context that triggered the callback
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else ''
    
    # Get stock data from cache or refresh if button was clicked
    if stock_symbol not in STOCK_DATA or trigger_id == "refresh-button":
        print(f"Fetching new stock data for {stock_symbol} (stocks comparison)...")
        STOCK_DATA[stock_symbol] = stock_fetcher.get_stock_data(stock_symbol)
    
    # Get index data from cache or refresh if button was clicked
    if index_symbol not in INDEX_DATA or trigger_id == "refresh-button":
        print(f"Fetching new index data for {index_symbol} (stocks comparison)...")
        INDEX_DATA[index_symbol] = stock_fetcher.get_stock_data(index_symbol)
    
    stock_data = STOCK_DATA[stock_symbol]
    index_data = INDEX_DATA[index_symbol]
    
    # Create stock chart
    stock_fig = go.Figure(data=[go.Candlestick(
        x=stock_data['date'],
        open=stock_data['open'],
        high=stock_data['high'],
        low=stock_data['low'],
        close=stock_data['close'],
        increasing_line_color='green',
        decreasing_line_color='red'
    )])
    
    stock_fig.update_layout(
        title="",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        xaxis_rangeslider_visible=False,
        height=400,
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    # Format date to remove year
    stock_fig.update_xaxes(tickformat='%b %d')
    
    # Create index chart
    index_fig = go.Figure(data=[go.Candlestick(
        x=index_data['date'],
        open=index_data['open'],
        high=index_data['high'],
        low=index_data['low'],
        close=index_data['close'],
        increasing_line_color='green',
        decreasing_line_color='red'
    )])
    
    index_fig.update_layout(
        title="",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        xaxis_rangeslider_visible=False,
        height=400,
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    # Format date to remove year
    index_fig.update_xaxes(tickformat='%b %d')
    
    # Get current prices and opening prices
    stock_current_price = stock_data['close'].iloc[-1] if not stock_data.empty else 0
    stock_opening_price = stock_data['open'].iloc[-1] if not stock_data.empty else 0
    index_current_price = index_data['close'].iloc[-1] if not index_data.empty else 0
    index_opening_price = index_data['open'].iloc[-1] if not index_data.empty else 0
    
    # Determine price colors based on comparison with opening prices
    stock_price_color = "green" if stock_current_price >= stock_opening_price else "red"
    index_price_color = "green" if index_current_price >= index_opening_price else "red"
    
    # Create colored price displays
    stock_price_display = html.H5(
        children=[
            f"{stock_symbol} Stock Price - Current: ",
            html.Span(f"${stock_current_price:,.2f}", style={"color": stock_price_color})
        ],
        className="text-center"
    )
    
    index_price_display = html.H5(
        children=[
            f"{index_symbol} Price - Current: ",
            html.Span(f"${index_current_price:,.2f}", style={"color": index_price_color})
        ],
        className="text-center"
    )
    
    # Calculate comparison metrics
    comparison = DataProcessor.compare_stock_to_index(stock_data, index_data)
    
    # Format values
    correlation = f"{comparison['correlation']:.2f}"
    alpha = f"{comparison['alpha']:.2f}%"
    beta = f"{comparison['beta']:.2f}"
    
    # Calculate metrics for stock
    stock_metrics = DataProcessor.calculate_metrics(stock_data)
    
    # Calculate metrics for index
    index_metrics = DataProcessor.calculate_metrics(index_data)
    
    # Create table rows for stock metrics
    stock_open_row = [html.Th("Open"), html.Th(f"${stock_metrics['open']:,.2f}")]
    stock_high_row = [html.Td("Day High"), html.Td(f"${stock_metrics['high']:,.2f}")]
    stock_low_row = [html.Td("Day Low"), html.Td(f"${stock_metrics['low']:,.2f}")]
    stock_prev_close_row = [html.Td("Previous Close"), html.Td(f"${stock_metrics['previous_close']:,.2f}")]
    stock_fifty_day_row = [html.Td("Fifty Day Avg"), html.Td(f"${stock_metrics['fifty_day_avg']:,.2f}")]
    
    # Create table rows for index metrics
    index_open_row = [html.Th("Open"), html.Th(f"${index_metrics['open']:,.2f}")]
    index_high_row = [html.Td("Day High"), html.Td(f"${index_metrics['high']:,.2f}")]
    index_low_row = [html.Td("Day Low"), html.Td(f"${index_metrics['low']:,.2f}")]
    index_prev_close_row = [html.Td("Previous Close"), html.Td(f"${index_metrics['previous_close']:,.2f}")]
    index_fifty_day_row = [html.Td("Fifty Day Avg"), html.Td(f"${index_metrics['fifty_day_avg']:,.2f}")]
    
    return (
        stock_fig, index_fig, stock_price_display, index_price_display, correlation, alpha, beta,
        stock_open_row, stock_high_row, stock_low_row, stock_prev_close_row, stock_fifty_day_row,
        index_open_row, index_high_row, index_low_row, index_prev_close_row, index_fifty_day_row
    )


# Callbacks for toggling information sections
@app.callback(
    Output("correlation-info-collapse", "is_open"),
    Input("correlation-info-button", "n_clicks"),
    State("correlation-info-collapse", "is_open"),
)
def toggle_correlation_info(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open


@app.callback(
    Output("rel-performance-info-collapse", "is_open"),
    Input("rel-performance-info-button", "n_clicks"),
    State("rel-performance-info-collapse", "is_open"),
)
def toggle_rel_performance_info(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open


@app.callback(
    Output("volatility-ratio-info-collapse", "is_open"),
    Input("volatility-ratio-info-button", "n_clicks"),
    State("volatility-ratio-info-collapse", "is_open"),
)
def toggle_volatility_ratio_info(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open


# Callbacks for toggling stock-index information sections
@app.callback(
    Output("stock-index-correlation-info-collapse", "is_open"),
    Input("stock-index-correlation-info-button", "n_clicks"),
    State("stock-index-correlation-info-collapse", "is_open"),
)
def toggle_stock_index_correlation_info(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open


@app.callback(
    Output("alpha-info-collapse", "is_open"),
    Input("alpha-info-button", "n_clicks"),
    State("alpha-info-collapse", "is_open"),
)
def toggle_alpha_info(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open


@app.callback(
    Output("beta-info-collapse", "is_open"),
    Input("beta-info-button", "n_clicks"),
    State("beta-info-collapse", "is_open"),
)
def toggle_beta_info(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open


# Preload data for default symbols
def preload_data():
    print("Clearing cached data...")
    # Clear existing cached data
    STOCK_DATA.clear()
    CRYPTO_DATA.clear()
    INDEX_DATA.clear()
    
    print("Preloading data for default symbols...")
    # Preload stock data for default stock
    STOCK_DATA[DEFAULT_STOCK] = stock_fetcher.get_stock_data(DEFAULT_STOCK)
    # Preload crypto data for default crypto
    CRYPTO_DATA[DEFAULT_CRYPTO] = crypto_fetcher.get_crypto_data(DEFAULT_CRYPTO)
    # Preload index data for default index
    INDEX_DATA[DEFAULT_INDEX] = stock_fetcher.get_stock_data(DEFAULT_INDEX)
    print("Data preloading complete!")

if __name__ == "__main__":
    # Preload data before starting the server
    preload_data()
    app.run_server(debug=True)
