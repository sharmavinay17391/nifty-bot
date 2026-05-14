import os
import yfinance as yf
import pandas as pd
import numpy as np
import pytz
from datetime import datetime
import asyncio
from telegram import Bot

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

MIN_VOLUME_FILTER = 350000

# ==================== FULL STOCK LIST ====================
INDICES = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "SENSEX": "^BSESN",
    "FINNIFTY": "^NSEFIN",
    "MIDCPNIFTY": "^MIDCPNIFTY"
}

STOCKS = {
    "360ONE": "360ONE.NS", "AARTIIND": "AARTIIND.NS", "ABB": "ABB.NS", "ABCAPITAL": "ABCAPITAL.NS",
    "ABBOTINDIA": "ABBOTINDIA.NS", "ADANIENSOL": "ADANIENSOL.NS", "ADANIENT": "ADANIENT.NS",
    "ADANIGREEN": "ADANIGREEN.NS", "ADANIPORTS": "ADANIPORTS.NS", "ADANIPOWER": "ADANIPOWER.NS",
    "ALKEM": "ALKEM.NS", "AMBER": "AMBER.NS", "AMBUJACEM": "AMBUJACEM.NS", "ANGELONE": "ANGELONE.NS",
    "APLAPOLLO": "APLAPOLLO.NS", "APOLLOHOSP": "APOLLOHOSP.NS", "ASHOKLEY": "ASHOKLEY.NS",
    "ASIANPAINT": "ASIANPAINT.NS", "ASTRAL": "ASTRAL.NS", "AUBANK": "AUBANK.NS",
    "AUROPHARMA": "AUROPHARMA.NS", "AXISBANK": "AXISBANK.NS", "BAJAJ-AUTO": "BAJAJ-AUTO.NS",
    "BAJAJFINSV": "BAJAJFINSV.NS", "BAJAJHLDNG": "BAJAJHLDNG.NS", "BAJFINANCE": "BAJFINANCE.NS",
    "BANDHANBNK": "BANDHANBNK.NS", "BANKBARODA": "BANKBARODA.NS", "BANKINDIA": "BANKINDIA.NS",
    "BDL": "BDL.NS", "BEL": "BEL.NS", "BHARATFORG": "BHARATFORG.NS", "BHARTIARTL": "BHARTIARTL.NS",
    "BHEL": "BHEL.NS", "BIOCON": "BIOCON.NS", "BLUESTARCO": "BLUESTARCO.NS", "BOSCHLTD": "BOSCHLTD.NS",
    "BPCL": "BPCL.NS", "BRITANNIA": "BRITANNIA.NS", "BSE": "BSE.NS", "CAMS": "CAMS.NS",
    "CANBK": "CANBK.NS", "CDSL": "CDSL.NS", "CGPOWER": "CGPOWER.NS", "CHOLAFIN": "CHOLAFIN.NS",
    "CIPLA": "CIPLA.NS", "COALINDIA": "COALINDIA.NS", "COCHINSHIP": "COCHINSHIP.NS",
    "COFORGE": "COFORGE.NS", "COLPAL": "COLPAL.NS", "CONCOR": "CONCOR.NS", "CROMPTON": "CROMPTON.NS",
    "CUMMINSIND": "CUMMINSIND.NS", "DABUR": "DABUR.NS", "DALBHARAT": "DALBHARAT.NS",
    "DELHIVERY": "DELHIVERY.NS", "DIVISLAB": "DIVISLAB.NS", "DIXON": "DIXON.NS", "DLF": "DLF.NS",
    "DMART": "DMART.NS", "DRREDDY": "DRREDDY.NS", "EICHERMOT": "EICHERMOT.NS", "EXIDEIND": "EXIDEIND.NS",
    "FEDERALBNK": "FEDERALBNK.NS", "FORCEMOT": "FORCEMOT.NS", "FORTIS": "FORTIS.NS", "GAIL": "GAIL.NS",
    "GLENMARK": "GLENMARK.NS", "GMRAIRPORT": "GMRAIRPORT.NS", "GODFRYPHLP": "GODFRYPHLP.NS",
    "GODREJCP": "GODREJCP.NS", "GODREJPROP": "GODREJPROP.NS", "GRASIM": "GRASIM.NS", "HAL": "HAL.NS",
    "HAVELLS": "HAVELLS.NS", "HCLTECH": "HCLTECH.NS", "HDFCBANK": "HDFCBANK.NS", "HDFCAMC": "HDFCAMC.NS",
    "HDFCLIFE": "HDFCLIFE.NS", "HEROMOTOCO": "HEROMOTOCO.NS", "HINDALCO": "HINDALCO.NS",
    "HINDPETRO": "HINDPETRO.NS", "HINDUNILVR": "HINDUNILVR.NS", "HINDZINC": "HINDZINC.NS",
    "ICICIBANK": "ICICIBANK.NS", "ICICIGI": "ICICIGI.NS", "ICICIPRULI": "ICICIPRULI.NS",
    "IDEA": "IDEA.NS", "IDFCFIRSTB": "IDFCFIRSTB.NS", "IEX": "IEX.NS", "INDHOTEL": "INDHOTEL.NS",
    "INDIANB": "INDIANB.NS", "INDIGO": "INDIGO.NS", "INDUSINDBK": "INDUSINDBK.NS",
    "INDUSTOWER": "INDUSTOWER.NS", "INFY": "INFY.NS", "INOXWIND": "INOXWIND.NS", "IOC": "IOC.NS",
    "IREDA": "IREDA.NS", "IRFC": "IRFC.NS", "ITC": "ITC.NS", "JINDALSTEL": "JINDALSTEL.NS",
    "JIOFIN": "JIOFIN.NS", "JSWENERGY": "JSWENERGY.NS", "JSWSTEEL": "JSWSTEEL.NS",
    "JUBLFOOD": "JUBLFOOD.NS", "KALYANKJIL": "KALYANKJIL.NS", "KAYNES": "KAYNES.NS",
    "KEI": "KEI.NS", "KFINTECH": "KFINTECH.NS", "KOTAKBANK": "KOTAKBANK.NS", "KPITTECH": "KPITTECH.NS",
    "LAURUSLABS": "LAURUSLABS.NS", "LICHSGFIN": "LICHSGFIN.NS", "LICI": "LICI.NS", "LODHA": "LODHA.NS",
    "LT": "LT.NS", "LUPIN": "LUPIN.NS", "M&M": "M&M.NS", "MANAPPURAM": "MANAPPURAM.NS",
    "MARICO": "MARICO.NS", "MARUTI": "MARUTI.NS", "MAXHEALTH": "MAXHEALTH.NS", "MAZDOCK": "MAZDOCK.NS",
    "MCX": "MCX.NS", "MFSL": "MFSL.NS", "MOTHERSON": "MOTHERSON.NS", "MOTILALOFS": "MOTILALOFS.NS",
    "MPHASIS": "MPHASIS.NS", "MUTHOOTFIN": "MUTHOOTFIN.NS", "NATIONALUM": "NATIONALUM.NS",
    "NBCC": "NBCC.NS", "NESTLEIND": "NESTLEIND.NS", "NHPC": "NHPC.NS", "NMDC": "NMDC.NS",
    "NTPC": "NTPC.NS", "NUVAMA": "NUVAMA.NS", "OBEROIRLTY": "OBEROIRLTY.NS", "OFSS": "OFSS.NS",
    "ONGC": "ONGC.NS", "OIL": "OIL.NS", "PAGEIND": "PAGEIND.NS", "PERSISTENT": "PERSISTENT.NS",
    "PETRONET": "PETRONET.NS", "PFC": "PFC.NS", "PIDILITIND": "PIDILITIND.NS", "PNB": "PNB.NS",
    "POLYCAB": "POLYCAB.NS", "POWERGRID": "POWERGRID.NS", "RELIANCE": "RELIANCE.NS", "SBIN": "SBIN.NS",
    "SHRIRAMFIN": "SHRIRAMFIN.NS", "SIEMENS": "SIEMENS.NS", "SOLARINDS": "SOLARINDS.NS",
    "SRF": "SRF.NS", "SUNPHARMA": "SUNPHARMA.NS", "SUZLON": "SUZLON.NS", "TATAMOTORS": "TATAMOTORS.NS",
    "TATACONSUM": "TATACONSUM.NS", "TATASTEEL": "TATASTEEL.NS", "TCS": "TCS.NS", "TECHM": "TECHM.NS",
    "TITAN": "TITAN.NS", "TRENT": "TRENT.NS", "TVSMOTOR": "TVSMOTOR.NS", "ULTRACEMCO": "ULTRACEMCO.NS",
    "VOLTAS": "VOLTAS.NS", "WIPRO": "WIPRO.NS", "ZOMATO": "ZOMATO.NS", "ZYDUSLIFE": "ZYDUSLIFE.NS"
}

ALL_SYMBOLS = {**INDICES, **STOCKS}

# ==================== SIGNAL WITH PATTERNS ====================
def generate_signal(df):
    if len(df) < 30:
        return None, 0, None, []

    last = df['Close'].iloc[-1]
    ma20 = df['Close'].rolling(20).mean().iloc[-1]
    vol_avg = df['Volume'].rolling(20).mean().iloc[-1]

    score = 0
    reasons = []

    # Technical
    if last > ma20:
        score += 4
        reasons.append("Above 20 EMA")
    if last > df['Close'].rolling(10).mean().iloc[-1]:
        score += 3
        reasons.append("Momentum")

    if df['Volume'].iloc[-1] > vol_avg * 1.8:
        score += 3
        reasons.append("Volume Surge")

    # Patterns
    body = abs(df['Close'] - df['Open'])
    lower_shadow = df[['Open','Close']].min(axis=1) - df['Low']
    if (lower_shadow > 2 * body).iloc[-1]:
        score += 4
        reasons.append("Hammer Pattern")

    if score >= 8:
        signal = "🚀 VERY STRONG BUY ⬆️"
        atm = round(last / 10) * 10
        return signal, score, f"BUY {atm} CE", reasons

    return None, 0, None, []

# ==================== TELEGRAM ====================
async def send_telegram(message):
    try:
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='HTML')
    except:
        pass

# ==================== MAIN ====================
async def main():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)

    if now.weekday() >= 5 or now.hour < 9 or now.hour >= 15:
        print("Market Closed")
        return

    msg = f"<b>🔥 VERY STRONG SIGNALS (Score ≥ 8)</b>\n"
    msg += f"🕒 {now.strftime('%d-%m-%Y %H:%M IST')}\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

    count = 0
    for name, ticker in ALL_SYMBOLS.items():
        try:
            df = yf.Ticker(ticker).history(period="2d", interval="5m")
            if df.empty or len(df) < 30:
                continue
            if name not in INDICES and df['Volume'].iloc[-1] < MIN_VOLUME_FILTER:
                continue

            signal, score, option, reasons = generate_signal(df)
            if signal:
                spot = df['Close'].iloc[-1]
                msg += f"<b>{name}</b> @ {spot:.1f}\n"
                msg += f"{signal} | Score: {score}\n"
                msg += f"Option: {option}\n"
                if reasons:
                    msg += f"→ {', '.join(reasons)}\n\n"
                count += 1
        except:
            continue

    if count > 0:
        await send_telegram(msg)
        print(f"✅ {count} strong signals sent")
    else:
        print("No strong signals this cycle")

if __name__ == "__main__":
    asyncio.run(main())
