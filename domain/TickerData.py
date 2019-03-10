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

class TickerData(object):
    def __init__(self):
        self.marketName = ""
        self.id = -1  # Poloniex specific
        self.high = 0.0
        self.low = 0.0
        self.volume = 0.0
        self.last = 0.0
        self.baseVolume = 0.0
        self.timeStamp = None
        self.bid = 0.0
        self.ask = 0.0
        self.openBuyOrders = 0
        self.openSellOrders = 0
        self.prevDay = 0.0
        self.created = None
        self.percentChange = 0.0
