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

from datetime import datetime
from typing import List

from domain.CoinMarketData import CoinMarketData
from domain.Parameters import Parameters
from domain.TickerData import TickerData
from utils.LoggingUtils import LoggingUtils


class Api(object):
    def __init__(self, params: Parameters, api):
        self.params = params
        self.api = api
        self.shown_ticker_minute = -1
        self.logger = LoggingUtils()
        self.market_historic = None

    def get_full_ticker(self) -> List[TickerData]:
        return self.api.get_full_ticker()

    def subscribe_websocket(self, market_historic):
        self.market_historic = market_historic
        self.api.subscribe_websocket(self.process_websocket_ticker_update)

    def process_websocket_ticker_update(self, ws_ticker):
        show_ticker = False
        if datetime.now().minute != self.shown_ticker_minute:
            self.shown_ticker_minute = datetime.now().minute
            show_ticker = True
        self.market_historic.process_ticker(ws_ticker, show_ticker)

    def hist_exists(self, coin, n_order):
        return self.api.exist_trade_order(coin, n_order)

    def order_buy(self, currency_pair, lowest_ask, invest_balance):
        order_num, price = self.api.order_buy(currency_pair, lowest_ask, invest_balance)

        if order_num is not None:
            self.logger.logging_result_star('{} CREADA ORDEN DE COMPRA NUM {} - PRECIO: {} - INVERSION: {}'.format(currency_pair, order_num, lowest_ask, invest_balance))
        else:
            self.logger.logging_result_star('{} FALLO AL INTENTAR CRER ORDEN DE COMPRA - PRECIO: {} - INVERSION: {}'.format(currency_pair, lowest_ask, invest_balance))

        return order_num, price

    def order_sell(self, currency_pair, sell_price, invest_balance):
        order_num = self.api.order_sell(currency_pair, sell_price, invest_balance)

        if order_num is not None:
            self.logger.logging_result_star("{} CREADA ORDEN DE VENTA NUM {} - PRECIO: {} - IVERSION: {}".format(currency_pair, order_num, sell_price, invest_balance))
        else:
            self.logger.logging_result_star('{} ERROR AL INTENTAR CRER ORDEN DE VENDA - PRECIO: {} - INVERSION: {}'.format(currency_pair, sell_price, invest_balance))

        return order_num

    def order_move(self, close_order_id, lowest_ask, operation_type):
        order_num = self.api.order_move(close_order_id, lowest_ask, operation_type)

        if order_num is not None:
            self.logger.logging_result_star('MOVIDA ORDEN DE {}: {} -> {} AL NUEVO PRECIO: {} CORRECTAMENTE'.format(operation_type, close_order_id, order_num, lowest_ask))
        else:
            self.logger.logging_result_star('ERROR AL MOVER ORDEN DE {}: {} AL NUEVO PRECIO: {}'.format(operation_type, close_order_id, lowest_ask))

        return order_num

    def open_orders(self, currency_pair, num_last_order):
        return self.api.open_orders(currency_pair, num_last_order)

    def get_balance(self, c):
        return self.api.get_balance(c)

    def get_full_balance(self):
        return self.api.get_full_balance()

    def exists_in_coins_trader(self, coin):
        for co in self.params.coins_trader:
            if coin == co.n_alt:
                return True
        return False

    def num_open_orders(self):
        n_open_orders = 0
        for c in self.params.coins_trader:
            if c.operation_type != 'NO_ORDER':
                n_open_orders += 1

        return n_open_orders

    def get_historic_values_fifteen_min(self, coin, max_lasts=500) -> CoinMarketData:
        return self.api.get_historic_values_fifteen_min(coin, max_lasts)

    def get_historic_values_five_min(self, coin, max_lasts=500) -> CoinMarketData:
        return self.api.get_historic_values_five_min(coin, max_lasts)
