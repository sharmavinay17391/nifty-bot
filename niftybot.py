import os
import yfinance as yf
import pandas as pd
import asyncio
from telegram import Bot
from datetime import datetime
import numpy as np

# Read from GitHub Secrets
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

def calculate_rsi(prices, period=14):
    """Calculate RSI (Relative Strength Index)"""
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

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD"""
    try:
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        return {
            'macd': macd_line.iloc[-1],
            'signal': signal_line.iloc[-1],
            'histogram': histogram.iloc[-1],
            'prev_histogram': histogram.iloc[-2] if len(histogram) > 1 else 0
        }
    except Exception as e:
        print(f"MACD calc error: {e}")
        return {'macd': 0, 'signal': 0, 'histogram': 0, 'prev_histogram': 0}

def calculate_ema(prices, period):
    """Calculate EMA"""
    try:
        return prices.ewm(span=period).mean().iloc[-1]
    except:
        return 0

def calculate_bollinger_bands(prices, period=20, num_std=2):
    """Calculate Bollinger Bands"""
    try:
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper_band = sma + (std * num_std)
        lower_band = sma - (std * num_std)
        return {
            'upper': upper_band.iloc[-1],
            'middle': sma.iloc[-1],
            'lower': lower_band.iloc[-1],
            'current_price': prices.iloc[-1]
        }
    except Exception as e:
        print(f"Bollinger Bands error: {e}")
        return {'upper': 0, 'middle': 0, 'lower': 0, 'current_price': 0}

def calculate_volume_trend(df):
    """Check if volume is above average"""
    try:
        avg_volume = df['Volume'].rolling(20).mean().iloc[-1]
        current_volume = df['Volume'].iloc[-1]
        return current_volume > avg_volume
    except:
        return False

def fetch_nifty_candles():
    """Fetch NIFTY data using yfinance — works in GitHub Actions"""
    try:
        print("Fetching NIFTY data via yfinance...")
        ticker = yf.Ticker("^NSEI")
        df = ticker.history(period="90d", interval="1d")
        if df is None or df.empty:
            print("No data returned from yfinance")
            return None
        df = df.reset_index()
        df = df[['Close', 'Volume']].dropna()
        print(f"Fetched {len(df)} candles successfully!")
        return df
    except Exception as e:
        print(f"Failed to fetch candles: {e}")
        return None

def fetch_nifty_spot():
    """Fetch current NIFTY spot price"""
    try:
        ticker = yf.Ticker("^NSEI")
        info = ticker.fast_info
        return info.last_price
    except Exception as e:
        print(f"Failed to fetch spot: {e}")
        return None

def generate_advanced_signal(df):
    """Generate trading signal based on multiple indicators"""
    try:
        ema_20 = calculate_ema(df['Close'], 20)
        ema_50 = calculate_ema(df['Close'], 50)
        rsi = calculate_rsi(df['Close'], 14)
        macd_data = calculate_macd(df['Close'])
        bb = calculate_bollinger_bands(df['Close'], 20, 2)
        volume_up = calculate_volume_trend(df)

        last_close = df['Close'].iloc[-1]

        buy_score = 0
        sell_score = 0

        # 1. Trend (0-2 points)
        if last_close > ema_20 and ema_20 > ema_50:
            buy_score += 2
        elif last_close < ema_20 and ema_20 < ema_50:
            sell_score += 2
        elif last_close > ema_20:
            buy_score += 1
        elif last_close < ema_20:
            sell_score += 1

        # 2. RSI (0-2 points)
        if rsi < 30:
            buy_score += 2
        elif rsi > 70:
            sell_score += 2
        elif 30 <= rsi < 50:
            buy_score += 1
        elif 50 < rsi <= 70:
            sell_score += 1

        # 3. MACD (0-1 point)
        if macd_data['histogram'] > 0 and macd_data['prev_histogram'] <= 0:
            buy_score += 1
        elif macd_data['histogram'] < 0 and macd_data['prev_histogram'] >= 0:
            sell_score += 1

        # 4. Bollinger Bands (0-1 point)
        if last_close < bb['lower']:
            buy_score += 1
        elif last_close > bb['upper']:
            sell_score += 1

        # 5. Volume (0-1 point)
        if volume_up:
            if buy_score > sell_score:
                buy_score += 1
            elif sell_score > buy_score:
                sell_score += 1

        # Signal
        if buy_score >= 4:
            signal = "STRONG BUY ⬆️"
            confidence = "Very Strong"
        elif buy_score >= 3:
            signal = "BUY ↗️"
            confidence = "Strong"
        elif sell_score >= 4:
            signal = "STRONG SELL ⬇️"
            confidence = "Very Strong"
        elif sell_score >= 3:
            signal = "SELL ↘️"
            confidence = "Strong"
        else:
            signal = "HOLD ➡️"
            confidence = "Neutral"

        return {
            'signal': signal,
            'confidence': confidence,
            'buy_score': buy_score,
            'sell_score': sell_score,
            'ema_20': ema_20,
            'ema_50': ema_50,
            'rsi': rsi,
            'macd': macd_data['macd'],
            'macd_signal': macd_data['signal'],
            'bb_upper': bb['upper'],
            'bb_lower': bb['lower'],
            'last_close': last_close
        }
    except Exception as e:
        print(f"Signal generation error: {e}")
        return None

def suggest_strike(signal_text, spot):
    """Suggest option strike based on signal and spot price"""
    try:
        if spot is None:
            return "Could not fetch spot price"

        # Round to nearest 50
        atm_strike = round(spot / 50) * 50

        if "BUY" in signal_text:
            return f"BUY {atm_strike} CE | Spot: {spot:.2f}"
        elif "SELL" in signal_text:
            return f"BUY {atm_strike} PE | Spot: {spot:.2f}"
        else:
            return "No trade recommended (HOLD)"
    except Exception as e:
        print(f"Strike suggestion error: {e}")
        return "No trade recommended"

async def send_telegram_message(message):
    """Send message via Telegram"""
    try:
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='HTML')
        print("✅ Message sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send message: {e}")

def main():
    print("=" * 60)
    print("🤖 NIFTY Advanced Trading Bot")
    print("=" * 60)

    print("\n📊 Fetching NIFTY data...")
    candles = fetch_nifty_candles()

    if candles is None or len(candles) == 0:
        asyncio.run(send_telegram_message("❌ Failed to fetch NIFTY candles."))
        return

    print("✅ Data fetched successfully!")

    signal_data = generate_advanced_signal(candles)
    if signal_data is None:
        asyncio.run(send_telegram_message("❌ Failed to generate signal."))
        return

    print(f"\n📈 Signal: {signal_data['signal']}")
    print(f"Confidence: {signal_data['confidence']}")
    print(f"Buy Score: {signal_data['buy_score']}/5 | Sell Score: {signal_data['sell_score']}/5")

    spot = fetch_nifty_spot()
    suggestion = suggest_strike(signal_data['signal'], spot)

    message = (
        f"📊 <b>NIFTY Trading Signal</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{signal_data['signal']}\n"
        f"Confidence: {signal_data['confidence']}\n\n"
        f"<b>📈 Indicators:</b>\n"
        f"• RSI: {signal_data['rsi']:.2f}\n"
        f"• EMA 20: {signal_data['ema_20']:.2f}\n"
        f"• EMA 50: {signal_data['ema_50']:.2f}\n"
        f"• MACD: {signal_data['macd']:.4f}\n"
        f"• Last Close: {signal_data['last_close']:.2f}\n\n"
        f"<b>💡 Option Suggestion:</b>\n"
        f"{suggestion}\n\n"
        f"<b>Score:</b> Buy: {signal_data['buy_score']}/5 | Sell: {signal_data['sell_score']}/5\n"
        f"🕐 {datetime.now().strftime('%d-%m-%Y %H:%M IST')}"
    )

    asyncio.run(send_telegram_message(message))
    print("\n✅ Done!")
    print("=" * 60)

if __name__ == '__main__':
    main()
