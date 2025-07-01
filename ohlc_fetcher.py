import requests
import boto3
import pandas as pd
import pandas_ta as ta
from datetime import date, timedelta
from config import AWSConfig  # Assuming you have a config.py with AWSConfig class


class FetchOHLC:
    def __init__(self, instrument_key="NSE_INDEX|Nifty 50", interval='minutes/60', ssm_param='/upstox/access_token'):
        self.instrument_key = instrument_key
        self.interval = interval

        current_date = date.today()
        six_days_before = current_date - timedelta(days=14)

        self.from_date = six_days_before.strftime('%Y-%m-%d')
        self.to_date = current_date.strftime('%Y-%m-%d')

        config = AWSConfig()
        self.token = config.get_parameter('/upstox/access_token')['Parameter']['Value']
        # self.redirect_uri = config.get_parameter('/upstox/redirect_uri')['Parameter']['Value']
        # self.client_secret = config.get_parameter('/upstox/client_secret')['Parameter']['Value']



    def current_day_ohlc(self):
        url = f'https://api.upstox.com/v3/historical-candle/intraday/{self.instrument_key}/{self.interval}'
        headers = {'Accept': 'application/json', 'Authorization': f'Bearer {self.token}'}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            candles = data.get('data', {}).get('candles', [])
            df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'oi'])
            df = df.drop(columns=['volume', 'oi'])
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            df = df.sort_values(by='timestamp').reset_index(drop=True)
            return df
        else:
            raise Exception(f"Error fetching intraday data: {response.status_code} - {response.text}")

    def all_days_ohlc(self):
        intraday_df = self.current_day_ohlc()
        url = f"https://api.upstox.com/v3/historical-candle/{self.instrument_key}/{self.interval}/{self.to_date}/{self.from_date}"
        headers = {'Accept': 'application/json', 'Authorization': f'Bearer {self.token}'}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()['data']['candles']
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'oi'])
            df = df.drop(columns=['volume', 'oi'])
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            df = df.sort_values(by='timestamp').reset_index(drop=True)

            combined = pd.concat([df, intraday_df], ignore_index=True)
            combined['Date'] = pd.to_datetime(combined['timestamp'].str.split().str[0])
            combined['Day'] = combined['Date'].dt.day_name()
            combined['EMA_20'] = ta.ema(combined['close'], length=20)
            supertrend = ta.supertrend(high=combined['high'], low=combined['low'], close=combined['close'], length=10, multiplier=3.5)
            combined['supertrend'] = supertrend['SUPERTd_10_3.5']
            return combined
        else:
            raise Exception(f"Error fetching historical data: {response.status_code} - {response.text}")


# Run the code
# ohlc = FetchOHLC()
# all_days_df = ohlc.all_days_ohlc()
# print(all_days_df.tail(30))

