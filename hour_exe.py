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

    def _append_to_s3_csv(self, data, columns, s3_key="all_trade_execution.csv"):
        s3 = boto3.client('s3')
        bucket = "upstox-trade-state-287191041687"
        try:
            obj = s3.get_object(Bucket=bucket, Key=s3_key)
            existing_df = pd.read_csv(io.BytesIO(obj['Body'].read()))
        except s3.exceptions.NoSuchKey:
            existing_df = pd.DataFrame(columns=columns)

        new_df = pd.DataFrame([data], columns=columns)
        result_df = pd.concat([existing_df, new_df], ignore_index=True)

        csv_buffer = io.StringIO()
        result_df.to_csv(csv_buffer, index=False)
        s3.put_object(Bucket=bucket, Key=s3_key, Body=csv_buffer.getvalue())

    def record_trade_execution(self, trade_data):
        columns = ["expiry_date", "strike_price", "delta", "ltp", "instrument_token", "timestamp", "action"]
        self._append_to_s3_csv(trade_data, columns, "all_trade_execution.csv")

    def record_end_of_day(self, eod_data, date):
        self._append_to_s3_csv(eod_data, list(range(0,len(eod_data))), f"end_of_day_{date}.csv")

    def run(self):
        now = datetime.now(pytz.timezone('Asia/Kolkata'))
        ll = self.last_line

        logger.info(f"Running trade execution at {now}")

        cond_call = (ll['close'].values[0] < ll['EMA_20'].values[0] and
                    ll['supertrend'].values[0] == -1 and
                    ll['close'].values[0] < ll['open'].values[0])
        cond_put = (ll['close'].values[0] > ll['EMA_20'].values[0] and
                    ll['supertrend'].values[0] == 1 and
                    ll['close'].values[0] > ll['open'].values[0])

        tz = pytz.timezone("Asia/Kolkata")
        expiry_time = (
            tz.localize(datetime.strptime(self.expiry + ' 15:00:00', "%Y-%m-%d %H:%M:%S"))
            if isinstance(self.expiry, str)
            else None
        )

        # --- Expiry exit logic ---
        if self.call_trade == 1 and expiry_time and expiry_time <= now:
            logger.info("Exiting CALL trade due to expiry.")
            self._exit_trade('call', now)
            self.call_trade = 0

        if self.put_trade == 1 and expiry_time and expiry_time <= now:
            logger.info("Exiting PUT trade due to expiry.")
            self._exit_trade('put', now)
            self.put_trade = 0

        # --- End of day capture ---
        eod_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
        if now >= eod_time:
            logger.info("Recording end-of-day positions.")
            try:
                pos = PositionFetcher().get_positions()['data'][0]
            except Exception as e:
                pos = PositionFetcher().get_positions()['data']
            self.record_end_of_day(pos, now.strftime("%Y-%m-%d_%H-%M-%S"))

        # --- Entry logic ---
        if cond_call and self.call_trade == 0 and self.put_trade == 0:
            logger.info("Entering CALL trade.")
            self._enter_trade('call', now)
            self.call_trade = 1

        elif cond_put and self.call_trade == 0 and self.put_trade == 0:
            logger.info("Entering PUT trade.")
            self._enter_trade('put', now)
            self.put_trade = 1

        # --- Stoploss/Trailing SL logic ---
        elif self.call_trade == 1 and ll['supertrend'].values[0] == 1:
            logger.info("Exiting CALL trade due to stoploss/trailing SL.")
            self._exit_trade('call', now)
            self.call_trade = 0

        elif self.put_trade == 1 and ll['supertrend'].values[0] == -1:
            logger.info("Exiting PUT trade due to stoploss/trailing SL.")
            self._exit_trade('put', now)
            self.put_trade = 0

        self.state_mgr.update_trade_flags(self.call_trade, self.put_trade)
        logger.info("Updated trade flags and saved state.")

        

    def _enter_trade(self, typ, now):
        logger.info(f"Placing {typ.upper()} entry orders at {now}")
        opt = self.call_option if typ == 'call' else self.put_option

        buy_token = opt[0]['instrument_key'].values[0]
        sell_token = opt[1]['instrument_key'].values[0]

        self.order_conf = Order(75, 'BUY')
        self.order_conf.order_place(buy_token)
        logger.info(f"BUY order placed for: {buy_token}")
        self.record_trade_execution(np.append(opt[0].values, [now, 'BUY']))

        self.order_conf = Order(75, 'SELL')
        self.order_conf.order_place(sell_token)
        logger.info(f"SELL order placed for: {sell_token}")
        self.record_trade_execution(np.append(opt[1].values, [now, 'SELL']))

        # Save the tokens in state for exit
        state = self.state_mgr.get_state()
        if typ == 'call':
            state['call_entry_tokens'] = [buy_token, sell_token]
        else:
            state['put_entry_tokens'] = [buy_token, sell_token]
        self.state_mgr.save_state(state)

        subject = f"{typ.upper()} Trade Entry Executed"
        body = (
            f"A {typ.upper()} trade has been entered at {now}.\n"
            f"BUY: {buy_token}\n"
            f"SELL: {sell_token}"
        )
        self.state_mgr.send_trade_email(subject, body, "snehadeep.sb@gmail.com", "pranavuiih@gmail.com")

    def _exit_trade(self, typ, now):
        logger.info(f"Placing {typ.upper()} exit orders at {now}")

        state = self.state_mgr.get_state()
        if typ == 'call':
            tokens = state.get('call_entry_tokens', [])
        else:
            tokens = state.get('put_entry_tokens', [])

        if len(tokens) != 2:
            logger.error(f"No entry tokens found for {typ.upper()} trade exit!")
            return

        # Exit in reverse: sell what was bought, buy what was sold
        self.order_conf = Order(75, 'SELL')
        self.order_conf.order_place(tokens[0])
        logger.info(f"SELL order placed for: {tokens[0]}")
        self.record_trade_execution([tokens[0], now, 'SELL'])

        self.order_conf = Order(75, 'BUY')
        self.order_conf.order_place(tokens[1])
        logger.info(f"BUY order placed for: {tokens[1]}")
        self.record_trade_execution([tokens[1], now, 'BUY'])

        # Remove tokens from state after exit
        if typ == 'call':
            state['call_entry_tokens'] = []
        else:
            state['put_entry_tokens'] = []
        self.state_mgr.save_state(state)

        subject = f"{typ.upper()} Trade Exit Executed"
        body = (
            f"A {typ.upper()} trade has been exited at {now}.\n"
            f"SELL: {tokens[0]}\n"
            f"BUY: {tokens[1]}"
        )
        self.state_mgr.send_trade_email(subject, body, "snehadeep.sb@gmail.com", "pranavuiih@gmail.com")


if __name__ == "__main__":
    exe = HourlyExecution()
    exe.run()
