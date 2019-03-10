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
from threading import Timer
from datetime import datetime, timedelta
from typing import Dict, List

from domain.TickerData import TickerData
from domain.CoinMarketData import CoinMarketData
from utils.LoggingUtils import LoggingUtils
from utils import RepeatedTimer as timer


class MarketHistoric(object):
    def __init__(self):
        self.market_historic = {}  # type: Dict[str, CoinMarketData]
        self.logger = LoggingUtils()
        # Candle data variables
        self.store_candle_data = False
        self.candle_time_minutes = 5
        self.update_market_timer = None

    def get_coin_market_data(self, coin_pair_name) -> CoinMarketData:
        if coin_pair_name in self.market_historic:
            return self.market_historic[coin_pair_name]

    def set_coin_market_data(self, coin_pair_name, coin_market_data: CoinMarketData) -> None:
        self.market_historic[coin_pair_name] = coin_market_data

    '''
    Sets only the historic values of open,close,high,low,volume,timestamp. Current ticker data and current candle
    calculation data is preserved. Useful to update only the historic candle data. 
    '''
    def set_coin_market_historic_only(self, coin_pair_name, coin_market_data: CoinMarketData) -> None:
        current_coin_market_data = self.market_historic[coin_pair_name]
        for candle_data in current_coin_market_data.current_candle_data:
            coin_market_data.current_candle_data.append(candle_data)
        coin_market_data.high24hr = current_coin_market_data.high24hr
        coin_market_data.low24hr = current_coin_market_data.low24hr
        coin_market_data.last = current_coin_market_data.last
        coin_market_data.lowestAsk = current_coin_market_data.lowestAsk
        coin_market_data.highestBid = current_coin_market_data.highestBid
        coin_market_data.percentChange = current_coin_market_data.percentChange
        coin_market_data.baseVolume = current_coin_market_data.baseVolume
        self.market_historic[coin_pair_name] = coin_market_data

    '''
    Fill all the information for every alt in the ticker.
    If self.store_candle_data is set to True, append every last from the ticker to the "current_candle_data" property, to be able to calculate candles.
    '''
    def process_ticker(self, partial_ticker: List[TickerData], show_ticker) -> None:
        if show_ticker:
            self.logger.logging_line_char('-')
            self.logger.logging_info('FECHA TICKER: {} '.format(time.strftime("%d/%m/%y %H:%M:%S")))
            self.logger.logging_line_char('-')
        for ticker_alt in partial_ticker:
            self.add_coin_ticker_data(ticker_alt.marketName, ticker_alt.high, ticker_alt.low, ticker_alt.percentChange,
                                      ticker_alt.baseVolume, ticker_alt.ask, ticker_alt.bid, ticker_alt.last)
            if self.store_candle_data:
                self.append_current_candle_data(ticker_alt.marketName, ticker_alt.last)

    def add_coin_ticker_data(self, coin_name, high24hr, low24hr, percent_change, base_volume, lowest_ask, highest_bid, last) -> None:
        if coin_name not in self.market_historic:
            cmd = CoinMarketData()
            cmd.alt_name = coin_name
            self.market_historic[coin_name] = cmd
        coin = self.market_historic[coin_name]
        coin.high24hr = float(high24hr)
        coin.low24hr = float(low24hr)
        coin.percentChange = float(percent_change)
        coin.baseVolume = float(base_volume)
        coin.lowestAsk = float(lowest_ask)
        coin.highestBid = float(highest_bid)
        coin.last = float(last)

    ##############################################
    #           Candle Calculations              #
    ##############################################

    def start_candle_calculations(self, candle_time_minutes: int) -> None:
        self.store_candle_data = True
        self.candle_time_minutes = candle_time_minutes
        self.program_next_candle_timer()

    def program_next_candle_timer(self) -> None:
        # Syncrhonize the first candle calculation to the next 'self.candle_time_minutes' minutes to follow Exchanges calculations
        sync_timer = Timer(self.get_seconds_until_next_candle(), self.synchronized_market_update)
        sync_timer.daemon = True
        sync_timer.start()

    def synchronized_market_update(self) -> None:
        candle_seconds = self.candle_time_minutes * 60
        self.update_market_timer = timer.RepeatedTimer(candle_seconds, self.close_and_calculate_candle)
        self.close_and_calculate_candle()

    def append_current_candle_data(self, coin_pair_name, last) -> None:
        self.market_historic[coin_pair_name].current_candle_data.append(last)

    def close_and_calculate_candle(self) -> None:
        for coin_pair_name in self.market_historic:
            coin = self.market_historic[coin_pair_name]
            if len(coin.current_candle_data) == 0:
                self.logger.logging_warning("Coin {} doesn't have any candle data!!!".format(coin.alt_name))
                return
            # Write the calculated values for the new candle to the end of each array and Reset current candle data
            if len(coin.close) == 0:
                # We may reach this point before the coin gets historic value, so we use the first data as open. This
                # can happen at the beggining of the program execution
                coin.open.append(float(coin.current_candle_data[0]))
            else:
                coin.open.append(float(coin.close[-1]))
            coin.high.append(float(max(coin.current_candle_data)))
            coin.low.append(float(min(coin.current_candle_data)))
            coin.close.append(float(coin.current_candle_data[-1]))
            coin.volume.append(float(coin.baseVolume))
            coin.current_candle_data = []

    def get_seconds_until_next_candle(self) -> int:
        now = datetime.now()
        minute = now.minute + 1
        for next_min in range(0, (60 + self.candle_time_minutes), self.candle_time_minutes):
            if next_min >= minute:
                if next_min == 60:
                    next_min = 0
                    target_time = now.replace(minute=next_min, second=0) + timedelta(hours=1)
                else:
                    target_time = now.replace(minute=next_min, second=0)
                delta = target_time - now
                return delta.seconds
