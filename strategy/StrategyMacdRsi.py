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

import sys
import time
import numpy as np
import talib

from api.Api import Api
from domain.InfoAlt import InfoAlt
from domain.MarketHistoric import MarketHistoric
from domain.Parameters import Parameters
from strategy.BaseStrategy import BaseStrategy
from utils import Config
from utils.LoggingUtils import LoggingUtils
from utils import RepeatedTimer as timer
from utils.Telegram import Telegram


class StrategyMacdRsi(BaseStrategy):

    def __init__(self, params: Parameters, api: Api, telegram_bot: Telegram, market_historic: MarketHistoric):
        super().__init__(params, api, telegram_bot, market_historic)
        self.params = params
        self.api = api
        self.telegram_bot = telegram_bot
        self.market_historic = market_historic
        self.update_market_timer = None
        self.print_status_timer = None
        self.num_currently_operating_alts = 0
        self.candles_time_minutes = 15
        self.logger = LoggingUtils()

    def pre_cycles_iterator(self) -> None:
        self.populate_market_history()
        self.market_historic.start_candle_calculations(self.candles_time_minutes)
        self.print_coins_macd_status()
        self.api.subscribe_websocket(self.market_historic)
        self.print_status_timer = timer.RepeatedTimer(60, self.print_coins_macd_status)
        time.sleep(30)

    def pre_coins_interator(self) -> None:
        return

    def post_coins_interator(self) -> None:
        return

    def post_cycles_iterator(self) -> None:
        if self.update_market_timer is not None:
            self.update_market_timer.stop()
        if self.print_status_timer is not None:
            self.print_status_timer.stop()

    def should_buy_coin(self, coin: InfoAlt) -> bool:
        if self.num_currently_operating_alts >= self.params.max_alts_to_trade:
            return False

        # If we have the same number of Candles than when we last bought this coin, ignore it until next candle is calculated.
        if len(self.market_historic.get_coin_market_data(coin.n_alt).close) == coin.last_used_candle:
            return False

        return self.analyze_macd_rsi(coin)

    #################################################
    #                 NOTIFICATIONS                 #
    #################################################

    def buy_order_placed_at_exchange(self, coin: InfoAlt) -> None:
        self.num_currently_operating_alts += 1
        # Store the number of candles we have when the buy has been places on the exchange, to avoid future buys on the same candle.
        coin.last_used_candle = len(self.market_historic.get_coin_market_data(coin.n_alt).close)

    def buy_order_completed(self, coin: InfoAlt) -> None:
        return

    def sell_order_placed_at_exchange(self, coin: InfoAlt) -> None:
        return

    def sell_order_completed(self, coin: InfoAlt) -> None:
        self.num_currently_operating_alts -= 1

    ######################################################
    #                 TECHNICAL ANALYSIS                 #
    ######################################################

    def populate_market_history(self):
        self.logger.logging_info('OBTENIENDO LOS DATOS DE HISTORIAL DE LAS MONEDAS DEL EXCHANGE PARA EL ANÁLISIS TÉCNICO (MACD/RSI)')
        for coin in self.params.coins_trader:
            coin_historic = self.api.get_historic_values_fifteen_min(coin.n_alt)
            if len(coin_historic.close) >= (self.params.macd_long_period * 2):
                self.market_historic.set_coin_market_data(coin.n_alt, coin_historic)
            else:
                self.logger.logging_info("NO SE HA PODIDO OBTENER LOS DATOS HISTORICOS DE {}".format(coin.n_alt))
                sys.exit(0)
            time.sleep(2)
        self.logger.logging_info('### INICIANDO BITTBOT CON LOS VALORES RECOGIDOS DEL EXCHANGE ###')

    def calculate_macd(self, coin: InfoAlt):
        candles = np.array(self.market_historic.get_coin_market_data(coin.n_alt).close, dtype=float)
        macd, macdsignal, macdhist = talib.MACD(candles, self.params.macd_short_period, self.params.macd_long_period, self.params.macd_smoothing)
        return macd, macdsignal, macdhist

    def calculate_rsi(self, coin: InfoAlt):
        candles = np.array(self.market_historic.get_coin_market_data(coin.n_alt).close, dtype=float)
        return talib.RSI(candles)

    def analyze_macd_rsi(self, coin: InfoAlt):
        macd, macdsignal, macdhist = self.calculate_macd(coin)
        rsi = self.calculate_rsi(coin)

        # CASE 1: histogram is already positive -> we need RSI to cross from 50- to 50+
        if macdhist[-1] > 0 and (rsi[-3] < 50 and rsi[-2] <= 50 and rsi[-1] > 50):
            return True

        # CASE 2: RSI is already at 50+ -> we need histogram to cross from negative to positive
        if rsi[-1] > 50 and (macdhist[-3] < 0 and macdhist[-2] <= 0 and macdhist[-1] > 0):
            return True

        return False

    def print_coins_macd_status(self):
        self.logger.logging_line_char("-")
        self.logger.logging_info("Ultimos valores del Historial MACD y RSI para cada moneda (de más reciente a más antiguo):")
        for coin in self.params.coins_trader:
            macd, macdsignal, macdhist = self.calculate_macd(coin)
            rsi = self.calculate_rsi(coin)
            self.logger.logging_info("\t[{}] - HMACD: {}, {}, {}. RSI: {}, {}, {}".format(coin.n_alt, macdhist[-1], macdhist[-2], macdhist[-3], rsi[-1], rsi[-2], rsi[-3]))
        self.logger.logging_line_char("-")

    ##############################################
    #                 PARAMETERS                 #
    ##############################################

    def get_needed_parameters(self):
        self.params.full_invest_quantity = Config.get_balance_invest(self.api, self.params.altstr)
        self.params.stop_loss = Config.get_stop_loss()
        self.params.macd_short_period = Config.get_short_macd()
        self.params.macd_long_period = Config.get_long_macd()
        self.params.macd_smoothing = Config.get_macd_smoothing()
        self.params.max_alts_to_trade = Config.get_max_alts_to_trade(len(self.params.working_alts))
        self.params.saldo_inv = self.params.full_invest_quantity / self.params.max_alts_to_trade
        self.params.profit_margin_alts = Config.get_profit_margin_alts() / 100
        Config.populate_coins(self.params)
        self.params.cycles = Config.get_cycles()

    def show_config_summary(self):
        self.logger.logging_empty_line()
        self.logger.logging_line_char("*")
        self.logger.logging_decorative("Resumen de configuración")
        self.logger.logging_empty_line()
        self.logger.logging_info("Estrategia: Análisis técnico (MACD + RSI)")
        self.logger.logging_info("Fichero configuracion: {}".format(self.params.config_file))
        self.logger.logging_info('Alt escogida: {}'.format(self.params.altstr))
        self.logger.logging_info('Saldo Invertido: {} {}'.format(self.params.full_invest_quantity, self.params.altstr))
        self.logger.logging_info('Opcion Escogida: {}'.format(self.params.funcionamiento))
        self.logger.logging_info('Margen de Perdidas: {} %'.format(self.params.stop_loss * 100))
        self.logger.logging_info('Margen de Beneficio: {} %'.format(self.params.profit_margin_alts * 100))
        self.logger.logging_info('Periodo MACD Corto: {}'.format(self.params.macd_short_period))
        self.logger.logging_info('Periodo MACD Largo: {}'.format(self.params.macd_long_period))
        self.logger.logging_info('Periodo smoothing de MACD: {}'.format(self.params.macd_smoothing))
        self.logger.logging_info('Num Max Alts Tradear: {}'.format(self.params.max_alts_to_trade))
        self.logger.logging_info('Total de Ciclos: {}'.format(self.params.cycles))
        self.logger.logging_line_char("*")
        self.logger.logging_empty_line()

    def telegram_config_summary(self):
        summary = 'Iniciada nueva sesión de Bittbot!\n\nEstrategia: Análisis técnico (MACD + RSI)'
        summary += '\nSaldo Invertido: {} {}'.format(self.params.full_invest_quantity, self.params.altstr)
        summary += '\nMargen de Perdidas: {} %'.format(self.params.stop_loss * 100)
        summary += '\nMargen de Beneficio: {} %'.format(self.params.profit_margin_alts * 100)
        summary += '\nMACD: {}/{}/{}'.format(self.params.macd_short_period, self.params.macd_long_period, self.params.macd_smoothing)
        summary += '\nNum Max Alts Tradear: {}'.format(self.params.max_alts_to_trade)
        summary += '\nTotal de Ciclos: {}'.format(self.params.cycles)
        self.telegram_bot.send_message(summary)
