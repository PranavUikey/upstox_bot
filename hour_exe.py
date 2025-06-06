from ohlc_fetcher import FetchOHLC
from option_chain import BullCallBearSpread
from expiry_fetcher import FetchExpiryDates
from order_exe import Order
import numpy as np
from position_fetcher import PositionFetcher
import pytz
from datetime import datetime

class HourlyExecution:
    def __init__(self):
        self.end_off_data = []
        self.all_trade_execution = []
        self.call_trade = 0
        self.put_trade = 0

        ohlc_data = FetchOHLC()
        self.last_line = ohlc_data.all_days_ohlc().tail(1)
        print(f"Last OHLC Data: {self.last_line}")

        expiryDate = FetchExpiryDates()
        self.expiry = expiryDate.expiry_date()[1]

        BullCallBear = BullCallBearSpread()
        self.call_option = BullCallBear.option_chain('call')
        self.put_option = BullCallBear.option_chain('put')

    def run(self):
        now = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y-%m-%d %H:%M:%S")
        ll = self.last_line

        cond_call = (ll['close'].values[0] < ll['EMA_20'].values[0] and
                     ll['supertrend'].values[0] == -1 and
                     ll['close'].values[0] < ll['open'].values[0])
        cond_put = (ll['close'].values[0] > ll['EMA_20'].values[0] and
                    ll['supertrend'].values[0] == 1 and
                    ll['close'].values[0] > ll['open'].values[0])

        expiry_time = self.expiry + ' 03:00:00' if isinstance(self.expiry, str) else ''
        if self.call_trade and expiry_time >= now:
            self._exit_trade('call', now)
            self.call_trade = 0
        elif self.put_trade and expiry_time >= now:
            self._exit_trade('put', now)
            self.put_trade = 0

        if now >= datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y-%m-%d") + ' 15:30:00':
            pos = PositionFetcher().get_positions()['data']
            self.end_off_data.append(pos)

        if cond_call and not self.call_trade and not self.put_trade:
            self._enter_trade('call', now)
            self.call_trade = 1
        elif cond_put and not self.put_trade and not self.call_trade:
            self._enter_trade('put', now)
            self.put_trade = 1
        elif self.call_trade and ll['supertrend'].values[0] == 1:
            self._exit_trade('call', now)
            self.call_trade = 0
        elif self.put_trade and ll['supertrend'].values[0] == -1:
            self._exit_trade('put', now)
            self.put_trade = 0

    def _enter_trade(self, typ, now):
        opt = self.call_option if typ == 'call' else self.put_option
        self.order_conf = Order(75, 'BUY')
        self.order_conf.order_place(opt[0]['instrument_key'].values[0])

        self.order_conf = Order(75, 'SELL')
        self.order_conf.order_place(opt[1]['instrument_key'].values[0])
        self.all_trade_execution.append(np.append(opt[0].values, [now, 'BUY']))
        self.all_trade_execution.append(np.append(opt[1].values, [now, 'SELL']))

    def _exit_trade(self, typ, now):
        opt = self.call_option if typ == 'call' else self.put_option
        self.order_conf = Order(75, 'SELL')
        self.order_conf.order_place(opt[0]['instrument_key'].values[0])

        self.order_conf = Order(75, 'BUY')
        self.order_conf.order_place(opt[1]['instrument_key'].values[0])
        self.all_trade_execution.append(np.append(opt[0].values, [now, 'SELL']))
        self.all_trade_execution.append(np.append(opt[1].values, [now, 'BUY']))


exe = HourlyExecution()
exe.run()