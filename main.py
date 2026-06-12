import datetime
import random
import sqlite3
import requests
import telebot
import time

# ==============================
# إعدادات الربط مع cTrader API
# ==============================
CTRADER_CLIENT_ID = "30283_xuuTTpTjC3BvNyoMLex2xjapLkKHAUMgyETcgF4MF56qVstEf2H"
CTRADER_SECRET = "a5L0aUul9b7mxiBXuFua7UFyqADPFXu6RhvdoSg2yT8D92IVhH"
CTRADER_ACCOUNT = "10640911"  # FxPro Demo Account

# ==============================
# إعدادات الربط مع Telegram Bot
# ==============================
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "7391407789"
bot = telebot.TeleBot(TELEGRAM_TOKEN)

def send_telegram_message(message):
    bot.send_message(CHAT_ID, message)

# ==============================
# Market Scanner (Simulation فقط، لاحقًا API)
# ==============================
assets = ["Gold","Silver","US30","Nasdaq100","USDJPY"]
max_spread = {"Gold":0.5,"Silver":0.3,"US30":1.0,"Nasdaq100":1.0,"USDJPY":0.2}

def market_scanner():
    scores = {}
    for asset in assets:
        atr = random.uniform(0.1,2.0)
        spread = random.uniform(0.01,1.0)
        move = random.uniform(10,100)
        vol = random.uniform(5,50)
        if spread > max_spread[asset]:
            continue
        volatility_pct = atr / random.uniform(100,200)
        score = (atr*20)+(move/2)-(spread*10)+vol+(volatility_pct*100)
        scores[asset] = round(score,2)
    return scores

# ==============================
# Timeframe Selection
# ==============================
def choose_timeframe(atr):
    if atr < 0.5: return "M1"
    elif atr < 1.0: return "M5"
    else: return "M15-H1"

# ==============================
# Support & Resistance
# ==============================
def support_resistance(prices):
    resistance = max(prices[-50:])
    support = min(prices[-50:])
    return resistance,support

# ==============================
# Orders مع Validation
# ==============================
def calculate_orders(resistance,support,atr,spread):
    buffer = spread+0.2*atr
    distance = atr+spread+buffer
    buy_stop = resistance+distance
    sell_stop = support-distance
    buy_limit = support-distance
    sell_limit = resistance+distance
    if buy_limit > resistance: buy_limit = support-distance
    if sell_limit < support: sell_limit = resistance+distance
    return {"buy_stop":buy_stop,"sell_stop":sell_stop,
            "buy_limit":buy_limit,"sell_limit":sell_limit}

# ==============================
# Risk Manager
# ==============================
def position_sizing(equity,risk_pct,atr,pip_value):
    risk_amount = equity*(risk_pct/100)
    stop_distance = 0.5*atr
    lot_size = risk_amount/(stop_distance*pip_value)
    return round(lot_size,2)

def manage_trade(entry,atr,asset,trade_type,resistance=None,support=None):
    if entry is None:
        return None
    
    if trade_type in ["BREAKOUT_BUY","LIQUIDITY_SWEEP_BUY"]:
        sl = support if support else entry-(0.5*atr)
    elif trade_type in ["BREAKOUT_SELL","LIQUIDITY_SWEEP_SELL"]:
        sl = resistance if resistance else entry+(0.5*atr)
    else:
        sl = entry-(0.5*atr)

    trailing = trailing_stop(asset,atr)
    return {"SL":sl,"Trailing":trailing}

# ==============================
# Trailing Stop لكل زوج
# ==============================
def trailing_stop(asset,atr):
    factors = {"Gold":0.5,"Silver":0.4,"US30":1.0,"Nasdaq100":0.8,"USDJPY":0.3}
    return factors.get(asset,0.3)*atr

# ==============================
# Entry Engine مع Liquidity Sweep
# ==============================
def entry_engine(price,high,low,volume,avg_volume,spread,atr,candle_close):
    sweep_size = abs(price-high)
    volume_ratio = volume/avg_volume if avg_volume>0 else 0

    if price > high and candle_close > high and sweep_size > 0.2*atr and volume_ratio > 1.5 and spread < 0.3:
        return "BREAKOUT_BUY",volume_ratio,sweep_size
    elif price < low and candle_close < low and sweep_size > 0.2*atr and volume_ratio > 1.5 and spread < 0.3:
        return "BREAKOUT_SELL",volume_ratio,sweep_size
    elif price > high and candle_close < high and sweep_size > 0.2*atr and volume_ratio > 1.5:
        return "LIQUIDITY_SWEEP_SELL",volume_ratio,sweep_size
    elif price < low and candle_close > low and sweep_size > 0.2*atr and volume_ratio > 1.5:
        return "LIQUIDITY_SWEEP_BUY",volume_ratio,sweep_size
    else:
        return "NO_ENTRY",volume_ratio,sweep_size

# ==============================
# Signal → Order Mapping
# ==============================
def signal_to_order(signal,orders):
    if signal=="BREAKOUT_BUY": return orders["buy_stop"]
    elif signal=="BREAKOUT_SELL": return orders["sell_stop"]
    elif signal=="LIQUIDITY_SWEEP_SELL": return orders["sell_limit"]
    elif signal=="LIQUIDITY_SWEEP_BUY": return orders["buy_limit"]
    else: return None

# ==============================
# Loop مع Telegram إخراج
# ==============================
if __name__ == "__main__":
    while True:
        prices = [random.uniform(160,161) for _ in range(100)]
        scores = market_scanner()
        best_asset = max(scores,key=scores.get)
        res,sup = support_resistance(prices)
        orders = calculate_orders(res,sup,atr=0.3,spread=0.05)
        lot = position_sizing(equity=1000,risk_pct=2,atr=0.3,pip_value=0.1)
        signal,volume_ratio,sweep_size = entry_engine(price=160.5,high=res,low=sup,
                                                      volume=120,avg_volume=100,spread=0.05,
                                                      atr=0.3,candle_close=160.4)
        entry_price = signal_to_order(signal,orders)

        if entry_price is not None:
            trade = manage_trade(entry=entry_price,atr=0.3,asset=best_asset,
                                 trade_type=signal,resistance=res,support=sup)
            message = f"""
🚀 صفقة جديدة!
📊 الزوج: {best_asset}
📈 الإشارة: {signal}
🎯 الدخول: {entry_price}
💵 حجم العقد: {lot}
🛡️ إدارة الصفقة: {trade}
"""
            send_telegram_message(message)
            print(message)
        else:
            print("⏸️ لا توجد إشارة حالياً")

        time.sleep(60)  # يعاود كل دقيقة
