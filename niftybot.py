import os
import yfinance as yf
import pandas as pd
import numpy as np
import pytz
from datetime import datetime
import asyncio
from telegram import Bot

# ==================== CONFIG ====================
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

MIN_VOLUME_FILTER = 350000

# ==================== FULL SYMBOL LIST ====================
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

# ==================== PATTERN DETECTION ====================
def detect_patterns(df):
    body = abs(df['Close'] - df['Open'])
    upper_shadow = df['High'] - df[['Open','Close']].max(axis=1)
    lower_shadow = df[['Open','Close']].min(axis=1) - df['Low']

    patterns = {
        'Hammer': (lower_shadow > 2 * body) & (upper_shadow < body * 0.5) & (df['Close'] > df['Open']),
        'BullEngulfing': (df['Close'].shift(1) < df['Open'].shift(1)) & (df['Close'] > df['Open']) & 
                         (df['Close'] > df['Open'].shift(1)) & (df['Open'] < df['Close'].shift(1)),
        'BearEngulfing': (df['Close'].shift(1) > df['Open'].shift(1)) & (df['Close'] < df['Open']) & 
                         (df['Close'] < df['Open'].shift(1)) & (df['Open'] > df['Close'].shift(1))
    }
    
    # Double Bottom (Bullish)
    lows = df['Low'].rolling(window=8, center=True).min()
    double_bottom = (abs(df['Low'] - lows.shift(8)) < df['Low']*0.008) & \
                    (abs(df['Low'] - lows.shift(-8)) < df['Low']*0.008)
    
    return patterns, double_bottom.iloc[-1]

# ==================== SIGNAL ENGINE (Score >= 8) ====================
def generate_signal(df):
    if len(df) < 30:
        return None, 0, None, []

    last = df['Close'].iloc[-1]
    ma20 = df['Close'].rolling(20).mean().iloc[-1]
    vol_avg = df['Volume'].rolling(20).mean().iloc[-1]

    score = 0
    reasons = []

    patterns, double_bottom = detect_patterns(df)

    # Technical Conditions
    if last > ma20:
        score += 4
        reasons.append("Above 20 EMA")

    if last > df['Close'].rolling(10).mean().iloc[-1]:
        score += 3
        reasons.append("Short Momentum")

    if df['Volume'].iloc[-1] > vol_avg * 1.8:
        score += 3
        reasons.append("Volume Surge")

    # Pattern Conditions (High Success Rate)
    if patterns['Hammer'].iloc[-1]:
        score += 4
        reasons.append("Hammer Candlestick (81%)")

    if patterns['BullEngulfing'].iloc[-1]:
        score += 4
        reasons.append("Bullish Engulfing (72%)")

    if double_bottom:
        score += 3
        reasons.append("Double Bottom (64%)")

    # Final Decision
    signal = None
    if score >= 8:
        signal = "🚀 VERY STRONG BUY ⬆️"
    elif score <= -8:
        signal = "🔻 VERY STRONG SELL ⬇️"

    atm = round(last / 10) * 10
    option = f"BUY {atm} CE" if "BUY" in str(signal) else f"BUY {atm} PE" if "SELL" in str(signal) else "HOLD"

    return signal, score, option, reasons

# ==================== TELEGRAM ====================
async def send_telegram(message):
    try:
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='HTML')
        print("✅ Very Strong Signal Sent!")
    except Exception as e:
        print(f"Telegram Error: {e}")

# ==================== MAIN ====================
def main():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)

    if now.weekday() >= 5 or now.hour < 9 or now.hour >= 15:
        print("Market Closed")
        return

    msg = f"<b>🔥 VERY STRONG SIGNALS (Score ≥ 8)</b>\n"
    msg += f"🕒 {now.strftime('%d-%m-%Y %H:%M IST')}\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

    strong_count = 0

    for name, ticker in ALL_SYMBOLS.items():
        try:
            df = yf.Ticker(ticker).history(period="2d", interval="5m")
            if df.empty or len(df) < 30:
                continue
            if name not in INDICES and df['Volume'].iloc[-1] < MIN_VOLUME_FILTER:
                continue

            signal, score, option, reasons = generate_signal(df)
            if signal is None:
                continue

            spot = df['Close'].iloc[-1]

            msg += f"<b>{name}</b> @ {spot:.1f}\n"
            msg += f"{signal} | Score: {score}\n"
            msg += f"Option: {option}\n"
            if reasons:
                msg += f"→ {', '.join(reasons)}\n\n"
            strong_count += 1

        except:
            continue

    if strong_count > 0:
        asyncio.run(send_telegram(msg))
        print(f"✅ Sent {strong_count} VERY STRONG signals")
    else:
        print("No signals above score 8 this cycle")

if __name__ == "__main__":
    asyncio.run(main())
