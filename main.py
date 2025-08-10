import yfinance as yf
import datetime
import pytz
import time
import requests

# ======================================
# 📜 Stock List
STOCKS = {
    "HDFCBANK.NS": "12345",
    "INFY.NS": "12345",
    "TCS.NS": "12345",
    "ONGC.NS": "12345",
    "GOLDBEES.NS": "12345",
    "ANGELONE.NS": "12345",
    "SUNPHARMA.BO": "12345",
    "TECHM.NS": "12345",
    "HINDUNILVR.BO": "12345",
    "BSE.NS": "12345",
    "SILVERBEES.NS": "12345",
    "BAJAJ-AUTO.NS": "12345",
    "WIPRO.BO": "12345",
    "BHARTIARTL.BO": "12345",
    "TATAMOTORS.NS": "12345",
    "APOLLOTYRE.NS": "12345",
    "JSWSTEEL.NS": "12345",
    "HINDCOPPER.BO": "12345",
    "HAL.NS": "12345",
    "TATAPOWER.NS": "12345",
    "LT.NS": "12345",
    "LTF.NS": "12345",
    "MAZDOCK.NS": "12345",
    "COCHINSHIP.BO": "12345",
    "MOTHERSON.BO": "12345",
    "BAJAJFINSV.NS": "12345",
    "CAMS.BO": "12345",
    "TRENT.BO": "12345",
    "GPPL.NS": "12345",
    "NCC.BO": "12345",
    "RECLTD.BO": "12345",
    "CDSL.NS": "12345",
    "MCX.NS": "12345"
}

# ======================================
# 📊 Notification tracking per stock
stock_notify_tracker = {
    symbol: {"count": 0, "last_sent": None} for symbol in STOCKS.keys()
}

# 🕒 Market Hours (IST)
MARKET_OPEN = datetime.time(9, 15)
MARKET_CLOSE = datetime.time(15, 30)
TIMEZONE = pytz.timezone('Asia/Kolkata')

# 📥 Fetch 15-min Candle
def fetch_candles(symbol):
    try:
        data = yf.download(
            tickers=symbol,
            interval="15m",
            period="15d",
            progress=False,
            auto_adjust=False,
        )
        data.reset_index(inplace=True)
        data.rename(columns={'Datetime': 'time', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}, inplace=True)
        return data
    except Exception as e:
        print(f"❌ Error fetching data for {symbol}:", e)
        return None

# 📈 Apply EMA
def apply_emas(df):
    if df is None or df.empty or len(df) < 200:
        return None
    df['EMA_13'] = df['close'].ewm(span=13).mean()
    df['EMA_50'] = df['close'].ewm(span=50).mean()
    df['EMA_200'] = df['close'].ewm(span=200).mean()
    return df

# 📲 Telegram Configuration
TELEGRAM_TOKEN = "7888730208:AAH8raBpIc_uiTUGYrPtlVJ0bu2EMclBtMc"
TELEGRAM_CHAT_ID = "6157562865"

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        }
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print(f"❌ Telegram Error: {response.text}")
    except Exception as e:
        print("❌ Telegram Exception:", e)

# 🔍 Check EMA Signal
def check_signal(df, symbol, tracker):
    latest = df.iloc[-1]

    ema_13 = latest['EMA_13'].item() if hasattr(latest['EMA_13'], 'item') else float(latest['EMA_13'])
    ema_50 = latest['EMA_50'].item() if hasattr(latest['EMA_50'], 'item') else float(latest['EMA_50'])
    ema_200 = latest['EMA_200'].item() if hasattr(latest['EMA_200'], 'item') else float(latest['EMA_200'])
    close = latest['close'].item() if hasattr(latest['close'], 'item') else float(latest['close'])
    open_ = latest['open'].item() if hasattr(latest['open'], 'item') else float(latest['open'])

    ema_diff = abs(ema_13 - ema_50)
    threshold = 5

    bullish = (
        ema_diff < threshold and
        ema_200 > ema_50 and
        ema_200 > ema_13 and
        close > ema_50 and
        close > open_
    )

    bearish = (
        ema_diff < threshold and
        ema_200 < ema_50 and
        ema_200 < ema_13 and
        close < ema_50 and
        close < open_
    )

    now = datetime.datetime.now(TIMEZONE)
    track = tracker[symbol]

    allow_notify = (
        track["last_sent"] is None or
        (now - track["last_sent"]).total_seconds() >= 7200
    )

    if bullish:
        signal = "Bullish ✅"
        print(f"🔔 {symbol} => {signal}")
        if allow_notify:
            send_telegram(f"📈 {symbol} => {signal}")
            track["count"] += 1
            track["last_sent"] = now
        return signal, close, ema_13, ema_50, ema_200

    elif bearish:
        signal = "Bearish ❌"
        print(f"🔔 {symbol} => {signal}")
        if allow_notify:
            send_telegram(f"📉 {symbol} => {signal}")
            track["count"] += 1
            track["last_sent"] = now
        return signal, close, ema_13, ema_50, ema_200

    else:
        print(f"➖ {symbol} => No Signal")
        return "No Signal ➖", close, ema_13, ema_50, ema_200

# 🕒 Check if Market Open
def is_market_open():
    now = datetime.datetime.now(TIMEZONE)
    if now.weekday() >= 5:
        return False
    return MARKET_OPEN <= now.time() <= MARKET_CLOSE

# 🔁 Main Loop
print("🚀 EMA Trading Bot Started")
while True:
    now = datetime.datetime.now(TIMEZONE).time()
    if now > MARKET_CLOSE:
        print("Market closed. Exiting loop.")
        break
    try:
        if not is_market_open():
            print("💤 Market closed. Waiting...")
            time.sleep(300)
            continue

        for symbol in STOCKS.keys():
            print(f"\n🔄 Checking {symbol}...")
            df = fetch_candles(symbol)
            if df is None or len(df) < 200:
                print(f"⚠️ Not enough data for {symbol}")
                continue

            df = apply_emas(df)
            if df is None:
                continue

            signal, close, ema_13, ema_50, ema_200 = check_signal(df, symbol, stock_notify_tracker)
            now_time = datetime.datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M")

            print(f"🔔 {symbol} => {signal}")

        print("⏳ Waiting 1 minute...")
        time.sleep(60)

    except KeyboardInterrupt:
        print("🛑 Bot stopped by user")
        break
    except Exception as e:
        print(f"❌ Error: {e}")
        time.sleep(60)
