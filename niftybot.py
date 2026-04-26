import os
import requests
import pandas as pd
import asyncio
from telegram import Bot
from datetime import datetime

# Read from GitHub Secrets
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

def calculate_rsi(prices, period=14):
    try:
        if len(prices) < period + 1:
            return 50
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]
    except Exception as e:
        print(f"RSI calc error: {e}")
        return 50

def fetch_nifty_candles():
    url = "https://www.nseindia.com/api/chart-databyindex?index=NIFTY"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        data = requests.get(url, headers=headers, timeout=10).json()
        if "grapthData" in data:
            candles = data["grapthData"]
            if candles:
                df = pd.DataFrame(candles, columns=['Timestamp', 'Close'])
                df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
                df = df.dropna()
                return df
        return None
    except Exception as e:
        print(f"Failed to fetch candles: {e}")
        return None

def fetch_option_chain(symbol="NIFTY"):
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        data = requests.get(url, headers=headers, timeout=10).json()
        return data
    except Exception as e:
        print(f"Failed to fetch option chain: {e}")
        return None

def get_signal(candles):
    try:
        rsi = calculate_rsi(candles['Close'], period=14)
        if rsi < 30:
            return "BUY", rsi
        elif rsi > 70:
            return "SELL", rsi
        else:
            return "HOLD", rsi
    except Exception as e:
        print(f"Signal error: {e}")
        return "HOLD", 50

def suggest_strike(option_chain, signal):
    try:
        if not option_chain or "records" not in option_chain:
            return "No option data available"
        
        records = option_chain["records"]
        if "underlyingValue" not in records:
            return "No underlying value found"
        
        spot = records["underlyingValue"]
        
        if "data" not in records:
            return "No strike data found"
        
        strikes = []
        for item in records["data"]:
            if "strikePrice" in item:
                strikes.append(item["strikePrice"])
        
        if not strikes:
            return "No strikes available"
        
        strikes = sorted(strikes, key=lambda x: abs(x - spot))
        atm_strike = strikes[0]
        
        if signal == "BUY":
            return f"BUY {atm_strike} CE (CALL) | Spot: {spot}"
        elif signal == "SELL":
            return f"BUY {atm_strike} PE (PUT) | Spot: {spot}"
        else:
            return "No trade recommended"
    except Exception as e:
        print(f"Strike suggestion error: {e}")
        return "No trade recommended"

async def send_telegram_message(message):
    try:
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text=message)
        print("✅ Message sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send message: {e}")

def main():
    print("Fetching NIFTY data...")
    candles = fetch_nifty_candles()
    
    if candles is None or len(candles) == 0:
        asyncio.run(send_telegram_message("Failed to fetch NIFTY candles."))
        return
    
    signal, rsi = get_signal(candles)
    print(f"Signal: {signal} (RSI: {rsi:.2f})")
    
    print("Fetching option chain...")
    option_chain = fetch_option_chain()
    
    if option_chain is None:
        asyncio.run(send_telegram_message("Failed to fetch NIFTY option chain."))
        return
    
    suggestion = suggest_strike(option_chain, signal)
    
    message = (
        f"📊 NIFTY Signal: {signal}\n"
        f"RSI: {rsi:.2f}\n"
        f"💡 Option: {suggestion}\n"
        f"🕐 Time: {datetime.now().strftime('%d-%m-%Y %H:%M')}"
    )
    
    asyncio.run(send_telegram_message(message))
    print("Done!")

if __name__ == '__main__':
    main()