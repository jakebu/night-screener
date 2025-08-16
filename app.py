
from flask import Flask, request, render_template, send_file
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
import os, boto3

app = Flask(__name__)
ssm_name = os.getenv("POLYGON_API_PARAM","/signals/POLYGON_API_KEY")
api_key = os.getenv("POLYGON_API_KEY")
if not api_key:
    ssm = boto3.client("ssm")
    api_key = ssm.get_parameter(Name=ssm_name, WithDecryption=True)["Parameter"]["Value"]

def fetch_polygon_bars(ticker, start_date, end_date, multiplier=1, timespan='day'):
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{start_date}/{end_date}?adjusted=true&sort=asc&apiKey={api_key}"
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

@app.route('/', methods=['GET', 'POST'])
def index():
    summary = ""
    chart_path = ""
    if request.method == 'POST':
        ticker = request.form['ticker'].upper()
        start_date = '2023-01-01'
        end_date = datetime.now().strftime('%Y-%m-%d')
        try:
            df = fetch_polygon_bars(ticker, start_date, end_date)
            df['EMA8'] = EMAIndicator(df['Close'], window=8).ema_indicator()
            df['EMA21'] = EMAIndicator(df['Close'], window=21).ema_indicator()
            df['EMA50'] = EMAIndicator(df['Close'], window=50).ema_indicator()
            df['MACD'] = MACD(df['Close']).macd()
            df['MACD_Signal'] = MACD(df['Close']).macd_signal()
            df['RSI'] = RSIIndicator(df['Close'], window=14).rsi()

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

            signals_df = pd.DataFrame(signals)
            total_signals = len(signals_df)
            successes = signals_df['Gain >= 3%'].sum()
            success_rate = f"{(successes / total_signals * 100):.2f}%" if total_signals > 0 else "0%"

            summary = f"Backtest Results for {ticker}:<br>Total Signals: {total_signals}<br>Hit 3% Gain: {successes}<br>Success Rate: {success_rate}"

            # Plot chart
            chart_path = f"static/{ticker}_chart.png"
            plt.figure(figsize=(12, 6))
            plt.plot(df.index, df['Close'], label='Close Price', linewidth=1.5)
            plt.scatter(signal_dates, df.loc[signal_dates, 'Close'], color='limegreen', label='Signal', marker='^', s=100)
            plt.title(f"{ticker} — Price with Entry Signals")
            plt.xlabel("Date")
            plt.ylabel("Price")
            plt.legend()
            plt.grid(True)
            plt.tight_layout()
            plt.savefig(chart_path)
            plt.close()

        except Exception as e:
            summary = f"Error processing {ticker}: {e}"

    return render_template('index.html', summary=summary, chart=chart_path)

if __name__ == '__main__':
    os.makedirs('static', exist_ok=True)
    app.run(debug=True)
