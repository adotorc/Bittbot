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

class CoinMarketData(object):
    def __init__(self):
        self.alt_name = ""

        # Last Ticker information
        self.high24hr = 0.0
        self.low24hr = 0.0
        self.last = 0.0
        self.lowestAsk = 0.0
        self.highestBid = 0.0
        self.percentChange = 0.0
        self.baseVolume = 0.0

        # Candle Historic
        self.open = []
        self.high = []
        self.low = []
        self.close = []
        self.volume = []
        self.timestamp = []

        # Current Candle "Lasts" values to calculate the candle at the end
        self.current_candle_data = []
