
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator

# === CONFIGURATION ===
API_KEY = 'xdnUr7m4klqE5LOoaVnKzBBdTtUjZzpz'  # <-- Replace with your real API key
TICKER = 'TSLA'
START_DATE = '2023-01-01'
END_DATE = datetime.now().strftime('%Y-%m-%d')


def fetch_polygon_bars(ticker, multiplier=1, timespan='day'):
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{START_DATE}/{END_DATE}?adjusted=true&sort=asc&apiKey={API_KEY}"
    r = requests.get(url)
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame(data['results'])
    df['t'] = pd.to_datetime(df['t'], unit='ms')
    df.set_index('t', inplace=True)
    df.rename(columns={'o': 'Open', 'h': 'High', 'l': 'Low', 'c': 'Close', 'v': 'Volume'}, inplace=True)
    return df[['Open', 'High', 'Low', 'Close', 'Volume']]


def simulate_gain(df, entry_index, target_gain=0.03, max_hold_days=14):
    entry_price = df.iloc[entry_index + 1]['Open']
    for day in range(1, max_hold_days + 1):
        if entry_index + 1 + day >= len(df):
            break
        current_price = df.iloc[entry_index + 1 + day]['Close']
        gain = (current_price - entry_price) / entry_price
        if gain >= target_gain:
            return True, day
    return False, max_hold_days


df = fetch_polygon_bars(TICKER)
print(f"Data starts on {df.index[0].date()}, ends on {df.index[-1].date()}, total rows: {len(df)}")

# Indicators
df['EMA8'] = EMAIndicator(df['Close'], window=8).ema_indicator()
df['EMA21'] = EMAIndicator(df['Close'], window=21).ema_indicator()
df['EMA50'] = EMAIndicator(df['Close'], window=50).ema_indicator()
df['MACD'] = MACD(df['Close']).macd()
df['MACD_Signal'] = MACD(df['Close']).macd_signal()
df['RSI'] = RSIIndicator(df['Close'], window=14).rsi()

# Identify signal points
signals = []
signal_dates = []
for i in range(50, len(df) - 15):
    row = df.iloc[i]
    if (
        row['Close'] > row['EMA8'] > row['EMA21'] > row['EMA50'] and
        row['MACD'] > row['MACD_Signal'] and
        55 < row['RSI'] < 70
    ):
        signal_dates.append(df.index[i + 1])
        gain_hit, days = simulate_gain(df, i)
        signals.append({
            'Date': df.index[i + 1].strftime('%Y-%m-%d'),
            'Entry Price': df.iloc[i + 1]['Open'],
            'Gain >= 3%': gain_hit,
            'Days to Hit': days if gain_hit else None
        })

# Summary
signals_df = pd.DataFrame(signals)
total_signals = len(signals_df)
successes = signals_df['Gain >= 3%'].sum()
success_rate = successes / total_signals if total_signals > 0 else 0

print("\nBacktest Results for", TICKER)
print("Total Signals:", total_signals)
print("Hit 3% Gain:", successes)
print("Success Rate: {:.2%}".format(success_rate))

# === CHART with SIGNAL POINTS ===
plt.figure(figsize=(12, 6))
plt.plot(df.index, df['Close'], label='Close Price', linewidth=1.5)
plt.scatter(signal_dates, df.loc[signal_dates, 'Close'], color='limegreen', label='Signal', marker='^', s=100)
plt.title(f"{TICKER} — Price with Entry Signals")
plt.xlabel("Date")
plt.ylabel("Price")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("signal_price_chart.png")
plt.show()
