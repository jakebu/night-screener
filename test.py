import yfinance as yf
import time

tickers = ["AAPL", "MSFT", "TSLA"]

for ticker in tickers:
    try:
        print(f"Fetching {ticker}...")
        data = yf.Ticker(ticker).history(period="1d")
        print(data)
    except Exception as e:
        if "rate limit" in str(e).lower() or "Too Many Requests" in str(e):
            print(f"Rate limited on {ticker}. Waiting 60 seconds...")
            time.sleep(60)
        else:
            print(f"Error on {ticker}: {e}")
