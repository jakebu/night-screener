import logging
import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
import time

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Create timestamped log file
log_filename = datetime.now().strftime("logs/log_%Y-%m-%d_%H-%M.txt")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()  # Also prints to console
    ]
)

API_KEY = 'xdnUr7m4klqE5LOoaVnKzBBdTtUjZzpz'

tickers = ['SPY', 'QQQ', 'PLTR', 'DASH', 'CRCL', 'CRWV', 'AMD', 'USO', 'AMZN', 'SMCI', 'NVDA', 'QUBT', 'ASTS', 'DKNG', 'PYPL', 'DHI', 'HD', 'TSLA', 'IBIT', 'USO', 'MSFT','IWM','META','RKLB','AMZN','NBIS','SPHR','RDW','CRWD','DELL','ORCL','GSRT']

def fetch_polygon_bars(ticker, multiplier=1, timespan='day', limit=500):
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/" \
          f"{(pd.Timestamp.now() - pd.Timedelta(days=350)).strftime('%Y-%m-%d')}/" \
          f"{pd.Timestamp.now().strftime('%Y-%m-%d')}?adjusted=true&sort=asc&limit={500}&apiKey={API_KEY}"
    
    r = requests.get(url)
    if r.status_code != 200:
        logging.info(f"Failed to fetch data for {ticker}: {r.status_code} {r.text}")
        return None
    
    data = r.json()
    if 'results' not in data:
        logging.info(f"No results for {ticker}")
        return None
    
    df = pd.DataFrame(data['results'])
    # Convert timestamps
    df['t'] = pd.to_datetime(df['t'], unit='ms')
    df.set_index('t', inplace=True)
    df.rename(columns={'o': 'Open', 'h': 'High', 'l': 'Low', 'c': 'Close', 'v': 'Volume'}, inplace=True)
    return df[['Open', 'High', 'Low', 'Close', 'Volume']]

qualified = []

for ticker in tickers:
    logging.info(f"Processing {ticker}...")
    data = fetch_polygon_bars(ticker)
    if data is None or data.empty:
        continue

    # Calculate indicators
    data['EMA20'] = EMAIndicator(data['Close'], window=20).ema_indicator()
    data['EMA50'] = EMAIndicator(data['Close'], window=50).ema_indicator()
    data['EMA200'] = EMAIndicator(data['Close'], window=200).ema_indicator()
    data['RSI'] = RSIIndicator(data['Close'], window=14).rsi()

    macd = MACD(data['Close'])
    data['MACD'] = macd.macd()
    data['MACD_Signal'] = macd.macd_signal()

    latest = data.iloc[-1]
    logging.info(f"\n{ticker} latest values:")
    logging.info(f"Close: {latest['Close']:.2f}, EMA20: {latest['EMA20']:.2f}, EMA50: {latest['EMA50']:.2f}, EMA200: {latest['EMA200']:.2f}")
    logging.info(f"RSI: {latest['RSI']:.2f}, MACD: {latest['MACD']:.4f}, MACD_Signal: {latest['MACD_Signal']:.4f}")

    # Screen criteria
    if (
        latest['Close'] > latest['EMA20'] > latest['EMA50'] > latest['EMA200'] and
        55 < latest['RSI'] < 70 and
        latest['MACD'] > latest['MACD_Signal']
    ):
        qualified.append(ticker)

        # Plot chart
        plt.figure(figsize=(10, 5))
        plt.title(f"{ticker} — Screening Match")
        plt.plot(data.index, data['Close'], label='Close Price')
        plt.plot(data.index, data['EMA20'], label='EMA 20')
        plt.plot(data.index, data['EMA50'], label='EMA 50')
        plt.plot(data.index, data['EMA200'], label='EMA 200')
        plt.plot(data.index, data['MACD'], label='MACD')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(f"{ticker}_chart.png")
        plt.close()
    
    time.sleep(25) # Wait 25 seconds since polygon.io only allows 5 request per minute (~3 per minute from experience)

logging.info("\nQualified tickers:")
logging.info(qualified)
