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
import numpy as np
import talib

from api.Api import Api
from domain.CoinMarketData import CoinMarketData
from domain.InfoAlt import InfoAlt
from domain.MarketHistoric import MarketHistoric
from domain.Parameters import Parameters
from strategy.BaseStrategy import BaseStrategy
from utils import Config
from utils.LoggingUtils import LoggingUtils
from utils import RepeatedTimer as timer
from utils.Telegram import Telegram


class StrategyBBands(BaseStrategy):

    def __init__(self, params: Parameters, api: Api, telegram_bot: Telegram, market_historic: MarketHistoric):
        super().__init__(params, api, telegram_bot, market_historic)
        self.params = params
        self.api = api
        self.telegram_bot = telegram_bot
        self.market_historic = market_historic
        self.update_market_timer = None
        self.print_status_timer = None
        self.num_currently_operating_alts = 0
        self.candles_time_minutes = 5
        self.market_historic = market_historic
        self.logger = LoggingUtils()
        self.bbands_period = 20
        self.bbands_stddev = 2
        self.min_historic_data = 300  # A little more than 24h with 5min candle

    def pre_cycles_iterator(self) -> None:
        self.market_historic.start_candle_calculations(self.candles_time_minutes)
        self.api.subscribe_websocket(self.market_historic)
        self.print_status_timer = timer.RepeatedTimer(60, self.print_coins_bbands_status)
        time.sleep(30)

    def pre_coins_interator(self) -> None:
        self.delete_not_operating_coins()  # Removes the alts that does not have an order in the exchange.

        if len(self.params.coins_trader) < self.params.max_alts_to_trade:
            bugged_coins = []  # Thanks Bittrex for bugged coins that has 24h percentage change, volume but not buy/sell operations
            coins = self.select_coins_to_operate()
            if len(coins) == 0:
                self.logger.logging_info("NO HAY ALTS QUE CUMPLAN LOS REQUISITOS")
                return
            for coin in coins:
                if not self.api.exists_in_coins_trader(coin.n_alt):
                    self.params.coins_trader.append(coin)
            # Update historic if it's the first time we use this alt -> doesn't have historic data
            for coin in self.params.coins_trader:
                coin_market_data = self.market_historic.get_coin_market_data(coin.n_alt)
                if coin_market_data is None:
                    bugged_coins.append(coin)
                    continue
                if len(coin_market_data.close) < self.min_historic_data:
                    self.populate_market_history(coin)
                    coin_market_data = self.market_historic.get_coin_market_data(coin.n_alt)
                    if len(coin_market_data.close) < self.min_historic_data:
                        bugged_coins.append(coin)
                        continue
            for coin in bugged_coins:
                self.params.coins_trader.remove(coin)

    def delete_not_operating_coins(self):
        alt_not_operating = []
        for coin in self.params.coins_trader:
            if coin.operation_type == 'NO_ORDER':
                alt_not_operating.append(coin)
        if len(alt_not_operating) > 0:
            for coin in alt_not_operating:
                self.params.coins_trader.remove(coin)

    def select_coins_to_operate(self):
        blacklisted_coins = []
        if "Blacklisted_Coins" in self.params.config:
            for alt_name in self.params.config["Blacklisted_Coins"]:
                blacklisted_coins.append("{}_{}".format(self.params.altstr, alt_name))
        market_alts = []  # List[CoinMarketData]
        ticker = self.api.get_full_ticker()
        for ticker_alt in ticker:
            if ticker_alt.marketName.find(self.params.altstr) != 0:  # We want ALT_*** only, so we want it in position 0
                continue
            if ticker_alt.marketName in blacklisted_coins:
                continue
            volume = ticker_alt.baseVolume
            change24h = ticker_alt.percentChange * 100
            if change24h < self.params.coin_selection_min_24_increment or change24h > self.params.coin_selection_max_24_increment:
                continue
            if volume < self.params.coin_selection_min_volume:
                continue
            # If we reach here, it fulfills all requirements, so add it
            alt = CoinMarketData()
            alt.alt_name = ticker_alt.marketName
            alt.baseVolume = volume
            alt.high24hr = ticker_alt.high
            alt.low24hr = ticker_alt.low
            alt.percentChange = change24h
            alt.lowestAsk = ticker_alt.ask
            alt.highestBid = ticker_alt.bid
            alt.last = ticker_alt.last
            market_alts.append(alt)
        market_alts.sort(key=lambda x: x.baseVolume, reverse=True)  # Sort by Volume descending
        alts = []
        for market_coin in market_alts:
            alt = InfoAlt()
            alt.n_alt = market_coin.alt_name
            alts.append(alt)
        return alts

    def post_coins_interator(self) -> None:
        return

    def post_cycles_iterator(self) -> None:
        if self.update_market_timer is not None:
            self.update_market_timer.stop()
        if self.print_status_timer is not None:
            self.print_status_timer.stop()

    def should_buy_coin(self, coin: InfoAlt) -> bool:
        if self.num_currently_operating_alts >= self.params.max_alts_to_trade:
            # self.logger.logging_info("[{}] No compramos porque ya estamos usando el numero maximo de alts simultaneas {}/{}".format(coin.n_alt, self.num_currently_operating_alts, self.params.max_alts_to_trade))
            return False

        # If we have the same number of Candles than when we last bought this coin, ignore it until next candle is calculated.
        if len(self.market_historic.get_coin_market_data(coin.n_alt).close) == coin.last_used_candle:
            # self.logger.logging_info("[{}] No compramos porque ya hemos operado en esta coin y esta vela {}".format(coin.n_alt, coin.last_used_candle))
            return False

        # We analyse current 5-min candle BB entry condition. If it's valid, we then check if the market is bullish.
        # If both conditions are fulfilled, we issue a buy signal.
        bbands_entry_signal = self.analyze_bbands_entry(coin)
        if bbands_entry_signal:
            is_market_bull = self.get_market_state(coin)
            if is_market_bull:
                return True
        return False

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

    def populate_market_history(self, coin: InfoAlt):
        self.logger.logging_info('Obteniendo los valores historicos de la alt {}'.format(coin.n_alt))
        coin_historic = self.api.get_historic_values_five_min(coin.n_alt)
        if len(coin_historic.close) >= self.min_historic_data:
            self.market_historic.set_coin_market_historic_only(coin.n_alt, coin_historic)
            return True
        else:
            self.logger.logging_info("NO SE HA PODIDO OBTENER LOS DATOS HISTORICOS DE {}".format(coin.n_alt))
            return False

    def calculate_bbands(self, coin: InfoAlt):
        candles = np.array(self.market_historic.get_coin_market_data(coin.n_alt).close, dtype=float)
        upperband, middleband, lowerband = talib.BBANDS(candles, self.bbands_period, self.bbands_stddev, self.bbands_stddev)
        return upperband, middleband, lowerband

    def analyze_bbands_entry(self, coin: InfoAlt):
        upperband, middleband, lowerband = self.calculate_bbands(coin)
        last_close = self.market_historic.get_coin_market_data(coin.n_alt).close[-1]
        last_open = self.market_historic.get_coin_market_data(coin.n_alt).open[-1]

        # Check for a red candle (close < open)
        if last_close < last_open:
            # Check if the candle crosses the lower Bollinger Band (overselling)
            if (lowerband[-1] >= ((last_open - last_close) * self.params.bbands_crossing_share) + last_close) and lowerband[-1] < last_open:
                return True

        return False

    def get_market_state(self, coin: InfoAlt):
        candles = self.generate_half_hour_candles(coin)
        closes = np.array(candles.close, dtype=float)
        ema9 = talib.EMA(closes, 9)
        # self.logger.logging_info("[{}] -> Will start analysing market EMA9[-1] = {}, EMA9[-48] = {}".format(coin.n_alt, ema9[-1], ema9[-48]))
        if ema9[-1] >= (ema9[-48] + (ema9[-48] * self.params.market_state_24h_share)):
            # self.logger.logging_info("[{}] -> Passed ema9 (24h)".format(coin.n_alt))
            ema12 = talib.EMA(closes, 12)
            if ema12[-1] >= (ema12[-24] + (ema12[-24] * self.params.market_state_12h_share)):
                # self.logger.logging_info("[{}] -> Passed ema12 (12h)".format(coin.n_alt))
                ema24 = talib.EMA(closes, 24)
                if ema24[-1] >= (ema24[-10] + (ema24[-10] * self.params.market_state_5h_share)):
                    # self.logger.logging_info("[{}] -> Passed ema24 (5h)".format(coin.n_alt))
                    return True
        return False

    '''
    Returns 30 minutes candles based on 5min candles from exchange.
    '''
    def generate_half_hour_candles(self, coin: InfoAlt) -> CoinMarketData:
        coin_data = self.market_historic.get_coin_market_data(coin.n_alt)
        chunk_size = 5  # 30 min -> 5x 5min candles

        # The order will be reversed to create the 30minute candle data.
        # That means newest candle will be on position [0] while the oldest one will be at [-1]
        chunk_open = [coin_data.open[::-1][i:i + chunk_size] for i in range(0, len(coin_data.open), chunk_size)]  # [::-1] reverses the array as a view
        chunk_high = [coin_data.high[::-1][i:i + chunk_size] for i in range(0, len(coin_data.high), chunk_size)]
        chunk_low = [coin_data.low[::-1][i:i + chunk_size] for i in range(0, len(coin_data.low), chunk_size)]
        chunk_close = [coin_data.close[::-1][i:i + chunk_size] for i in range(0, len(coin_data.close), chunk_size)]

        # Reverse the order to get back to the original one.
        # That means newest candle on [-1] and oldest on [0]
        chunk_open.reverse()
        chunk_high.reverse()
        chunk_low.reverse()
        chunk_close.reverse()

        new_candles = CoinMarketData()
        new_candles.alt_name = coin_data.alt_name
        for i in range(0, len(chunk_close)):
            new_candles.open.append(chunk_open[i][-1])
            new_candles.high.append(max(chunk_high))
            new_candles.low.append(min(chunk_low))
            new_candles.close.append(chunk_close[i][0])
        return new_candles

    def print_coins_bbands_status(self):
        if len(self.params.coins_trader) == 0:
            return
        self.logger.logging_line_char("-")
        self.logger.logging_info("Ultimos valores de las Bollinger Bands para cada moneda (de más reciente a más antiguo):")
        for coin in self.params.coins_trader:
            try:
                # This may crash when there is a bugged coin that is still not removed because we are still calculating
                # the market historic and we didn't detect it yet.
                upperband, middleband, lowerband = self.calculate_bbands(coin)
                timestamp = self.market_historic.get_coin_market_data(coin.n_alt).timestamp[-1]
                self.logger.logging_info("\t[{}] - BB Candle {} - upper: {}, middle: {}, lower: {}".format(coin.n_alt, timestamp, upperband[-1], middleband[-1], lowerband[-1]))
            except Exception:
                continue
        self.logger.logging_line_char("-")

    ##############################################
    #                 PARAMETERS                 #
    ##############################################

    def get_needed_parameters(self):
        self.params.full_invest_quantity = Config.get_balance_invest(self.api, self.params.altstr)
        self.params.stop_loss = Config.get_stop_loss()
        self.params.coin_selection_min_volume = Config.get_coin_selection_min_volume()
        self.params.coin_selection_min_24_increment = Config.get_coin_selection_min_24_increment()
        self.params.coin_selection_max_24_increment = Config.get_coin_selection_max_24_increment()
        self.params.bbands_crossing_share = Config.get_bbands_crossing_share()
        self.params.market_state_24h_share = Config.get_market_state_24h_share()
        self.params.market_state_12h_share = Config.get_market_state_12h_share()
        self.params.market_state_5h_share = Config.get_market_state_5h_share()
        self.params.max_alts_to_trade = Config.get_max_alts_to_trade(99999)
        self.params.saldo_inv = self.params.full_invest_quantity / self.params.max_alts_to_trade
        self.params.profit_margin_alts = Config.get_profit_margin_alts() / 100
        self.params.cycles = Config.get_cycles()

    def show_config_summary(self):
        self.logger.logging_empty_line()
        self.logger.logging_line_char("*")
        self.logger.logging_decorative("Resumen de configuración")
        self.logger.logging_empty_line()
        self.logger.logging_info("Estrategia: Análisis técnico (Bollinger Bands)")
        self.logger.logging_info("Fichero configuración: {}".format(self.params.config_file))
        self.logger.logging_info('Alt escogida: {}'.format(self.params.altstr))
        self.logger.logging_info('Saldo Invertido: {} {}'.format(self.params.full_invest_quantity, self.params.altstr))
        self.logger.logging_info('Opcion Escogida: {}'.format(self.params.funcionamiento))
        self.logger.logging_info('Margen de Perdidas: {} %'.format(self.params.stop_loss * 100))
        self.logger.logging_info('Margen de Beneficio: {} %'.format(self.params.profit_margin_alts * 100))
        self.logger.logging_info('Selección de Alts Min24h: {} %'.format(self.params.coin_selection_min_24_increment))
        self.logger.logging_info('Selección de Alts Max24h: {} %'.format(self.params.coin_selection_max_24_increment))
        self.logger.logging_info('Selección de Alts Volumen Minimo: {}'.format(self.params.coin_selection_min_volume))
        self.logger.logging_info('Porcentage de cruce de BB Suelo: {} %'.format(self.params.bbands_crossing_share * 100))
        self.logger.logging_info('Porcentage de incremento del mercado 24h: {} %'.format(self.params.market_state_24h_share * 100))
        self.logger.logging_info('Porcentage de incremento del mercado 12h: {} %'.format(self.params.market_state_12h_share * 100))
        self.logger.logging_info('Porcentage de incremento del mercado 5h: {} %'.format(self.params.market_state_5h_share * 100))
        self.logger.logging_info('Num Max Alts Tradear: {}'.format(self.params.max_alts_to_trade))
        self.logger.logging_info('Total de Ciclos: {}'.format(self.params.cycles))
        self.logger.logging_line_char("*")
        self.logger.logging_empty_line()

    def telegram_config_summary(self):
        summary = 'Iniciada nueva sesión de Bittbot!\n\nEstrategia: Análisis técnico (Bollinger Bands)'
        summary += '\nSaldo Invertido: {} {}'.format(self.params.full_invest_quantity, self.params.altstr)
        summary += '\nMargen de Perdidas: {} %'.format(self.params.stop_loss * 100)
        summary += '\nMargen de Beneficio: {} %'.format(self.params.profit_margin_alts * 100)
        summary += '\nSelección de Alts (min/max/vol): {}/{}/{}'.format(self.params.coin_selection_min_24_increment, self.params.coin_selection_max_24_increment, self.params.coin_selection_min_volume)
        summary += '\nPorcentage de cruce de BB Suelo: {} %'.format(self.params.bbands_crossing_share * 100)
        summary += '\nPorcentages incremento mercado (24/12/5): {}/{}/{}'.format(self.params.market_state_24h_share*100, self.params.market_state_12h_share*100, self.params.market_state_5h_share*100)
        summary += '\nNum Max Alts Tradear: {}'.format(self.params.max_alts_to_trade)
        summary += '\nTotal de Ciclos: {}'.format(self.params.cycles)
        self.telegram_bot.send_message(summary)
