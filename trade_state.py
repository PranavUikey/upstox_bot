import boto3
import json
from datetime import datetime
import pytz

class TradeState:
    def __init__(self, bucket_name="upstox-trade-state-287191041687", key="trade_state.json"):
        self.bucket = bucket_name
        self.key = key
        self.s3 = boto3.client("s3")
        self._today = datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d")
        self._ensure_file()

    def _ensure_file(self):
        try:
            self.s3.head_object(Bucket=self.bucket, Key=self.key)
        except self.s3.exceptions.ClientError:
            self.save_state({"call_trade": 0, "put_trade": 0, "last_reset_date": self._today})

    def load_state(self):
        obj = self.s3.get_object(Bucket=self.bucket, Key=self.key)
        return json.loads(obj['Body'].read().decode("utf-8"))

    def save_state(self, state):
        self.s3.put_object(
            Bucket=self.bucket,
            Key=self.key,
            Body=json.dumps(state),
            ContentType='application/json'
        )

    def get_state(self):
        state = self.load_state()
        if state.get("last_reset_date") != self._today:
            state = {"call_trade": 0, "put_trade": 0, "last_reset_date": self._today}
            self.save_state(state)
        return state

    def update_trade_flags(self, call_trade, put_trade):
        state = self.get_state()
        state.update({
            "call_trade": call_trade,
            "put_trade": put_trade,
            "last_reset_date": self._today
        })
        self.save_state(state)
