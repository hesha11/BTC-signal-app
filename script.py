import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objs as go
import ta
from streamlit_autorefresh import st_autorefresh
from twilio.rest import Client

# ================== Twilio Configuration ===================
account_sid = 'AC20df6982b13620151baa8ec430d9c7be'  # Your Twilio Account SID
auth_token = '22e71bb3c24f7dca56c113eb825d2971'  # 🚨 Please reset your token and use the new one here
twilio_whatsapp_number = 'whatsapp:+14155238886'
your_whatsapp_number = 'whatsapp:+94714900557'

client = Client(account_sid, auth_token)

def send_whatsapp_message(message_body):
    try:
        message = client.messages.create(
            from_=twilio_whatsapp_number,
            body=message_body,
            to=your_whatsapp_number
        )
        print(f"WhatsApp message sent! SID: {message.sid}")
    except Exception as e:
        print(f"Error sending WhatsApp message: {e}")

# ================== Streamlit Setup ===================
st.set_page_config(page_title="BTCUSDT Advanced Signal Dashboard", layout="wide")
st.title("📊 Real-Time BTCUSDT Dashboard with Full Signal Logic (Indicators + SMC + S&R)")
st_autorefresh(interval=15_000, key="refresh")

# Binance API Setup
symbol = "BTCUSDT"
interval = "1m"
limit = 500

def get_binance_ohlcv(symbol, interval, limit=500):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data, columns=[
        "Time", "Open", "High", "Low", "Close", "Volume", "_", "_", "_", "_", "_", "_"
    ])
    df["Time"] = pd.to_datetime(df["Time"], unit="ms")
    df[["Open", "High", "Low", "Close", "Volume"]] = df[["Open", "High", "Low", "Close", "Volume"]].astype(float)
    return df

def find_support_resistance(df, window=10):
    supports = []
    resistances = []
    for i in range(window, len(df) - window):
        low_range = df['Low'][i - window:i + window]
        high_range = df['High'][i - window:i + window]
        if df['Low'][i] == low_range.min():
            supports.append((df['Time'][i], df['Low'][i]))
        if df['High'][i] == high_range.max():
            resistances.append((df['Time'][i], df['High'][i]))
    return supports, resistances

def detect_bos(df):
    recent_high = df['High'].iloc[-2]
    previous_high = df['High'].iloc[-5]
    if df['Close'].iloc[-1] > recent_high > previous_high:
        return "BOS Up"
    elif df['Close'].iloc[-1] < df['Low'].iloc[-2] < df['Low'].iloc[-5]:
        return "BOS Down"
    else:
        return "No BOS"

def detect_liquidity_sweep(df, supports, resistances):
    sweep_detected = None
    current_low = df['Low'].iloc[-1]
    current_high = df['High'].iloc[-1]
    for t, level in supports[-3:]:
        if current_low < level * 0.999:
            sweep_detected = "Sweep Below Support"
            break
    for t, level in resistances[-3:]:
        if current_high > level * 1.001:
            sweep_detected = "Sweep Above Resistance"
            break
    return sweep_detected or "No Sweep"

# Fetch data
df = get_binance_ohlcv(symbol, interval, limit)

# Add Indicators
df['SMA20'] = ta.trend.sma_indicator(df['Close'], window=20)
df['EMA20'] = ta.trend.ema_indicator(df['Close'], window=20)
df['UpperBand'] = ta.volatility.bollinger_hband(df['Close'], window=20)
df['LowerBand'] = ta.volatility.bollinger_lband(df['Close'], window=20)
df['MACD'] = ta.trend.macd_diff(df['Close'])
df['RSI'] = ta.momentum.rsi(df['Close'])
df['Volume_SMA'] = ta.trend.sma_indicator(df['Volume'], window=20)

# S&R Levels
supports, resistances = find_support_resistance(df)

# Smart Money Concepts
detected_bos = detect_bos(df)
detected_sweep = detect_liquidity_sweep(df, supports, resistances)

# ================== Chart ===================
fig = go.Figure()

fig.add_trace(go.Candlestick(
    x=df["Time"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Candles"
))

fig.add_trace(go.Scatter(x=df["Time"], y=df["SMA20"], line=dict(color="blue", width=1), name="SMA20"))
fig.add_trace(go.Scatter(x=df["Time"], y=df["EMA20"], line=dict(color="orange", width=1), name="EMA20"))
fig.add_trace(go.Scatter(x=df["Time"], y=df["UpperBand"], line=dict(color="green", width=1, dash='dot'), name="Boll Upper"))
fig.add_trace(go.Scatter(x=df["Time"], y=df["LowerBand"], line=dict(color="red", width=1, dash='dot'), name="Boll Lower"))

fig.add_trace(go.Bar(x=df["Time"], y=df["Volume"], marker_color='gray', name='Volume', yaxis='y2', opacity=0.3))

for t, price in resistances[-5:]:
    fig.add_hline(y=price, line=dict(color='red', width=1, dash='dot'), annotation_text="Resistance", annotation_position="top left")

for t, price in supports[-5:]:
    fig.add_hline(y=price, line=dict(color='green', width=1, dash='dot'), annotation_text="Support", annotation_position="bottom left")

fig.update_layout(
    title="BTCUSDT Live Chart with Full Signals",
    xaxis=dict(title='Time', rangeslider=dict(visible=False)),
    yaxis=dict(title='Price'),
    yaxis2=dict(title='Volume', overlaying='y', side='right', showgrid=False),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    height=600
)

st.plotly_chart(fig, use_container_width=True)

# ================== RSI and MACD ===================
st.subheader("📈 RSI (Relative Strength Index)")
fig_rsi = go.Figure()
fig_rsi.add_trace(go.Scatter(x=df["Time"], y=df["RSI"], name="RSI", line=dict(color='purple')))
fig_rsi.add_hline(y=70, line=dict(color='red', dash='dash'))
fig_rsi.add_hline(y=30, line=dict(color='green', dash='dash'))
fig_rsi.update_layout(yaxis_title="RSI", height=300)
st.plotly_chart(fig_rsi, use_container_width=True)

st.subheader("📉 MACD Histogram")
fig_macd = go.Figure()
fig_macd.add_trace(go.Bar(x=df["Time"], y=df["MACD"], name="MACD", marker_color='orange'))
fig_macd.update_layout(yaxis_title="MACD", height=300)
st.plotly_chart(fig_macd, use_container_width=True)

# ================== Signal Logic ===================
st.subheader("📌 Final Multi-Indicator + SMC Signal")
latest = df.iloc[-1]

is_uptrend = latest['Close'] > latest['SMA20'] and latest['Close'] > latest['EMA20']
is_downtrend = latest['Close'] < latest['SMA20'] and latest['Close'] < latest['EMA20']

rsi_buy = latest['RSI'] < 30
rsi_sell = latest['RSI'] > 70

macd_buy = latest['MACD'] > 0
macd_sell = latest['MACD'] < 0

bollinger_buy = latest['Close'] <= latest['LowerBand'] * 1.005
bollinger_sell = latest['Close'] >= latest['UpperBand'] * 0.995

volume_avg = df['Volume'].rolling(window=20).mean().iloc[-1]
high_volume = latest['Volume'] > volume_avg

signal_sent = False

if is_uptrend and rsi_buy and macd_buy and bollinger_buy and high_volume and detected_bos == "BOS Up" and "Sweep Below Support" in detected_sweep:
    st.success("✅ STRONG BUY SIGNAL: Full Confluence")
    if not signal_sent:
        send_whatsapp_message("✅ STRONG BUY SIGNAL detected in BTCUSDT 🚀🚀🚀")
        signal_sent = True
elif is_downtrend and rsi_sell and macd_sell and bollinger_sell and high_volume and detected_bos == "BOS Down" and "Sweep Above Resistance" in detected_sweep:
    st.error("❌ STRONG SELL SIGNAL: Full Confluence")
    if not signal_sent:
        send_whatsapp_message("❌ STRONG SELL SIGNAL detected in BTCUSDT 📉📉📉")
        signal_sent = True
else:
    st.info("⏳ HOLD: No strong confluence yet.")

st.write(f"**Trend:** {'Uptrend' if is_uptrend else 'Downtrend' if is_downtrend else 'Sideways'}")
st.write(f"**RSI:** {latest['RSI']:.2f}")
st.write(f"**MACD:** {latest['MACD']:.4f}")
st.write(f"**Volume:** {latest['Volume']:.4f} (Avg: {volume_avg:.4f})")
st.write(f"**Break of Structure:** {detected_bos}")
st.write(f"**Liquidity Sweep:** {detected_sweep}")
