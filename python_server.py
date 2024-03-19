import requests
import math
import websocket
import json


with open('config.json') as file:
    config = json.load(file)


def on_open(ws):
    print('connected')
    auth_msg = {
        "action": "auth",
        "key":config["APCA_API_KEY_ID"],
        "secret": config["APCA_API_SECRET_KEY"]
    }
    ws.send(json.dumps(auth_msg))

    subscribe_msg = {
        "action": "subscribe",
        "news": ["*"]
    }
    ws.send(json.dumps(subscribe_msg))

def getAccountBalance():
    balance_response = requests.get(
            url="https://paper-api.alpaca.markets/v2/account",
            headers= {
                'APCA-API-KEY-ID': config["APCA_API_KEY_ID"],
                'APCA-API-SECRET-KEY': config["APCA_API_SECRET_KEY"]
            })

    print("Getting account balance: ")
    print(balance_response.json())
    balance = float(balance_response.json()['cash'])
    print(balance);  
    return balance

  
def ask_gpt(summary):
    company_impact = 0  #init to 0

    # Ask GPT its thoughts
    apiRequestBody = {
        "model": "gpt-4-turbo-preview",
        "messages": [
            {"role": "system", "content": "Only respond with a number rating from 1 to 100 how much impact this news might have on the stock's price in the next few days, with 1 being an absolute sell and 100 being a definite buy. If the event is a news summary of a company's growth and not new news, give a neutral score of 50."},
            {"role": "user", "content": f"Given the summary '{summary}', give only a number from 1-100 detailing the impact of this summary."}
        ]
    }
    print("AI fetch init")
    gpt_response = requests.post(
        url="https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": "Bearer " + config["OPENAI_API_KEY"],
            "Content-Type": "application/json",
        },
        json=apiRequestBody)

    print("GPT response:")
    print(gpt_response)

    # Check if the response was successful
    if gpt_response.status_code == 200:
        gpt_response_json = gpt_response.json()  # Use .json() method directly
        company_impact = int(gpt_response_json['choices'][0]['message']['content'].strip())  # Adjust according to the actual key
        print("Estimated company_impact:", company_impact)
    else:
        print("Failed to fetch response, status code:", gpt_response.status_code)

    return company_impact
    

def getLatestTrade(ticker_symbol):
    price_response = requests.get(
        url=f"https://data.alpaca.markets/v2/stocks/{ticker_symbol}/trades/latest",
        headers= {
            'APCA-API-KEY-ID': config["APCA_API_KEY_ID"],
            'APCA-API-SECRET-KEY': config["APCA_API_SECRET_KEY"]
        })

    print("Latest trade response: for " + ticker_symbol)
    print(price_response.json())
    price = float(price_response.json()['trade']['p'])
    print(price);  
    return price

def placeOrder(buy_sell, ticker_symbol, quantity, currentPrice):
    print("placing order for " + ticker_symbol)

    if buy_sell == "buy":
        stop_loss_decimal = round(currentPrice * 0.98, 2)
        stop_profit_decimal = round(currentPrice * 1.06, 2)
    elif buy_sell == "sell":
        stop_loss_decimal = round(currentPrice * 1.02, 2)
        stop_profit_decimal = round(currentPrice * 0.94, 2)
    else:
        print("invalid buy_sell value")
        return

    orderData = {
        "symbol": ticker_symbol,
        "qty": quantity,
        "side": buy_sell,
        "type": "market",
        "time_in_force": "gtc",
        "order_class": 'bracket',
        "stop_loss": {
            "stop_price": stop_loss_decimal,
        },
        "take_profit":{
            "limit_price": stop_profit_decimal
        }}
        
    order_post = requests.post(
        url="https://paper-api.alpaca.markets/v2/orders",
        headers= {
        'APCA-API-KEY-ID': config["APCA_API_KEY_ID"],
        'APCA-API-SECRET-KEY': config["APCA_API_SECRET_KEY"],
        'Content-Type': 'application/json'},
        json=orderData)
    
    if order_post.status_code == 200:
        print(order_post.json())
        print("order posted for " + ticker_symbol + " with a stop loss at " + str(stop_loss_decimal) + " and a take profit at " + str(stop_profit_decimal) + " at price " + str(currentPrice) + " and a quantity of " + str(quantity) + " shares.")
    else:
        print("Failed to place order, status code:", order_post.status_code)
        print(order_post.json())



def is_news_event(currentEvent):
    if currentEvent[0]["T"] == "n":
        if currentEvent[0]["summary"] != '':
            print("News event detected:\n", currentEvent)
            return True
        else:
            print("No summary found")
            return False
    else:
        print("Non news event")
        return False
            

def on_message(ws, message):
    print('Received message:')


    currentEvent = json.loads(message)
    if is_news_event(currentEvent):
            print("Summary:")
            summary = currentEvent[0]['summary']
            print(summary)

            company_impact = ask_gpt(summary)
            print("Company Impact:")
            print(company_impact)

            ticker_symbol = currentEvent[0]['symbols'][0]
            print("Ticker Symbol:")
            print(ticker_symbol)

            if company_impact >= 70:                                            #buy order
                currentPrice = getLatestTrade(ticker_symbol)                    
                balance = getAccountBalance()
                print("Balance: ", balance)
                quantity = max(math.floor(balance / currentPrice * 0.1), 1)     #around 10% of portfolio

                placeOrder("buy", ticker_symbol, quantity, currentPrice)

            if company_impact <= 30:                                            #sell order
                currentPrice = getLatestTrade(ticker_symbol)
                balance = getAccountBalance()
                quantity = max(math.floor(balance / currentPrice * 0.1), 1)     #around 10% of portfolio

                placeOrder("sell", ticker_symbol, quantity, currentPrice)        

def on_error(ws, error):
    print('Error:')
    print(error)

def on_close(ws, close_status_code, close_msg):
    print('### closed ###')


websocket.enableTrace(True)
ws_url = 'wss://stream.data.alpaca.markets/v1beta1/news' 
ws = websocket.WebSocketApp(ws_url,
                            on_open=on_open,
                            on_message=on_message,
                            on_error=on_error,
                            on_close=on_close)

ws.run_forever() 