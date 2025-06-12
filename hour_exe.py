from ohlc_fetcher import FetchOHLC
from option_chain import BullCallBearSpread
from expiry_fetcher import FetchExpiryDates
from order_exe import Order
import numpy as np
from position_fetcher import PositionFetcher
from trade_state import TradeState
import pytz
from datetime import datetime
import logging
import boto3
import pandas as pd
import io

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("trade.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class HourlyExecution:
    def __init__(self):
        logger.info("Initializing HourlyExecution...")

        self.end_off_data = []
        self.all_trade_execution = []

        self.state_mgr = TradeState()
        state = self.state_mgr.get_state()
        self.call_trade = state["call_trade"]
        self.put_trade = state["put_trade"]
        logger.info(f"Current trade state - Call: {self.call_trade}, Put: {self.put_trade}")

        ohlc_data = FetchOHLC()
        self.last_line = ohlc_data.all_days_ohlc().tail(1)
        logger.info(f"Last OHLC Data: {self.last_line}")

        expiryDate = FetchExpiryDates()
        self.expiry = expiryDate.expiry_date()[1]
        logger.info(f"Expiry date selected: {self.expiry}")

        BullCallBear = BullCallBearSpread()
        self.call_option = BullCallBear.option_chain('call')
        self.put_option = BullCallBear.option_chain('put')
    

    def run(self):
        now = datetime.strptime(str(datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y-%m-%d %H:%M:%S")),"%Y-%m-%d %H:%M:%S")
        print(now)
        ll = self.last_line

        logger.info(f"Running trade execution at {now}")

        cond_call = (ll['close'].values[0] < ll['EMA_20'].values[0] and
                     ll['supertrend'].values[0] == -1 and
                     ll['close'].values[0] < ll['open'].values[0])
        
        cond_put = (ll['close'].values[0] > ll['EMA_20'].values[0] and
                    ll['supertrend'].values[0] == 1 and
                    ll['close'].values[0] > ll['open'].values[0])

        expiry_time = datetime.strptime(self.expiry + ' 03:00:00', "%Y-%m-%d %H:%M:%S") if isinstance(self.expiry, str) else None


        if cond_call and self.call_trade==0 and  self.put_trade == 0:
            logger.info("Entering CALL trade based on strategy.")
            self._enter_trade('call', now)
            self.call_trade = 1
        elif cond_put and  self.put_trade ==0 and self.call_trade == 0:
            logger.info("Entering PUT trade based on strategy.")
            self._enter_trade('put', now)
            self.put_trade = 1

        elif self.call_trade == 1 and ll['supertrend'].values[0] == 1:
            logger.info("Exiting CALL trade due to stop loss condition.")
            self._exit_trade('call', now)
            self.call_trade = 0
        elif self.put_trade == 1 and ll['supertrend'].values[0] == -1:
            logger.info("Exiting PUT trade due to stop loss condition.")
            self._exit_trade('put', now)
            self.put_trade = 0
        
        elif self.call_trade ==1 and expiry_time and expiry_time <= now:
            logger.info("Exiting CALL trade due to expiry condition.")
            self._exit_trade('call', now)
            self.call_trade = 0

        elif self.put_trade ==1 and expiry_time and expiry_time <= now:
            logger.info("Exiting PUT trade due to expiry condition.")
            self._exit_trade('put', now)
            self.put_trade = 0

        if now >= datetime.strptime(datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y-%m-%d") + ' 15:30:00', "%Y-%m-%d %H:%M:%S"):
            logger.info("Recording end-of-day positions.")
            pos = PositionFetcher().get_positions()['data']
            self.end_off_data.append(pos)
            print('End of Day Position Data:----> ', self.end_off_data)

        

        self.state_mgr.update_trade_flags(self.call_trade, self.put_trade)
        logger.info("Updated trade flags and saved state.")

    def _enter_trade(self, typ, now):
        logger.info(f"Placing {typ.upper()} entry orders at {now}")
        opt = self.call_option if typ == 'call' else self.put_option

        self.order_conf = Order(75, 'BUY')
        self.order_conf.order_place(opt[0]['instrument_key'].values[0])
        logger.info(f"BUY order placed for: {opt[0]['instrument_key'].values[0]}")

        self.order_conf = Order(75, 'SELL')
        self.order_conf.order_place(opt[1]['instrument_key'].values[0])
        logger.info(f"SELL order placed for: {opt[1]['instrument_key'].values[0]}")

        self.all_trade_execution.append(np.append(opt[0].values, [now, 'BUY']))
        

        self.all_trade_execution.append(np.append(opt[1].values, [now, 'SELL']))
        

        # ✅ Send Email Notification
        subject = f"{typ.upper()} Trade Entry Executed"
        body = (
            f"A {typ.upper()} trade has been entered at {now}.\n"
            f"BUY: {opt[0]['instrument_key'].values[0]}\n"
            f"SELL: {opt[1]['instrument_key'].values[0]}"
        )
        self.state_mgr.send_trade_email(
            subject=subject,
            message_body=body,
            to_email="snehadeep.sb@gmail.com",     # ⚠️ Change to your verified recipient
            from_email="pranavuiih@gmail.com"       # ⚠️ Must be verified in SES
        )

    def _exit_trade(self, typ, now):
        logger.info(f"Placing {typ.upper()} exit orders at {now}")
        opt = self.call_option if typ == 'call' else self.put_option

        self.order_conf = Order(75, 'SELL')
        self.order_conf.order_place(opt[0]['instrument_key'].values[0])
        logger.info(f"SELL order placed for: {opt[0]['instrument_key'].values[0]}")

        self.order_conf = Order(75, 'BUY')
        self.order_conf.order_place(opt[1]['instrument_key'].values[0])
        logger.info(f"BUY order placed for: {opt[1]['instrument_key'].values[0]}")

        self.all_trade_execution.append(np.append(opt[0].values, [now, 'SELL']))
        self.all_trade_execution.append(np.append(opt[1].values, [now, 'BUY']))

        # ✅ Send Email Notification
        subject = f"{typ.upper()} Trade Exit Executed"
        body = (
            f"A {typ.upper()} trade has been exited at {now}.\n"
            f"SELL: {opt[0]['instrument_key'].values[0]}\n"
            f"BUY: {opt[1]['instrument_key'].values[0]}"
        )
        self.state_mgr.send_trade_email(
            subject=subject,
            message_body=body,
            to_email="snehadeep.sb@gmail.com",     
            from_email="pranavuiih@gmail.com"
        )


if __name__ == "__main__":
    exe = HourlyExecution()
    exe.run()
    print('end_off_data',exe.end_off_data)
    print('All_trade_BUY_execution_list:----> ',exe.all_trade_execution)
