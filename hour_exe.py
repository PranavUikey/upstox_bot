from ohlc_fetcher import FetchOHLC
from option_chain import BullCallBearSpread
from expiry_fetcher import FetchExpiryDates
from order_exe import Order
import numpy as np
from position_fetcher import PositionFetcher
from config import AWSConfig
import pandas as pd
import pytz
from datetime import datetime


end_off_data = []
all_trade_execution  = []

ohlc_data = FetchOHLC()
last_line = ohlc_data.all_days_ohlc().tail(1)

print(f"Last OHLC Data: {last_line}")

expiryDate = FetchExpiryDates()
expiry = expiryDate.expiry_date()[1]

BullCallBear = BullCallBearSpread()
call_option = BullCallBear.option_chain('call')   
put_option = BullCallBear.option_chain('put')

order_conf = Order()
# order = order_conf.order_place(75 , )

current_time = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y-%m-%d %H:%M:%S")

condition_call = ((last_line['close'].values[0]<last_line['EMA_20'].values[0])and  
                  (last_line['supertrend'].values[0] == -1) and 
                  (last_line['close'].values[0]< last_line['open'].values[0]))

condition_put = ((last_line['close'].values[0]>last_line['EMA_20'].values[0])and  
                 (last_line['supertrend'].values[0] == 1) and
                   (last_line['close'].values[0]> last_line['open'].values[0]))

call_trade = 0
put_trade = 0
if isinstance(expiry , str): #end of expiry condition
    if call_trade ==1 and  expiry + ' 03:00:00'>= current_time:
        order_conf.order_place(75 ,'SELL' , call_option[0]['instrument_key'].values[0])
        order_conf.order_place(75 ,'BUY' , call_option[1]['instrument_key'].values[0])        
        all_trade_execution.append(np.append(call_option[0].values , [current_time , 'SELL']))
        all_trade_execution.append(np.append(call_option[1].values , [current_time , 'BUY']))
        call_trade=0
    elif put_trade ==1 and  expiry + ' 03:00:00'>= current_time:
        order_conf.order_place(75 ,'SELL' , put_option[0]['instrument_key'].values[0])
        order_conf.order_place(75 ,'BUY' , put_option[1]['instrument_key'].values[0])
        all_trade_execution.append(np.append(put_option[0].values , [current_time , 'SELL']))
        all_trade_execution.append(np.append(put_option[1].values , [current_time , 'BUY']))
        put_trade=0
if current_time >= (datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y-%m-%d")+' 15:30:00'): # every day pnl added
    pos = PositionFetcher()
    # get_positions = pos.get_positions()
    position_end_of_day  = pos.get_positions()['data']
    end_off_data.append(position_end_of_day)

if condition_call  and call_trade == 0 and put_trade ==0: # all condition for call option

        order_conf.order_place(75 ,'BUY' , call_option[0]['instrument_key'].values[0])
        order_conf.order_place(75 ,'SELL' , call_option[1]['instrument_key'].values[0])
        

        print(call_option[1]['instrument_key'].values[0], call_option[0]['instrument_key'].values[0])
     

        all_trade_execution.append(np.append(call_option[0].values , [current_time , 'BUY']))
        all_trade_execution.append(np.append(call_option[1].values , [current_time , 'SELL']))
        call_trade = 1
if condition_put and put_trade == 0  and call_trade==0 :
    order_conf.order_place(75 ,'BUY' , put_option[0]['instrument_key'].values[0])
    order_conf.order_place(75 ,'SELL' , put_option[1]['instrument_key'].values[0])

    all_trade_execution.append(np.append(put_option[0].values , [current_time , 'BUY']))
    all_trade_execution.append(np.append(put_option[1].values , [current_time , 'SELL']))


    put_trade= 1

elif call_trade ==1 : # sl and traling sl call
    if last_line['supertrend'].values[0] ==1:
        order_conf.order_place(75 ,'SELL' , call_option[0]['instrument_key'].values[0])
        order_conf.order_place(75 ,'BUY' , call_option[1]['instrument_key'].values[0])
    # current_time = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y-%m-%d %H:%M:%S")
        all_trade_execution.append(np.append(call_option[0].values ,[ current_time , 'SELL']))
        all_trade_execution.append(np.append(call_option[1].values ,[ current_time , 'BUY']))

        call_trade =0

elif put_trade==1 : # sl for put tarde
      if last_line['supertrend'].values[0] ==-1:
        order_conf.order_place(75 ,'SELL' , put_option[0]['instrument_key'].values[0])
        order_conf.order_place(75 ,'BUY' , put_option[1]['instrument_key'].values[0])

        all_trade_execution.append(np.append(put_option[0].values , [current_time , 'SELL']))
        all_trade_execution.append(np.append(call_option[1].values ,[ current_time , 'BUY']))

        put_trade =0