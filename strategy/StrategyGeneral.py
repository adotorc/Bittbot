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
from strategy.BaseStrategy import BaseStrategy
from utils import Config
from utils.LoggingUtils import LoggingUtils
from utils.Telegram import Telegram


class StrategyGeneral(BaseStrategy):
    def __init__(self, params: Parameters, api: Api, telegram_bot: Telegram, market_historic: MarketHistoric):
        super().__init__(params, api, telegram_bot, market_historic)
        self.params = params
        self.api = api
        self.telegram_bot = telegram_bot
        self.market_historic = market_historic
        self.logger = LoggingUtils()

    def pre_cycles_iterator(self) -> None:
        self.api.subscribe_websocket(self.market_historic)
        self.logger.logging_decorative('ESPERANDO 40 SEGUNDOS PARA PRIMERA RECOGIDA DE DATOS DEL EXCHANGE')
        time.sleep(40)

    def pre_coins_interator(self) -> None:
        return

    def post_coins_interator(self) -> None:
        return

    def post_cycles_iterator(self) -> None:
        pass

    def should_buy_coin(self, coin: InfoAlt) -> bool:
        coin_market = self.market_historic.get_coin_market_data(coin.n_alt)
        is_valid_change = coin_market.percentChange >= self.params.margin_increment_24h
        is_valid_lowest_ask = coin_market.lowestAsk <= (coin_market.high24hr + coin_market.low24hr) * self.params.current_margin_increment
        return is_valid_change and is_valid_lowest_ask

    #################################################
    #                 NOTIFICATIONS                 #
    #################################################

    def buy_order_placed_at_exchange(self, coin: InfoAlt) -> None:
        return

    def buy_order_completed(self, coin: InfoAlt) -> None:
        return

    def sell_order_placed_at_exchange(self, coin: InfoAlt) -> None:
        return

    def sell_order_completed(self, coin: InfoAlt) -> None:
        return

    def get_show_ticker(self) -> None:
        ticker = self.api.get_full_ticker()
        self.logger.logging_line_char("-")
        for ticker_alt in ticker:
            pair = ticker_alt.marketName.split('_')  # pair[0] -> Main coin, pair[1] -> Alt coin
            if pair[0] == self.params.altstr and pair[1] in self.params.working_alts:
                pct_change = round(ticker_alt.percentChange * 100, 3)
                self.logger.logging_decorative("{}  -- Max 24H: {} - Min 24H: {} - Inc: {} % - Last: {}".format(
                    ticker_alt.marketName, ticker_alt.high, ticker_alt.low, pct_change, ticker_alt.last))
        self.logger.logging_line_char("-")

    ##############################################
    #                 PARAMETERS                 #
    ##############################################

    def get_needed_parameters(self):
        self.params.full_invest_quantity = Config.get_balance_invest(self.api, self.params.altstr)
        # Get up to date Ticker and display it
        self.get_show_ticker()
        self.params.margin_increment_24h = Config.get_margin_increment_24h()
        self.params.current_margin_increment = Config.get_current_margin_increment()
        self.params.stop_loss = Config.get_stop_loss()
        self.params.profit_margin_alts = Config.get_profit_margin_alts() / 100
        Config.populate_coins(self.params)
        self.params.saldo_inv = self.params.full_invest_quantity / len(self.params.coins_trader)
        self.params.cycles = Config.get_cycles()

    def show_config_summary(self):
        self.logger.logging_empty_line()
        self.logger.logging_line_char("*")
        self.logger.logging_decorative("Resumen de configuración")
        self.logger.logging_empty_line()
        self.logger.logging_info("Estrategia : Segun Margen de Incremento 24h")
        self.logger.logging_info("Fichero configuracion: {}".format(self.params.config_file))
        self.logger.logging_info('Alt escogida: {}'.format(self.params.altstr))
        self.logger.logging_info('Saldo Invertido: {} {}'.format(self.params.full_invest_quantity, self.params.altstr))
        self.logger.logging_info('Opcion Escogida: {}'.format(self.params.funcionamiento))
        self.logger.logging_info('Margen de Perdidas: {} %'.format(self.params.stop_loss * 100))
        self.logger.logging_info('Margen Incremento 24h: {} %'.format(self.params.margin_increment_24h * 100))
        self.logger.logging_info('Margen Incremento Actual: {} %'.format(self.params.current_margin_increment * 100))
        self.logger.logging_info('Margen de Beneficio: {} %'.format(self.params.profit_margin_alts * 100))
        self.logger.logging_info('Total de Ciclos: {}'.format(self.params.cycles))
        self.logger.logging_line_char("*")
        self.logger.logging_empty_line()

    def telegram_config_summary(self):
        summary = 'Iniciada nueva sesión de Bittbot!\n\nEstrategia: Segun Margen de Incremento 24h (Manual)'
        summary += '\nSaldo Invertido: {} {}'.format(self.params.full_invest_quantity, self.params.altstr)
        summary += '\nMargen de Perdidas: {} %'.format(self.params.stop_loss * 100)
        summary += '\nMargen Incremento 24h: {} %'.format(self.params.margin_increment_24h * 100)
        summary += '\nMargen Incremento Actual: {} %'.format(self.params.current_margin_increment * 100)
        summary += '\nMargen de Beneficio: {} %'.format(self.params.profit_margin_alts * 100)
        summary += '\nTotal de Ciclos: {}'.format(self.params.cycles)
        self.telegram_bot.send_message(summary)
