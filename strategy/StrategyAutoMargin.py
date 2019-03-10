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
from domain import InfoAlt
from domain.MarketHistoric import MarketHistoric
from domain.Parameters import Parameters
from strategy.BaseStrategy import BaseStrategy
from utils import Config
from utils.LoggingUtils import LoggingUtils
from utils.Telegram import Telegram


class StrategyAutoMargin(BaseStrategy):
    def __init__(self, params: Parameters, api: Api, telegram_bot: Telegram, market_historic: MarketHistoric):
        super().__init__(params, api, telegram_bot, market_historic)
        self.params = params
        self.api = api
        self.alts_borrar = None
        self.alts_no_cumplen = None
        self.num_currently_operating_alts = 0
        self.telegram_bot = telegram_bot
        self.market_historic = market_historic
        self.logger = LoggingUtils()

    def pre_cycles_iterator(self) -> None:
        self.api.subscribe_websocket(self.market_historic)
        self.logger.logging_decorative('ESPERANDO 40 SEGUNDOS PARA PRIMERA RECOGIDA DE DATOS DEL EXCHANGE')
        time.sleep(40)

    def pre_coins_interator(self) -> None:
        if len(self.params.coins_trader) < self.params.max_alts_to_trade:
            coin_pairs = self.choose_alts()
            p = len(self.params.coins_trader)
            for coin_pair in coin_pairs:
                if p <= self.params.max_alts_to_trade and not self.api.exists_in_coins_trader(coin_pair):
                    fit_coin = InfoAlt.InfoAlt()
                    fit_coin.n_alt = coin_pair
                    self.params.coins_trader.append(fit_coin)
                    self.logger.logging_info('({}) INCORPORADA LA SIGUIENTE ALT: {} PARA TRADER'.format(len(self.params.coins_trader), coin_pair))
                    p += 1
        self.alts_borrar = []
        self.alts_no_cumplen = []

    def post_coins_interator(self) -> None:
        if len(self.alts_borrar) > 0:
            self.logger.logging_line_char("-")
            for al in self.alts_borrar:
                self.logger.logging_info('QUITANDO {} - PROCESO DE TRADER COMPLETADO CON EXITO'.format(al.n_alt))
                self.params.coins_trader.remove(al)
            self.logger.logging_line_char("-")

        if len(self.alts_no_cumplen) > 0:
            self.logger.logging_line_char("-")
            for al in self.alts_no_cumplen:
                self.logger.logging_info('QUITANDO {} POR NO CUMPLIR CON LOS PARAMETROS DE TRADER'.format(al.n_alt))
                self.params.coins_trader.remove(al)
            self.logger.logging_line_char("-")

    def post_cycles_iterator(self) -> None:
        pass

    def should_buy_coin(self, coin: InfoAlt) -> bool:
        if self.num_currently_operating_alts >= self.params.max_alts_to_trade:
            return False

        coin_market = self.market_historic.get_coin_market_data(coin.n_alt)
        if coin_market.percentChange >= self.params.margin_increment_24h and coin_market.lowestAsk <= coin_market.low24hr + ((coin_market.high24hr - coin_market.low24hr) * self.params.current_margin_increment):
            return True
        else:
            self.alts_no_cumplen.append(coin)
            return False

    #################################################
    #                 NOTIFICATIONS                 #
    #################################################

    def buy_order_placed_at_exchange(self, coin: InfoAlt) -> None:
        self.num_currently_operating_alts += 1

    def buy_order_completed(self, coin: InfoAlt) -> None:
        return

    def sell_order_placed_at_exchange(self, coin: InfoAlt) -> None:
        return

    def sell_order_completed(self, coin: InfoAlt) -> None:
        self.alts_borrar.append(coin)
        self.num_currently_operating_alts -= 1

    ######################################################
    #                 TECHNICAL ANALYSIS                 #
    ######################################################

    # Returns an array with the names of the coin pairs selected (ex: [BTC_ETH, BTC_NEO] )
    def choose_alts(self):
        alts_ok = []
        alts_ok_def = []
        ticker = self.api.get_full_ticker()

        for ticker_alt in ticker:
            pair = ticker_alt.marketName.split('_')  # pair[0] -> Main coin, pair[1] -> Alt coin
            if pair[0] == self.params.altstr and pair[1] in self.params.working_alts:
                desired_increment = (ticker_alt.high - ticker_alt.low) * self.params.current_margin_increment
                pass_percentage = ticker_alt.percentChange >= self.params.margin_increment_24h
                pass_current_increment = ticker_alt.ask <= ticker_alt.low + desired_increment
                if pass_percentage and pass_current_increment:
                    historic = self.market_historic.get_coin_market_data(ticker_alt.marketName)
                    if historic is None:  # This could happen on a coin that has near no movement
                        continue
                    alts_ok.append(historic)

        if len(alts_ok) == 0:
            self.logger.logging_info('### NINGUNA NUEVA ALT CUMPLE CON LOS CRITERIOS DE TRADER ###')
        else:
            self.logger.logging_line_char("-")
            alts_ok = sorted(alts_ok, key=lambda objeto: objeto.percentChange, reverse=True)
            n_tr = 1
            for coin in alts_ok:
                if n_tr <= self.params.max_alts_to_trade:
                    self.logger.logging_info("{} -- Max 24H: {} - Min 24H: {} - Inc: {} % - Last: {}".format(coin.alt_name, coin.high24hr, coin.low24hr, round(coin.percentChange * 100, 3), coin.last))
                    alts_ok_def.append(coin.alt_name)
                    n_tr += 1
            self.logger.logging_line_char("-")
        return alts_ok_def

    ##############################################
    #                 PARAMETERS                 #
    ##############################################
    def get_needed_parameters(self) -> None:
        self.params.full_invest_quantity = Config.get_balance_invest(self.api, self.params.altstr)
        # Get up to date Ticker and display it
        self.get_show_ticker()
        self.params.margin_increment_24h = Config.get_margin_increment_24h()
        self.params.current_margin_increment = Config.get_current_margin_increment()
        self.params.stop_loss = Config.get_stop_loss()
        self.params.max_alts_to_trade = Config.get_max_alts_to_trade(len(self.params.working_alts))
        self.params.saldo_inv = self.params.full_invest_quantity / self.params.max_alts_to_trade
        self.params.profit_margin_alts = Config.get_profit_margin_alts() / 100
        self.params.cycles = Config.get_cycles()

    def show_config_summary(self) -> None:
        self.logger.logging_empty_line()
        self.logger.logging_line_char("*")
        self.logger.logging_decorative("Resumen de configuración")
        self.logger.logging_empty_line()
        self.logger.logging_info("Estrategia : Automatico. Escoge las mejores Alts para tradear en cada momento (Segun Margenes)")
        self.logger.logging_info("Fichero configuracion: {}".format(self.params.config_file))
        self.logger.logging_info('Alt escogida: {}'.format(self.params.altstr))
        self.logger.logging_info('Saldo Invertido: {} {}'.format(self.params.full_invest_quantity, self.params.altstr))
        self.logger.logging_info('Opcion Escogida: {}'.format(self.params.funcionamiento))
        self.logger.logging_info('Margen de Perdidas: {} %'.format(self.params.stop_loss * 100))
        self.logger.logging_info('Margen Incremento 24h: {} %'.format(self.params.margin_increment_24h * 100))
        self.logger.logging_info('Margen Incremento Actual: {} %'.format(self.params.current_margin_increment * 100))
        self.logger.logging_info('Margen de Beneficio: {} %'.format(self.params.profit_margin_alts * 100))
        self.logger.logging_info('Num Max Alts Tradear: {}'.format(self.params.max_alts_to_trade))
        self.logger.logging_info('Total de Ciclos: {}'.format(self.params.cycles))
        self.logger.logging_line_char("*")
        self.logger.logging_empty_line()

    def telegram_config_summary(self):
        summary = 'Iniciada nueva sesión de Bittbot!\n\nEstrategia: Automático Segun Margenes'
        summary += '\nSaldo Invertido: {} {}'.format(self.params.full_invest_quantity, self.params.altstr)
        summary += '\nMargen de Perdidas: {} %'.format(self.params.stop_loss * 100)
        summary += '\nMargen Incremento 24h: {} %'.format(self.params.margin_increment_24h * 100)
        summary += '\nMargen Incremento Actual: {} %'.format(self.params.current_margin_increment * 100)
        summary += '\nMargen de Beneficio: {} %'.format(self.params.profit_margin_alts * 100)
        summary += '\nNum Max Alts Tradear: {}'.format(self.params.max_alts_to_trade)
        summary += '\nTotal de Ciclos: {}'.format(self.params.cycles)
        self.telegram_bot.send_message(summary)

    def get_show_ticker(self) -> None:
        ticker = self.api.get_full_ticker()
        self.logger.logging_line_char("-")
        for ticker_alt in ticker:
            pair = ticker_alt.marketName.split('_')  # pair[0] -> Main coin, pair[1] -> Alt coin
            if pair[0] == self.params.altstr and pair[1] in self.params.working_alts:
                self.logger.logging_decorative("{}  -- Max 24H: {} - Min 24H: {} - Inc: {} % - Last: {}".format(
                    ticker_alt.marketName, ticker_alt.high, ticker_alt.low, round(ticker_alt.percentChange * 100, 3),
                    ticker_alt.last))
        self.logger.logging_line_char("-")
