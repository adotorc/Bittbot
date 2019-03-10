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

class InfoAlt(object):
    def __init__(self):
        # Name of the pair to work with (Main Coin and Alt Name) using Poloniex Format (ex: BTC_NEO)
        self.n_alt = ''  # type: str

        # Price at which we bought the alt (price in main coin)
        self.last_buy_price = 0.0  # type: float

        # Price at which we sold the alt (price in main coin)
        self.last_sell_price = 0.0  # type: float

        # Inversion using main coin as value (ex: 0.02 BTC)
        self.inv_last_compra = 0.0  # type: float

        # Inversion using alt coin as value (ex: 3.25 NEO). So if we want the inversion in main coin, we have to
        # multiply this value for the price that we sell it (last_sell_price)
        self.inv_last_venta = 0.0  # type: float

        # State of the last operation done with this Alt. Do not translate to english as it's used on logs :(
        # Valid values: 'NO_ORDER', 'BUY', 'WAIT_BUY', 'SELL', 'WAIT_SELL'
        self.operation_type = 'NO_ORDER'  # type: str

        # Identifier of the last order put on the Exchange (order id)
        self.num_last_orden = ''  # type: str

        # Total Benefit for current Alt
        self.beneficio_total = 0.0  # type: float

        # Last Candle which we used to buy this altcoin (to avoid buying more than once in the same candle on Technical Analysis Strategies)
        self.last_used_candle = 0  # type: int
