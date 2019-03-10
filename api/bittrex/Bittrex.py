#  This file is part of Bittbot.
#
#  Bittbot is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Bittbot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Bittbot. If not, see <https://www.gnu.org/licenses/>.

import time
from datetime import datetime
from typing import List

from api.bittrex.BittrexLib import BittrexLib
from api.bittrex.BittrexWebsocketAPI import BittrexWebsocketAPI
from domain.CoinMarketData import CoinMarketData
from domain.TickerData import TickerData
from utils.LoggingUtils import LoggingUtils
import requests


class Bittrex(object):
    def __init__(self, api_key, secret):
        self.api_key = api_key
        self.secret = secret
        self.api = BittrexLib(api_key, secret)  # type: BittrexLib
        self.websocket = None
        self.api_ws_ticker_callback = None
        self.logger = LoggingUtils()
        self.logger.logging_info("Selected Bittrex Exchange")

    def subscribe_websocket(self, callback):
        self.api_ws_ticker_callback = callback
        self.websocket = BittrexWebsocketAPI(self.process_websocket_ticker, self.api)

    def get_full_ticker(self) -> List[TickerData]:
        while True:
            try:
                ticker = self.api.get_market_summaries()
                return self.parse_raw_ticker(ticker)
            except Exception:
                self.logger.logging_bittbot_error('EJECUTAR LEER TICKER', 10)

    def get_balance(self, currency_pair):
        while True:
            try:
                cc = currency_pair.split('_')
                if len(cc) == 1:
                    coin = cc[0]
                else:
                    coin = cc[1]
                balance = self.api.get_balance(coin)
                return self.parse_balance(balance)
            except Exception:
                self.logger.logging_bittbot_error('LEER BALANCE {}'.format(currency_pair), 10)

    def get_full_balance(self):
        while True:
            try:
                balances = self.api.get_balances()
                return self.parse_balances(balances)
            except Exception:
                self.logger.logging_bittbot_error('LEER BALANCE FULL', 10)

    def order_buy(self, currency_pair, buy_price, invest_balance):
        try:
            currency = currency_pair.replace("_", "-")
            make_order_buy = self.api.buy_limit(currency, invest_balance / buy_price, buy_price)
            order_id = self.parse_order_buy_sell(make_order_buy)
            if order_id is not None:
                return order_id, buy_price
            else:
                self.logger.logging_bittbot_error("CREAR ORDEN DE COMPRA PARA {}, Motivo: {}".format(currency_pair, make_order_buy["message"]))
                return None, 0.0
        except Exception:
            self.logger.logging_bittbot_error("CREAR ORDEN DE COMPRA PARA {}".format(currency_pair))
            return None, 0.0

    def order_sell(self, currency_pair, sell_price, invest_balance):
        try:
            currency = currency_pair.replace("_", "-")
            make_order_sell = self.api.sell_limit(currency, invest_balance, sell_price)
            order_id = self.parse_order_buy_sell(make_order_sell)
            if order_id is not None:
                return order_id
            else:
                self.logger.logging_bittbot_error("CREAR ORDEN DE VENTA PARA {}, Motivo: {}".format(currency_pair, make_order_sell["message"]))
                return None
        except Exception:
            self.logger.logging_bittbot_error("CREAR ORDEN DE VENTA PARA {}".format(currency_pair))
            return None

    def order_cancel(self, close_order_id):
        try:
            close_result = self.api.cancel(close_order_id)
            if close_result["success"]:
                return True
            return False
        except Exception:
            self.logger.logging_bittbot_error('CANCELAR ORDEN {}'.format(close_order_id))
            return False

    def get_order(self, order_id):
        try:
            order = self.api.get_order(order_id)
            if order["success"]:
                return order["result"]
        except Exception:
            self.logger.logging_bittbot_error('GET ORDEN {}'.format(order_id))
            return None

    def order_move(self, close_order_id, lowest_ask, operation_type):
        try:
            order_info = self.get_order(close_order_id)
            if order_info is not None:
                success = self.order_cancel(close_order_id)
                if success:
                    currency_pair = order_info["Exchange"]
                    if order_info["Type"] == "LIMIT_BUY":
                        old_price = float(order_info["Limit"])
                        invest_balance = float(order_info["Reserved"])
                        order_num, price = self.order_buy(currency_pair, lowest_ask, invest_balance)
                        return order_num
                    else:
                        invest_balance = order_info["QuantityRemaining"]
                        return self.order_sell(currency_pair, lowest_ask, invest_balance)
        except Exception:
            self.logger.logging_bittbot_error('MOVE ORDER {}'.format(close_order_id))

    def open_orders(self, currency_pair, num_last_order):
        while True:
            try:
                currency = currency_pair.replace("_", "-")
                open_orders = self.api.get_open_orders(currency)
                if open_orders["success"]:
                    for order in open_orders["result"]:
                        if order["OrderUuid"] == num_last_order:
                            return True
                    return False
            except Exception:
                self.logger.logging_bittbot_error('LEER LAS ORDENES ABIERTAS', 10)

    def exist_trade_order(self, coin, n_order):
        currency = coin.replace("_", "-")
        order = self.get_order(n_order)
        if order is None:
            return False
        if order["Exchange"] == currency and not order["IsOpen"]:
            return True
        return False

    def get_order_history(self):
        return self.api.get_order_history()

    def all_open_orders(self):
        while True:
            try:
                open_orders = self.api.get_all_open_orders()
                if open_orders["success"]:
                    return open_orders["result"]
            except Exception:
                self.logger.logging_bittbot_error('LEER LAS ORDENES ABIERTAS', 10)

    def get_historic_values_fifteen_min(self, coin, max_lasts) -> CoinMarketData:
        currency = coin.replace("_", "-")
        request_url = "https://bittrex.com/Api/v2.0/pub/market/GetTicks?marketName={}&tickInterval=fiveMin".format(currency)
        success = False
        while not success:
            try:
                response = requests.get(request_url).json()
                success = True
            except Exception:
                self.logger.logging_info("El Exchange esta ocupado, reintentando en 2 segundos...")
                time.sleep(2)

        historic = CoinMarketData()
        if response["success"]:
            historic.alt_name = currency
            for historic_ticker in response["result"]:
                timestamp = datetime.strptime(historic_ticker["T"], "%Y-%m-%dT%H:%M:%S")
                if timestamp.minute in [15, 30, 45, 00]:
                    historic.open.append(historic_ticker["O"])
                    historic.high.append(historic_ticker["H"])
                    historic.low.append(historic_ticker["L"])
                    historic.close.append(historic_ticker["C"])
                    historic.volume.append(historic_ticker["BV"])
                    historic.timestamp.append(historic_ticker["T"])

        historic.open = historic.open[-max_lasts:]
        historic.high = historic.high[-max_lasts:]
        historic.low = historic.low[-max_lasts:]
        historic.close = historic.close[-max_lasts:]
        historic.volume = historic.volume[-max_lasts:]
        historic.timestamp = historic.timestamp[-max_lasts:]

        return historic

    def get_historic_values_five_min(self, coin, max_lasts) -> CoinMarketData:
        currency = coin.replace("_", "-")
        request_url = "https://bittrex.com/Api/v2.0/pub/market/GetTicks?marketName={}&tickInterval=fiveMin".format(currency)
        success = False
        while not success:
            try:
                response = requests.get(request_url).json()
                success = True
            except Exception:
                self.logger.logging_info("El Exchange esta ocupado, reintentando en 2 segundos...")
                time.sleep(2)

        historic = CoinMarketData()
        if response["success"]:
            historic.alt_name = currency
            for historic_ticker in response["result"]:
                historic.open.append(historic_ticker["O"])
                historic.high.append(historic_ticker["H"])
                historic.low.append(historic_ticker["L"])
                historic.close.append(historic_ticker["C"])
                historic.volume.append(historic_ticker["BV"])
                historic.timestamp.append(historic_ticker["T"])

        historic.open = historic.open[-max_lasts:]
        historic.high = historic.high[-max_lasts:]
        historic.low = historic.low[-max_lasts:]
        historic.close = historic.close[-max_lasts:]
        historic.volume = historic.volume[-max_lasts:]
        historic.timestamp = historic.timestamp[-max_lasts:]

        return historic

    def process_websocket_ticker(self, ticker_dict):
        ticker = []  # type: List[TickerData]
        for tickerAlt in ticker_dict['D']:
            ticker_data = TickerData()
            ticker_data.marketName = tickerAlt["M"].replace("-", "_")
            try:
                if tickerAlt["l"] == 0.0:
                    ticker_data.percentChange = -1000000
                else:
                    ticker_data.percentChange = (float(tickerAlt["l"]) - float(tickerAlt["PD"])) / float(tickerAlt["l"])
                ticker_data.high = float(tickerAlt["H"])
                ticker_data.low = float(tickerAlt["L"])
                ticker_data.volume = float(tickerAlt["V"])
                ticker_data.last = float(tickerAlt["l"])
                ticker_data.baseVolume = float(tickerAlt["m"])
                ticker_data.timeStamp = tickerAlt["T"]
                ticker_data.bid = float(tickerAlt["B"])
                ticker_data.ask = float(tickerAlt["A"])
                ticker_data.openBuyOrders = int(tickerAlt["G"])
                ticker_data.openSellOrders = int(tickerAlt["g"])
                ticker_data.prevDay = float(tickerAlt["PD"])
                ticker_data.created = tickerAlt["x"]
                ticker.append(ticker_data)
            except Exception:
                # self.logger.logging_warning("[{}] El Exchange ha respondido con un valor no válido para el ticker. Ignorando Alt Coin hasta nuevo ticker...".format(coin_name))
                pass

        self.api_ws_ticker_callback(ticker)

    #######################
    #   Bittrex Parsers   #
    #######################
    def parse_raw_ticker(self, bittrex_ticker) -> List[TickerData]:
        if bittrex_ticker["success"]:
            ticker = []  # type: List[TickerData]
            for tickerAlt in bittrex_ticker["result"]:
                ticker_data = TickerData()
                ticker_data.marketName = tickerAlt["MarketName"].replace("-", "_")
                try:
                    if tickerAlt["Last"] == 0.0:
                        ticker_data.percentChange = -1000000
                    else:
                        ticker_data.percentChange = (float(tickerAlt["Last"]) - float(tickerAlt["PrevDay"])) / float(tickerAlt["Last"])
                    ticker_data.high = float(tickerAlt["High"])
                    ticker_data.low = float(tickerAlt["Low"])
                    ticker_data.volume = float(tickerAlt["Volume"])
                    ticker_data.last = float(tickerAlt["Last"])
                    ticker_data.baseVolume = float(tickerAlt["BaseVolume"])
                    ticker_data.timeStamp = tickerAlt["TimeStamp"]
                    ticker_data.bid = float(tickerAlt["Bid"])
                    ticker_data.ask = float(tickerAlt["Ask"])
                    ticker_data.openBuyOrders = int(tickerAlt["OpenBuyOrders"])
                    ticker_data.openSellOrders = int(tickerAlt["OpenSellOrders"])
                    ticker_data.prevDay = float(tickerAlt["PrevDay"])
                    ticker_data.created = tickerAlt["Created"]
                    ticker.append(ticker_data)
                except Exception:
                    # self.logger.logging_warning("[{}] El Exchange ha respondido con un valor no válido para el ticker. Ignorando hasta nuevo ticker...".format(coin_name))
                    pass

            return ticker

    def parse_balance(self, bittrex_balance):
        if bittrex_balance["success"]:
            return float(bittrex_balance["result"]["Balance"])

    def parse_balances(self, bittrex_balances):
        if bittrex_balances["success"]:
            balances = {}
            for alt in bittrex_balances["result"]:
                balances[alt["Currency"]] = alt["Balance"]
            return balances

    def parse_order_buy_sell(self, bittrex_order_buy_sell):
        if bittrex_order_buy_sell["success"]:
            return bittrex_order_buy_sell['result']['uuid']
