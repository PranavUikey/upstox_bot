import requests
import yaml
from option_chain import BullCallBearSpread
from config import AWSConfig  # Assuming you have a config.py with AWSConfig class

class Order:
    def __init__(self,quantity, transaction_type,):
        self.quantity = quantity
        self.transaction_type = transaction_type
        # Fetch access token from AWS SSM
        config = AWSConfig()
        self.token = config.get_parameter('/upstox/access_token')['Parameter']['Value']

    def order_place(self, instrument_token):

        if self.transaction_type == 'BUY':
            OptionCallBuy = 'BUY'
        elif self.transaction_type == 'SELL':
            OptionCallBuy = 'SELL'
        else:
            raise ValueError("Invalid transaction type. Use 'BUY' or 'SELL'.")
        


        url = 'https://api.upstox.com/v2/order/place'
        headers = {'Accept': 'application/json','Api-Version': '2.0',
                   'Content-Type': 'application/json','Authorization': f'Bearer {self.token}' }
        
        order_data = {'quantity': self.quantity,'product': 'D', 'validity': 'DAY','price': 0, 
                      'tag': OptionCallBuy,'instrument_token': instrument_token,
                      'order_type': 'MARKET','transaction_type': self.transaction_type, 'disclosed_quantity': 0, 
                      'trigger_price': 0,'is_amo': False}
        
        response = requests.post(url, json=order_data, headers=headers)
        print('Status Code:', response.status_code)
        return 'Response:', response.json()
    

BCBSpread = BullCallBearSpread()

output = BCBSpread.option_chain('call')

buy_call = output[0]
sell_call = output[1]


sell_strike = sell_call['strike_price'].values[0]
buy_strike = buy_call['strike_price'].values[0]

sell_instrument_token = sell_call['instrument_key'].values[0]
buy_instrument_token = buy_call['instrument_key'].values[0]

# Place sell order
sell_order = Order(75, 'SELL')
sell_response = sell_order.order_place(sell_instrument_token)
# Place buy order
buy_order = Order(75, 'BUY')
buy_response = buy_order.order_place( buy_instrument_token)
print("Sell Order Response:", sell_response)    
print("Buy Order Response:", buy_response)
# Print the strike prices
print("Sell Strike:", sell_strike)  
print("Buy Strike:", buy_strike)