import requests
import boto3
import pandas as pd

from config import AWSConfig



class FetchExpiryDates:
    def __init__(self, url="https://api.upstox.com/v2/option/contract", param_name='/upstox/access_token'):
        self.url = url
        aws_config = AWSConfig()
        self.access_token = aws_config.get_parameter('/upstox/access_token')['Parameter']['Value']
        self.client_id = aws_config.get_parameter('/upstox/client_id')['Parameter']['Value']
        self.redirect_uri = aws_config.get_parameter('/upstox/redirect_uri')['Parameter']['Value']
        self.client_secret = aws_config.get_parameter('/upstox/client_secret')['Parameter']['Value']


    def expiry_date(self):
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        params = {"instrument_key": "NSE_INDEX|Nifty 50"}
        response = requests.get(self.url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            contracts = data.get("data", [])
            expiry_dates = [contract["expiry"] for contract in contracts if "expiry" in contract]
            unique_expiry_dates = sorted(set(expiry_dates))
            return unique_expiry_dates
        else:
            return f"Error: {response.status_code} - {response.text}"

# # Run the script
# if __name__ == "__main__":
#     fetcher = FetchExpiryDates()
#     dates = fetcher.expiry_date()

#     print("Unique Expiry Dates for Nifty 50 Contracts:")
#     if isinstance(dates, list):
#         for date in dates:
#             print(date)
#     else:
#         print(dates)
