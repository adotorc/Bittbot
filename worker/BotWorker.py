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

from api.Api import Api
from domain.InfoAlt import InfoAlt
from domain.MarketHistoric import MarketHistoric
from domain.Parameters import Parameters
from strategy.StrategyAutoMargin import StrategyAutoMargin
from strategy.StrategyBBands import StrategyBBands
from strategy.StrategyMacdRsi import StrategyMacdRsi
from strategy.StrategyGeneral import StrategyGeneral
from utils import Config
from utils.LoggingUtils import LoggingUtils
from utils.Telegram import Telegram


class BotWorker(object):
    def __init__(self, params: Parameters, api: Api):
        self.params = params
        self.api = api
        self.global_cycles = 0
        self.num_profit_cycles = 0
        self.num_losses_cycles = 0
        self.total_profit = 0.0
        self.sleep = 10
        self.profit_alts = []
        self.losses_alts = []
        self.telegram_bot = Telegram()
        self.logger = LoggingUtils()
        self.market_historic = MarketHistoric()
        self.strategy = self.get_entry_strategy()

    def get_entry_strategy(self):
        if self.params.funcionamiento == Config.STRATEGY_AUTO_MARGIN:
            return StrategyAutoMargin(self.params, self.api, self.telegram_bot, self.market_historic)
        elif self.params.funcionamiento == Config.STRATEGY_MACD_RSI:
            return StrategyMacdRsi(self.params, self.api, self.telegram_bot, self.market_historic)
        elif self.params.funcionamiento == Config.STRATEGY_MANUAL_INCREMENT_24H_ALL_ALTS:
            return StrategyGeneral(self.params, self.api, self.telegram_bot, self.market_historic)
        elif self.params.funcionamiento == Config.STRATEGY_BBANDS:
            return StrategyBBands(self.params, self.api, self.telegram_bot, self.market_historic)

    def run(self):
        self.strategy.get_needed_parameters()
        self.strategy.show_config_summary()
        self.strategy.telegram_config_summary()
        self.strategy.pre_cycles_iterator()

        self.logger.print_init_bot()
        while self.global_cycles < self.params.cycles:
            self.strategy.pre_coins_interator()
            self.logger.logging_result('CICLOS: {}/{} -- Tot. Ciclos Benef: {} - Tot. Ciclos Perd: {} -- Beneficio: {}'.format(self.global_cycles, self.params.cycles, self.num_profit_cycles, self.num_losses_cycles, self.total_profit))
            for coin in self.params.coins_trader:
                if coin.operation_type == 'NO_ORDER':
                    # Only check for potential new buys if with this new buy we won't surpass max cycles.
                    if self.api.num_open_orders() + self.global_cycles < self.params.cycles:
                        if self.strategy.should_buy_coin(coin):
                            coin.operation_type = 'BUY'

                if coin.operation_type == 'BUY':
                    if self.do_buy(coin):
                        self.telegram_bot.send_message('[{}] Orden de compra creada a {}'.format(coin.n_alt, coin.last_buy_price))

                if coin.operation_type == 'WAIT_BUY':
                    self.strategy.buy_order_placed_at_exchange(coin)
                    bought = self.do_wait_for_buy_to_complete(coin)
                    if bought:
                        self.strategy.buy_order_completed(coin)
                        self.telegram_bot.send_message('[{}] Compra realizada correctamente a {}!'.format(coin.n_alt, coin.last_buy_price))

                if coin.operation_type == 'SELL':
                    if self.do_sell(coin):
                        self.telegram_bot.send_message('[{}] Orden de venta creada a {}'.format(coin.n_alt, coin.last_sell_price))

                if coin.operation_type == 'WAIT_SELL':
                    self.strategy.sell_order_placed_at_exchange(coin)
                    sold = self.do_wait_for_sell_to_complete(coin)
                    if sold:
                        self.strategy.sell_order_completed(coin)
                        self.telegram_bot.send_message('[{}] Venta finalizada correctamente a {}!'.format(coin.n_alt, coin.last_sell_price))

            self.strategy.post_coins_interator()
            time.sleep(self.sleep)

        self.strategy.post_cycles_iterator()
        self.print_results()

    def do_buy(self, coin: InfoAlt):
        coin_market_data = self.market_historic.get_coin_market_data(coin.n_alt)
        num_last_order, buy_price = self.api.order_buy(coin.n_alt, coin_market_data.lowestAsk, self.params.saldo_inv)
        if num_last_order is not None:
            coin.num_last_orden = num_last_order
            coin.last_buy_price = buy_price
            coin.operation_type = 'WAIT_BUY'
            coin.inv_last_compra = self.params.saldo_inv
            time.sleep(self.sleep)
            return True
        return False

    def do_wait_for_buy_to_complete(self, coin: InfoAlt):
        if self.api.hist_exists(coin.n_alt, coin.num_last_orden) and not self.api.open_orders(coin.n_alt, coin.num_last_orden):
            self.logger.logging_info('ORDEN DE COMPRA NUM: {} PARA {} FINALIZADA CORRECTAMENTE'.format(coin.num_last_orden, coin.n_alt))
            coin.operation_type = 'SELL'
            return True
        else:
            coin_market_data = self.market_historic.get_coin_market_data(coin.n_alt)
            if coin_market_data.lowestAsk > (coin.last_buy_price + (coin.last_buy_price * 0.01)):
                mv_num_orden = self.api.order_move(coin.num_last_orden, coin_market_data.lowestAsk, coin.operation_type)
                if mv_num_orden is not None:
                    coin.last_buy_price = coin_market_data.lowestAsk
                    coin.num_last_orden = mv_num_orden
                    time.sleep(self.sleep)
            else:
                self.logger.logging_result('ESPERANDO QUE SE CIERRE LA ORDEN {} DE {} PARA {} ({})'.format(coin.num_last_orden, coin.operation_type, coin.n_alt, coin.last_buy_price))
            return False

    def do_sell(self, coin: InfoAlt):
        coin_market_data = self.market_historic.get_coin_market_data(coin.n_alt)
        saldo_inv_alt = self.api.get_balance(coin.n_alt)
        sell_price = coin.last_buy_price + (coin.last_buy_price * self.params.profit_margin_alts)
        if sell_price < coin_market_data.highestBid:
            sell_price = coin_market_data.highestBid

        if saldo_inv_alt > 0:
            order_id = self.api.order_sell(coin.n_alt, sell_price, saldo_inv_alt)
            if order_id is not None:
                coin.num_last_orden = order_id
                coin.last_sell_price = sell_price
                coin.operation_type = 'WAIT_SELL'
                coin.inv_last_venta = saldo_inv_alt
                time.sleep(self.sleep)
                return True
        else:
            self.logger.logging_line_char(">")
            self.logger.logging_error('ERROR. SALDO INSUFICIENTE EN {} PARA REALIZAR LA VENTA'.format(coin.n_alt))
            self.logger.logging_error('ESPERANDO NUEVO SALDO')
            self.logger.logging_line_char(">")
        return False

    def do_wait_for_sell_to_complete(self, coin: InfoAlt):
        if self.api.hist_exists(coin.n_alt, coin.num_last_orden) and not self.api.open_orders(coin.n_alt, coin.num_last_orden):
            self.logger.logging_result('ORDEN DE VENTA NUM: {} PARA {} FINALIZADA CORRECTAMENTE'.format(coin.num_last_orden, coin.n_alt))
            coin.operation_type = 'NO_ORDER'

            if coin.last_sell_price - coin.last_buy_price > 0:
                self.num_profit_cycles += 1
                self.profit_alts.append(coin.n_alt)
            else:
                self.num_losses_cycles += 1
                self.losses_alts.append(coin.n_alt)

            self.total_profit += (coin.last_sell_price * coin.inv_last_venta) - coin.inv_last_compra
            self.global_cycles += 1
            return True
        else:
            if self.params.stop_loss > 0.0:
                coin_market_data = self.market_historic.get_coin_market_data(coin.n_alt)
                if coin_market_data.highestBid <= coin.last_buy_price - (coin.last_buy_price * self.params.stop_loss):
                    self.logger.logging_info('STOP LOSS: MOVIENDO LA ORDEN A PARA CERRAR CON PERDIDAS')
                    mv_num_orden = self.api.order_move(coin.num_last_orden, coin_market_data.highestBid, coin.operation_type)
                    if mv_num_orden is not None:
                        coin.last_sell_price = coin_market_data.highestBid
                        coin.num_last_orden = mv_num_orden
                        time.sleep(self.sleep)
                else:
                    self.logger.logging_result('ESPERANDO QUE SE CIERRE LA ORDEN {} DE {} PARA {} ({})'.format(coin.num_last_orden, coin.operation_type, coin.n_alt, coin.last_sell_price))
            else:
                self.logger.logging_result('ESPERANDO QUE SE CIERRE LA ORDEN {} DE {} PARA {} ({})'.format(coin.num_last_orden, coin.operation_type, coin.n_alt, coin.last_sell_price))
            return False

    def print_results(self):
        self.logger.logging_empty_line()
        self.logger.logging_decorative('###############################################################')
        self.logger.logging_decorative('#########    BITTBOT  FINALIZADO  CORRECTAMENTE     ###########')
        self.logger.logging_decorative('###############################################################')
        self.logger.logging_empty_line()
        self.logger.logging_empty_line()
        self.logger.logging_decorative(' TOTAL BENEFICIO: {}'.format(self.total_profit))
        self.logger.logging_empty_line()
        self.logger.logging_info('FINALIZADO CORRECTAMENTE CON BENEFICIO: {}'.format(self.total_profit))
        if len(self.profit_alts) > 0:
            self.logger.logging_line_char("-")
            self.logger.logging_info('ALTS CON BENEFICIO')
            profit_alts_copy = []
            for a in self.profit_alts:
                if a not in profit_alts_copy:
                    self.logger.logging_info('({}) {}'.format(self.profit_alts.count(a), a))
                    profit_alts_copy.append(a)
        self.logger.logging_empty_line()
        if len(self.losses_alts) > 0:
            self.logger.logging_line_char("-")
            self.logger.logging_info('ALTS CON PERDIDAS')
            losses_alts_copy = []
            for a in self.losses_alts:
                if a not in losses_alts_copy:
                    self.logger.logging_info('({}) {}'.format(self.losses_alts.count(a), a))
                    losses_alts_copy.append(a)
