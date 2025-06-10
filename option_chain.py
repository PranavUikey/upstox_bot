import pandas as pd
import requests
import yaml
from expiry_fetcher import FetchExpiryDates
from ohlc_fetcher import FetchOHLC
from config import AWSConfig  # Assuming you have a config.py with AWSConfig class

class BullCallBearSpread:
    def __init__(self):
        # Fetch expiry date
        expiry_dates = FetchExpiryDates()

        self.expiry_date = expiry_dates.expiry_date()[1]

        # Fetch Nifty close price
        ohlc = FetchOHLC()
        try:
            self.nifty_close = ohlc.all_days_ohlc()['close'].values[-1]
        except Exception as e:
            raise Exception("Failed to get Nifty close price: " + str(e))
        config = AWSConfig()
        self.token = config.get_parameter('/upstox/access_token')['Parameter']['Value']
        

        print(f"[INFO] Using Expiry: {self.expiry_date}")
        print(f"[INFO] Nifty Close: {self.nifty_close}")

    def option_chain(self, side):
        instrument_key = "NSE_INDEX|Nifty 50"
        segment = 'OPTIDX'
        url = "https://api.upstox.com/v2/option/chain"

        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.token}'
        }
        params = {
            'instrument_key': instrument_key,
            'expiry_date': self.expiry_date,
            'segment': segment
        }

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch option chain: {response.status_code} - {response.text}")

        data = response.json().get('data', [])
        if not data:
            raise Exception("Empty data received from Upstox Option Chain API")

        # df = pd.DataFrame(data)
        df = pd.DataFrame(response.json()['data'])
        

        if side == 'call':
            df = (pd.concat([df,
                pd.json_normalize (df['call_options']),
                pd.json_normalize(df['call_options'].apply(lambda x: x['option_greeks'])),
                pd.json_normalize(df['call_options'].apply(lambda x: x['market_data']))], axis=1)
            .loc[:, ['expiry', 'strike_price', 'delta', 'ltp', 'instrument_key']])
            targets_sell = 0.4
            near_delta_sell = min(df['delta'].values, key = lambda x:abs(x- targets_sell))
            strike_sell = df.loc[df['delta']==near_delta_sell]
            targert_buy = 0.25
            near_delta_buy = min(df['delta'].values, key = lambda x:abs(x- targert_buy))
            strike_buy = df.loc[df['delta']==near_delta_buy]
            return  strike_buy, strike_sell
        elif side == 'put':
            df = (pd.concat([df,
                pd.json_normalize (df['put_options']),
                pd.json_normalize(df['put_options'].apply(lambda x: x['option_greeks'])),
                pd.json_normalize(df['put_options'].apply(lambda x: x['market_data']))], axis=1)
            .loc[:, ['expiry', 'strike_price', 'delta', 'ltp', 'instrument_key']])
            targets_sell = -0.4
            near_delta_sell = min(df['delta'].values, key = lambda x:abs(x- targets_sell))
            strike_sell = df.loc[df['delta']==near_delta_sell]
            target_buy = -0.25
            near_delta_buy = min(df['delta'].values, key = lambda x:abs(x- target_buy))
            strike_buy = df.loc[df['delta']==near_delta_buy]
            return  strike_buy, strike_sell

        
           
        else:
            raise ValueError("Invalid side. Choose 'call' or 'put'.")

        


if __name__ == "__main__":
    try:
        BCBSpread = BullCallBearSpread()
        buy , sell = BCBSpread.option_chain('call')

        print("\n[RESULT] Bull Call Spread Recommendation:")
        print("Sell Strike Price:", sell['strike_price'].values[0])
        print("Buy Strike Price :", buy['strike_price'].values[0])
        # print("Net Credit        :", round(sell['ltp'].values[0] - buy['ltp'].values[0], 2))
    except Exception as e:
        print(f"[ERROR] {e}")
