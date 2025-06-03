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
        self.expiry_date = expiry_dates.expiry_date()[0]

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

        df = pd.DataFrame(data)

        if side == 'call':
            df_expanded = df['call_options'].apply(pd.Series)
            target_sell = 0.4
            target_buy = 0.25
        elif side == 'put':
            df_expanded = df['put_options'].apply(pd.Series)
            target_sell = -0.4
            target_buy = -0.25
        else:
            raise ValueError("Invalid side. Choose 'call' or 'put'.")

        market_data_expanded = df_expanded['market_data'].apply(pd.Series)
        option_greeks = df_expanded['option_greeks'].apply(pd.Series)

        final_df = pd.concat([df, option_greeks, market_data_expanded, df_expanded], axis=1)
        final_df = final_df.loc[:, ['expiry', 'strike_price', 'delta', 'ltp', 'instrument_key']]

        # Filter based on strike price
        if side == 'call':
            filtered = final_df[final_df['strike_price'] > self.nifty_close]
        else:
            filtered = final_df[final_df['strike_price'] <= self.nifty_close]

        # Drop rows with missing delta
        filtered = filtered.dropna(subset=['delta'])

        if filtered.empty:
            raise Exception("No valid option data available after filtering for delta.")

        # Find closest delta values
        sell_delta = min(filtered['delta'], key=lambda x: abs(x - target_sell))
        buy_delta = min(filtered['delta'], key=lambda x: abs(x - target_buy))

        sell_strike = filtered[filtered['delta'] == sell_delta]
        buy_strike = filtered[filtered['delta'] == buy_delta]

        return sell_strike, buy_strike, sell_delta, buy_delta


if __name__ == "__main__":
    try:
        BCBSpread = BullCallBearSpread()
        sell, buy,sell_del, buy_del = BCBSpread.option_chain('call')

        print("\n[RESULT] Bull Call Spread Recommendation:")
        print("Sell Strike Price:", sell['strike_price'].values[0], 'Delta:', round(sell_del, 2))
        print("Buy Strike Price :", buy['strike_price'].values[0], 'Delta:', round(buy_del, 2))
        print("Net Credit        :", round(sell['ltp'].values[0] - buy['ltp'].values[0], 2))
    except Exception as e:
        print(f"[ERROR] {e}")
