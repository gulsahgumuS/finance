import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from binance.client import Client
import gradio as gr

# Binance API bilgilerinizi doldurun
api_key = "your_api_key"
api_secret = "your_api_secret"
client = Client(api_key, api_secret)

# Binance verisini çekme
def fetch_binance_data(symbol, interval, start_date, end_date):
    try:
        klines = client.get_historical_klines(symbol, interval, start_date, end_date)
        data = pd.DataFrame(klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        data['close'] = data['close'].astype(float)
        data['high'] = data['high'].astype(float)
        data['low'] = data['low'].astype(float)
        data['close_time'] = pd.to_datetime(data['close_time'], unit='ms')
        return data
    except Exception as e:
        raise ValueError(f"Error fetching Binance data: {e}")

# ZigZag algoritması: Dinamik high ve low noktalarını bulma
def zigzag_high_low(df, threshold=0.01):
    highs = []
    lows = []
    direction = None  # None: henüz belirlenmedi, 'up': artıyor, 'down': azalıyor
    
    for i in range(1, len(df)):
        current_high = df['high'].iloc[i]
        current_low = df['low'].iloc[i]
        previous_high = df['high'].iloc[i - 1]
        previous_low = df['low'].iloc[i - 1]
        
        if direction is None:
            # İlk hareket yönünü belirle
            if current_high > previous_high:
                direction = "up"
                highs.append((i, current_high))
            elif current_low < previous_low:
                direction = "down"
                lows.append((i, current_low))
        elif direction == "up":
            if current_high > highs[-1][1]:
                highs[-1] = (i, current_high)  # Yüksek noktayı güncelle
            elif current_low < previous_low * (1 - threshold):
                direction = "down"
                lows.append((i, current_low))
        elif direction == "down":
            if current_low < lows[-1][1]:
                lows[-1] = (i, current_low)  # Düşük noktayı güncelle
            elif current_high > previous_high * (1 + threshold):
                direction = "up"
                highs.append((i, current_high))
    
    return highs, lows

# Grafik çizen fonksiyon
def plot_high_low(symbol, interval, start_date, end_date):
    # Veriyi çekme
    data = fetch_binance_data(symbol, interval, start_date, end_date)
    
    # ZigZag hesaplama
    highs, lows = zigzag_high_low(data, threshold=0.01)
    
    # Grafik oluşturma
    plt.figure(figsize=(14, 7))
    plt.plot(data['close'], label="Closing Prices", color="blue", alpha=0.5)
    plt.plot(data['close'].rolling(window=20).mean(), label="Moving Average", color="orange")
    
    # Yalnızca son high ve önceki low noktalarını işaretle
    if highs:
        last_high_index, last_high_price = highs[-1]
        plt.scatter(data.index[last_high_index], last_high_price, color='red', label='Last High', marker='o', s=150, edgecolor='black')
    
    if lows and len(highs) > 1:
        # Son high'dan önceki en düşük low noktasını bul
        last_low_index, last_low_price = lows[-2]  # Son low'un bir öncesini alıyoruz
        plt.scatter(data.index[last_low_index], last_low_price, color='purple', label='Last Low', marker='o', s=150, edgecolor='black')
    
    plt.title(f"{symbol} Price Chart with ZigZag High and Low Points")
    plt.xlabel("Date")
    plt.ylabel("Price ($)")
    plt.legend()
    plt.grid()
    
    # Grafiği kaydetmek yerine direk gösteriyoruz
    plt.tight_layout()
    
    # Gradio ile grafik çıktısı
    plt.savefig('/tmp/price_chart.png')  # Grafik dosyasını geçici bir dosyaya kaydediyoruz
    plt.close()  # Grafiği kapat
    return '/tmp/price_chart.png'

# Gradio kullanıcı arayüzü tanımı
iface = gr.Interface(
    fn=plot_high_low,  # Grafik çizen fonksiyon
    inputs=[
        gr.Textbox(label="Symbol (e.g., BTCUSDT)", value="BTCUSDT"),  # İşlem çifti girişi
        gr.Dropdown(choices=["1m", "5m", "15m", "1h", "4h", "1d"], label="Interval", value="1h"),  # Zaman aralığı seçimi
        gr.Textbox(label="Start Date (e.g., 1 Jan, 2023)", value="1 Jan, 2023"),  # Başlangıç tarihi girişi
        gr.Textbox(label="End Date (e.g., 1 Jun, 2023)", value="1 Jun, 2023"),  # Bitiş tarihi girişi
    ],
    outputs="image",  # Grafik çıktısı
    live=False  # Canlı güncelleme kapalı
)

# Gradio arayüzünü başlat
iface.launch()