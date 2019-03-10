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

import hmac
import json
import time
import datetime

from hashlib import sha512
from typing import List
from urllib.parse import urlencode

import requests

from api.poloniex.PoloniexWebsocketAPI import PoloniexWebsocketAPI
from domain.CoinMarketData import CoinMarketData
from domain.TickerData import TickerData
from utils.LoggingUtils import LoggingUtils


class Poloniex(object):
    def __init__(self, api_key, secret):
        self.nonce = int("{:.6f}".format(time.time()).replace('.', ''))
        self.api_key = api_key
        self.secret = secret
        self.websocket = None
        self.api_ws_ticker_callback = None
        self.logger = LoggingUtils()
        self.logger.logging_info("Selected Poloniex Exchange")

    def get_nonce(self):
        self.nonce += 42
        return self.nonce

    def private_order(self, command, args=None):
        if args is None:
            args = {}

        while True:
            try:
                args['command'] = command
                args['nonce'] = self.get_nonce()
                post_data = urlencode(args)

                sign = hmac.new(self.secret.encode('utf-8'), post_data.encode('utf-8'), sha512)

                ret = requests.post('https://poloniex.com/tradingApi', data=args,
                                    headers={'Sign': sign.hexdigest(), 'Key': self.api_key})

                return json.loads(ret.text, parse_float=str)
            except Exception:
                self.logger.logging_bittbot_error('EJECUTAR PRIVATE ORDER {}'.format(command), 10)

    def public_order(self, command, args=None):
        if args is None:
            args = {}

        while True:
            try:
                args['command'] = command
                ret = requests.get('https://poloniex.com/public?' + urlencode(args))
                return json.loads(ret.text, parse_float=str)
            except Exception:
                self.logger.logging_bittbot_error('EJECUTAR PUBLIC ORDER {}'.format(command), 10)

    def get_full_ticker(self) -> List[TickerData]:
        while True:
            try:
                ticker = self.public_order('returnTicker')
                return self.parse_ticker(ticker)
            except Exception:
                self.logger.logging_bittbot_error('EJECUTAR LEER TICKER', 10)

    def parse_ticker(self, ticker_dict) -> List[TickerData]:
        ticker = []  # type: List[TickerData]
        for alt_name in ticker_dict:
            ticker_alt = ticker_dict[alt_name]

            ticker_data = TickerData()
            ticker_data.marketName = alt_name
            ticker_data.id = int(ticker_alt["id"])
            ticker_data.percentChange = float(ticker_alt["percentChange"])
            ticker_data.high = float(ticker_alt["high24hr"])
            ticker_data.low = float(ticker_alt["low24hr"])
            ticker_data.volume = float(ticker_alt["quoteVolume"])
            ticker_data.last = float(ticker_alt["last"])
            ticker_data.baseVolume = float(ticker_alt["baseVolume"])
            ticker_data.timeStamp = None
            ticker_data.bid = float(ticker_alt["highestBid"])
            ticker_data.ask = float(ticker_alt["lowestAsk"])
            ticker_data.openBuyOrders = -1
            ticker_data.openSellOrders = -1
            ticker_data.prevDay = 0.0
            ticker_data.created = None
            ticker.append(ticker_data)
        return ticker

    def subscribe_websocket(self, callback):
        self.api_ws_ticker_callback = callback
        ticker = self.get_full_ticker()
        alt_id_relation = self.populate_alt_to_id(ticker)
        self.websocket = PoloniexWebsocketAPI(self.process_websocket_ticker, alt_id_relation)

    def process_websocket_ticker(self, ticker):
        ticker = self.parse_ticker(ticker)
        self.api_ws_ticker_callback(ticker)

    def get_balance(self, currency_pair):
        while True:
            try:
                cc = currency_pair.split('_')
                balance = self.private_order('returnBalances')
                if len(cc) == 1:
                    return float(balance[cc[0]])
                else:
                    return float(balance[cc[1]])
            except Exception:
                self.logger.logging_bittbot_error('LEER BALANCE {}'.format(currency_pair), 10)

    def get_full_balance(self):
        while True:
            try:
                balance = self.private_order('returnBalances')
                return balance
            except Exception:
                self.logger.logging_bittbot_error('LEER BALANCE FULL', 10)

    def order_buy(self, currency_pair, buy_price, invest_balance):
        try:
            make_order_buy = self.private_order('buy', {'currencyPair': currency_pair, 'rate': str(buy_price),
                                                        'amount': str(invest_balance / buy_price), 'postOnly': 1})
            return make_order_buy['orderNumber'], buy_price
        except Exception:
            self.logger.logging_bittbot_error("CREAR ORDEN DE COMPRA PARA {}".format(currency_pair))
            return None, 0.0

    def order_sell(self, currency_pair, sell_price, invest_balance):
        try:
            make_order_sell = self.private_order('sell', {'currencyPair': currency_pair, 'rate': str(sell_price),
                                                          'amount': str(invest_balance), 'postOnly': 1})
            return make_order_sell['orderNumber']

        except Exception:
            self.logger.logging_bittbot_error("CREAR ORDEN DE VENTA PARA {}".format(currency_pair))
            return None

    def order_move(self, close_order_id, lowest_ask, operation_type):
        try:
            mov_orden = self.private_order('moveOrder', {'orderNumber': str(close_order_id), 'rate': str(lowest_ask),
                                                         'postOnly': 1})
            return str(mov_orden['orderNumber'])
        except Exception:
            self.logger.logging_bittbot_error('MOVER ORDEN DE {}'.format(operation_type))
            return None

    def exist_trade_order(self, coin, n_order):
        while True:
            try:
                order_trades = self.private_order('returnOrderTrades', {'orderNumber': n_order})
                if 'error' in order_trades:
                    return False
                else:
                    for order in order_trades:
                        if order["currencyPair"] == coin:
                            return True
                return False
            except Exception:
                self.logger.logging_bittbot_error('MIRAR SI EXISTE UNA ORDEN DE {} CON ID {}'.format(coin, n_order))

    def open_orders(self, currency_pair, num_last_order):
        while True:
            try:
                open_orders = self.private_order('returnOpenOrders', {'currencyPair': currency_pair, })
                if len(open_orders) == 0:
                    return False
                else:
                    for op in open_orders:
                        if op['orderNumber'] == num_last_order:
                            return True
                    return False
            except Exception:
                self.logger.logging_bittbot_error('LEER LAS ORDENES ABIERTAS', 10)

    def get_historic_values_fifteen_min(self, currency_pair, max_lasts) -> CoinMarketData:
        while True:
            try:
                historic = CoinMarketData()
                now = int(time.time())
                start = datetime.datetime.now() - datetime.timedelta(minutes=(15*max_lasts))
                start = int(time.mktime(start.timetuple()))
                response = self.public_order('returnChartData', {'currencyPair': currency_pair, 'start': start, 'end': now, 'period': 900})
                for historic_ticker in response:
                    historic.open.append(float(historic_ticker["open"]))
                    historic.high.append(float(historic_ticker["high"]))
                    historic.low.append(float(historic_ticker["low"]))
                    historic.close.append(float(historic_ticker["close"]))
                    historic.volume.append(float(historic_ticker["volume"]))

                return historic
            except Exception:
                self.logger.logging_bittbot_error('OBTENER VALORES HISTORICOS', 10)

    def get_historic_values_five_min(self, currency_pair, max_lasts) -> CoinMarketData:
        while True:
            try:
                historic = CoinMarketData()
                now = int(time.time())
                start = datetime.datetime.now() - datetime.timedelta(minutes=(5*max_lasts))
                start = int(time.mktime(start.timetuple()))
                response = self.public_order('returnChartData', {'currencyPair': currency_pair, 'start': start, 'end': now, 'period': 300})
                for historic_ticker in response:
                    historic.open.append(float(historic_ticker["open"]))
                    historic.high.append(float(historic_ticker["high"]))
                    historic.low.append(float(historic_ticker["low"]))
                    historic.close.append(float(historic_ticker["close"]))
                    historic.volume.append(float(historic_ticker["volume"]))

                return historic
            except Exception:
                self.logger.logging_bittbot_error('OBTENER VALORES HISTORICOS', 10)

    def populate_alt_to_id(self, ticker: List[TickerData]):
        alt_to_id = {}
        for ticker_alt in ticker:
            alt_to_id[ticker_alt.id] = ticker_alt.marketName
        return alt_to_id
