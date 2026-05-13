import os
import yfinance as yf
import pandas as pd
import numpy as np
import pytz
from datetime import datetime
import asyncio
import time
from telegram import Bot

# ==================== CONFIG ====================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

CAPITAL = 100000
MAX_RISK_PER_TRADE = 0.02
VIX_THRESHOLD = 22
MIN_VOLUME_FILTER = 500000

# ==================== SYMBOLS ====================
INDICES = {
    "NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK", "SENSEX": "^BSESN",
    "FINNIFTY": "^NSEFIN", "MIDCPNIFTY": "^MIDCPNIFTY"
}

STOCKS = {
    "360ONE": "360ONE.NS", "AARTIIND": "AARTIIND.NS", "ABB": "ABB.NS", "ABCAPITAL": "ABCAPITAL.NS",
    "ABBOTINDIA": "ABBOTINDIA.NS", "ADANIENSOL": "ADANIENSOL.NS", "ADANIENT": "ADANIENT.NS",
    "ADANIGREEN": "ADANIGREEN.NS", "ADANIPORTS": "ADANIPORTS.NS", "ADANIPOWER": "ADANIPOWER.NS",
    "ALKEM": "ALKEM.NS", "AMBER": "AMBER.NS", "AMBUJACEM": "AMBUJACEM.NS", "ANGELONE": "ANGELONE.NS",
    "APLAPOLLO": "APLAPOLLO.NS", "APOLLOHOSP": "APOLLOHOSP.NS", "ASHOKLEY": "ASHOKLEY.NS",
    "ASIANPAINT": "ASIANPAINT.NS", "ASTRAL": "ASTRAL.NS", "AUBANK": "AUBANK.NS",
    "AUROPHARMA": "AUROPHARMA.NS", "AXISBANK": "AXISBANK.NS", "BAJAJ-AUTO": "BAJAJ-AUTO.NS",
    "BAJAJFINSV": "BAJAJFINSV.NS", "BAJFINANCE": "BAJFINANCE.NS", "BANDHANBNK": "BANDHANBNK.NS",
    "BANKBARODA": "BANKBARODA.NS", "BEL": "BEL.NS", "BHARTIARTL": "BHARTIARTL.NS",
    "BHEL": "BHEL.NS", "BIOCON": "BIOCON.NS", "BPCL": "BPCL.NS", "BRITANNIA": "BRITANNIA.NS",
    "CANBK": "CANBK.NS", "CHOLAFIN": "CHOLAFIN.NS", "CIPLA": "CIPLA.NS", "COALINDIA": "COALINDIA.NS",
    "COCHINSHIP": "COCHINSHIP.NS", "COLPAL": "COLPAL.NS", "DABUR": "DABUR.NS", "DELHIVERY": "DELHIVERY.NS",
    "DIVISLAB": "DIVISLAB.NS", "DIXON": "DIXON.NS", "DLF": "DLF.NS", "DMART": "DMART.NS",
    "DRREDDY": "DRREDDY.NS", "EICHERMOT": "EICHERMOT.NS", "EXIDEIND": "EXIDEIND.NS",
    "FEDERALBNK": "FEDERALBNK.NS", "GAIL": "GAIL.NS", "GLENMARK": "GLENMARK.NS",
    "GODREJCP": "GODREJCP.NS", "GRASIM": "GRASIM.NS", "HAL": "HAL.NS", "HAVELLS": "HAVELLS.NS",
    "HCLTECH": "HCLTECH.NS", "HDFCBANK": "HDFCBANK.NS", "HDFCLIFE": "HDFCLIFE.NS",
    "HEROMOTOCO": "HEROMOTOCO.NS", "HINDALCO": "HINDALCO.NS", "HINDPETRO": "HINDPETRO.NS",
    "HINDUNILVR": "HINDUNILVR.NS", "ICICIBANK": "ICICIBANK.NS", "IDEA": "IDEA.NS",
    "IDFCFIRSTB": "IDFCFIRSTB.NS", "INDHOTEL": "INDHOTEL.NS", "INDIGO": "INDIGO.NS",
    "INDUSINDBK": "INDUSINDBK.NS", "INFY": "INFY.NS", "IOC": "IOC.NS", "IRFC": "IRFC.NS",
    "ITC": "ITC.NS", "JINDALSTEL": "JINDALSTEL.NS", "JSWSTEEL": "JSWSTEEL.NS", "KOTAKBANK": "KOTAKBANK.NS",
    "LT": "LT.NS", "LUPIN": "LUPIN.NS", "M&M": "M&M.NS", "MARUTI": "MARUTI.NS",
    "NTPC": "NTPC.NS", "ONGC": "ONGC.NS", "PIDILITIND": "PIDILITIND.NS", "PNB": "PNB.NS",
    "POLYCAB": "POLYCAB.NS", "POWERGRID": "POWERGRID.NS", "RELIANCE": "RELIANCE.NS", "SBIN": "SBIN.NS",
    "SUNPHARMA": "SUNPHARMA.NS", "SUZLON": "SUZLON.NS", "TATAMOTORS": "TATAMOTORS.NS",
    "TATACONSUM": "TATACONSUM.NS", "TATASTEEL": "TATASTEEL.NS", "TCS": "TCS.NS", "TECHM": "TECHM.NS",
    "TITAN": "TITAN.NS", "TRENT": "TRENT.NS", "TVSMOTOR": "TVSMOTOR.NS", "ULTRACEMCO": "ULTRACEMCO.NS",
    "VOLTAS": "VOLTAS.NS", "WIPRO": "WIPRO.NS", "ZOMATO": "ZOMATO.NS", "ZYDUSLIFE": "ZYDUSLIFE.NS"
}

ALL_SYMBOLS = {**INDICES, **STOCKS}

# ==================== INDICATORS ====================
def calculate_atr(df, period=14):
    tr = pd.concat([df['High']-df['Low'], (df['High']-df['Close'].shift()).abs(), (df['Low']-df['Close'].shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calculate_supertrend(df, period=10, multiplier=3):
    try:
        atr = calculate_atr(df, period)
        hl2 = (df['High'] + df['Low']) / 2
        upper = hl2 + multiplier * atr
        lower = hl2 - multiplier * atr
        trend = np.where(df['Close'] > upper.shift(), 1, np.where(df['Close'] < lower.shift(), -1, np.nan))
        trend_series = pd.Series(trend).ffill()
        return trend_series.iloc[-1], lower.iloc[-1] if trend_series.iloc[-1] == 1 else upper.iloc[-1]
    except:
        return 0, 0

def calculate_vwap(df):
    try:
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        return (tp * df['Volume']).cumsum() / df['Volume'].cumsum().iloc[-1]
    except:
        return 0

def calculate_adx(df, period=14):
    try:
        tr = calculate_atr(df, period)
        dm_plus = df['High'].diff()
        dm_minus = df['Low'].diff().abs()
        di_plus = (dm_plus.where(dm_plus > dm_minus, 0) / tr).rolling(period).mean() * 100
        di_minus = (dm_minus.where(dm_minus > dm_plus, 0) / tr).rolling(period).mean() * 100
        dx = (di_plus - di_minus).abs() / (di_plus + di_minus) * 100
        return dx.rolling(period).mean().iloc[-1]
    except:
        return 20

def calculate_rsi(prices, period=14):
    try:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs)).iloc[-1]
    except:
        return 50

def get_vix():
    try:
        return yf.Ticker("^INDIAVIX").fast_info.last_price
    except:
        return 18

# ==================== PATTERN DETECTION ====================
def detect_candlestick_patterns(df):
    body = abs(df['Close'] - df['Open'])
    upper_shadow = df['High'] - df[['Open', 'Close']].max(axis=1)
    lower_shadow = df[['Open', 'Close']].min(axis=1) - df['Low']
    return {
        'Hammer': (lower_shadow > 2 * body) & (upper_shadow < body * 0.5) & (df['Close'] > df['Open']),
        'ShootingStar': (upper_shadow > 2 * body) & (lower_shadow < body * 0.5) & (df['Close'] < df['Open']),
        'BullEngulfing': (df['Close'].shift(1) < df['Open'].shift(1)) & (df['Close'] > df['Open']) & 
                         (df['Close'] > df['Open'].shift(1)) & (df['Open'] < df['Close'].shift(1)),
        'BearEngulfing': (df['Close'].shift(1) > df['Open'].shift(1)) & (df['Close'] < df['Open']) & 
                         (df['Close'] < df['Open'].shift(1)) & (df['Open'] > df['Close'].shift(1))
    }

def detect_double_top_bottom(df, window=8):
    try:
        highs = df['High'].rolling(window=window, center=True).max()
        lows = df['Low'].rolling(window=window, center=True).min()
        dt = (abs(df['High'] - highs.shift(window)) < df['High']*0.005) & (abs(df['High'] - highs.shift(-window)) < df['High']*0.005)
        db = (abs(df['Low'] - lows.shift(window)) < df['Low']*0.005) & (abs(df['Low'] - lows.shift(-window)) < df['Low']*0.005)
        return dt.iloc[-1], db.iloc[-1]
    except:
        return False, False

# ==================== MAIN SIGNAL ====================
def generate_signal(df, name):
    vix = get_vix()
    if vix > VIX_THRESHOLD:
        return "CAUTION - HIGH VOL", "Low", 0, ["High VIX"], 0, "HOLD"

    patterns = detect_candlestick_patterns(df)
    dt, db = detect_double_top_bottom(df)

    score = 0
    reasons = []

    super_dir, st_level = calculate_supertrend(df)
    vwap = calculate_vwap(df)
    adx = calculate_adx(df)
    rsi = calculate_rsi(df['Close'])
    last = df['Close'].iloc[-1]

    if super_dir == 1 and last > vwap:
        score += 4
        reasons.append("Supertrend Bullish + Above VWAP")
    elif super_dir == -1 and last < vwap:
        score -= 4
        reasons.append("Supertrend Bearish + Below VWAP")

    if adx > 25:
        score += 2
        reasons.append(f"Strong Trend (ADX {adx:.1f})")

    if rsi < 35:
        score += 2
        reasons.append("RSI Oversold")
    elif rsi > 65:
        score -= 2
        reasons.append("RSI Overbought")

    if patterns['Hammer'].iloc[-1] or patterns['BullEngulfing'].iloc[-1] or db:
        score += 3
        reasons.append("Bullish Pattern")
    if patterns['ShootingStar'].iloc[-1] or patterns['BearEngulfing'].iloc[-1] or dt:
        score -= 3
        reasons.append("Bearish Pattern")

    if score >= 7:
        signal = "STRONG BUY ⬆️"
        conf = "Very High"
    elif score >= 4:
        signal = "BUY ↗️"
        conf = "High"
    elif score <= -7:
        signal = "STRONG SELL ⬇️"
        conf = "Very High"
    elif score <= -4:
        signal = "SELL ↘️"
        conf = "High"
    else:
        signal = "HOLD ➡️"
        conf = "Neutral"

    risk_amount = CAPITAL * MAX_RISK_PER_TRADE
    stop_dist = abs(last - st_level) if st_level != 0 else last * 0.01
    qty = int(risk_amount / stop_dist) if stop_dist > 0 else 0

    atm = round(last / 10) * 10
    bias = " (Bullish Pattern)" if score > 4 else " (Bearish Pattern)" if score < -4 else ""
    option = f"BUY {atm} CE{bias}" if "BUY" in signal else f"BUY {atm} PE{bias}" if "SELL" in signal else "HOLD"

    return signal, conf, score, reasons, qty, option

# ==================== TELEGRAM ====================
async def send_telegram(message):
    try:
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='HTML')
    except:
        pass

# ==================== 15-MINUTE LOOP ====================
def run_15min_bot():
    print("🚀 15-Minute Trading Bot Started...")
    while True:
        try:
            ist = pytz.timezone('Asia/Kolkata')
            now = datetime.now(ist)

            if now.weekday() >= 5 or now.hour < 9 or now.hour >= 15:
                time.sleep(900)
                continue

            print(f"🔄 Running at {now.strftime('%H:%M:%S')}")

            msg = f"<b>🔴 15-MIN LIVE SIGNALS</b>\n"
            msg += f"🕒 {now.strftime('%d-%m-%Y %H:%M IST')} | VIX: {get_vix():.1f}\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

            count = 0
            for name, ticker in ALL_SYMBOLS.items():
                try:
                    df = yf.Ticker(ticker).history(period="5d", interval="5m")
                    if df.empty or len(df) < 30:
                        continue
                    if name not in INDICES and df['Volume'].iloc[-1] < MIN_VOLUME_FILTER:
                        continue

                    signal, conf, score, reasons, qty, option = generate_signal(df, name)
                    spot = df['Close'].iloc[-1]

                    if score >= 4 or score <= -4:   # Only send strong signals
                        msg += f"<b>{name}</b> @ {spot:.1f}\n"
                        msg += f"{signal} | {conf} (Score: {score})\n"
                        msg += f"Qty: ~{qty} | {option}\n"
                        if reasons:
                            msg += f"→ {reasons[0]}\n\n"
                        count += 1
                except:
                    continue

            if count > 0:
                asyncio.run(send_telegram(msg))
                print(f"✅ Sent {count} signals")

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(900)  # 15 minutes

if __name__ == "__main__":
    run_15min_bot()
