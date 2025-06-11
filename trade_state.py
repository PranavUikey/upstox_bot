import boto3
import json
from datetime import datetime
import pytz
import logging
from expiry_fetcher import FetchExpiryDates

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




class TradeState:
    def __init__(self, bucket_name="upstox-trade-state-287191041687", key="trade_state.json"):
        self.bucket = bucket_name
        self.key = key
        self.s3 = boto3.client("s3")
        self.ses = boto3.client('ses', region_name='ap-south-1')
        self._ensure_file()

    def _today(self):
        return datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d")

    def _ensure_file(self):
        try:
            self.s3.head_object(Bucket=self.bucket, Key=self.key)
            logger.info(f"State file '{self.key}' exists in bucket '{self.bucket}'.")
        except self.s3.exceptions.NoSuchKey:
            logger.warning("State file not found (NoSuchKey). Creating a new one.")
            expiry_fetcher = FetchExpiryDates()
            expiry_list = expiry_fetcher.expiry_date()
            expiry_date = expiry_list[1] if len(expiry_list) > 1 else expiry_list[0]
            self.save_state({
                "call_trade": 0,
                "put_trade": 0,
                "expiry_date": expiry_date
            })
        except self.s3.exceptions.ClientError as e:
            error_code = e.response['Error'].get('Code')
            if error_code == '404':
                logger.warning("State file not found (404). Creating a new one.")
                expiry_fetcher = FetchExpiryDates()
                expiry_list = expiry_fetcher.expiry_date()
                expiry_date = expiry_list[1] if len(expiry_list) > 1 else expiry_list[0]
                self.save_state({
                    "call_trade": 0,
                    "put_trade": 0,
                    "expiry_date": expiry_date
            })
            else:
                logger.error("Unhandled error checking S3 file: %s", str(e))
                raise
        except Exception as e:
            logger.error("Unexpected error: %s", str(e))
            raise


    def load_state(self):
        logger.info("Loading state from S3.")
        obj = self.s3.get_object(Bucket=self.bucket, Key=self.key)
        state = json.loads(obj['Body'].read().decode("utf-8"))
        logger.info("Loaded state: %s", state)
        return state

    def save_state(self, state):
        logger.info("Saving state to S3: %s", state)
        self.s3.put_object(
            Bucket=self.bucket,
            Key=self.key,
            Body=json.dumps(state),
            ContentType='application/json'
        )
        

    def get_state(self):
        state = self.load_state()
        return state


    def update_trade_flags(self, call_trade, put_trade):
        logger.info(f"Updating trade flags: call={call_trade}, put={put_trade}")
        state = self.load_state()
        state.update({
            "call_trade": call_trade,
            "put_trade": put_trade,
        })
        self.save_state(state)

    def send_trade_email(self, subject, message_body, to_email, from_email):
        """
        Send a confirmation email using AWS SES.
        Make sure 'from_email' and 'to_email' are verified in SES (unless SES is out of sandbox).
        """
        try:
            response = self.ses.send_email(
                Source=from_email,
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Data": subject},
                    "Body": {"Text": {"Data": message_body}}
                }
            )
            logger.info(f"Trade email sent to {to_email}. Message ID: {response['MessageId']}")
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
