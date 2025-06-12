import requests
import boto3

from config import AWSConfig  # Assuming you have a config.py with AWSConfig class
config = AWSConfig()
token = config.get_parameter('/upstox/access_token')['Parameter']['Value']

class PositionFetcher:

    def get_positions(self ):
        url = f"https://api.upstox.com/v2/portfolio/short-term-positions"
        # print(url)
        headers = {
            'Authorization': f'Bearer {token}' ,  'Accept': 'application/json'
        }
        response = requests.get( url, headers=headers)
        print(response.status_code)
        print(response.text)
        if response.status_code == 200:
            return response.json()
        else:
            print("Error fetching positions:", response.text)
            return None

# pos_fet = PositionFetcher()
# position = pos_fet.get_positions()
# print(position)