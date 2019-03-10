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

from typing import List

from domain.InfoAlt import InfoAlt


class Parameters(object):
    def __init__(self):
        # Config filename used
        self.config_file = ""  # type: str

        # Api key in use
        self.api_key = ""  # type: str

        # Array of InfoAlt with the coins that will be used to trade
        self.coins_trader = None  # type: List[InfoAlt]

        # Strategy to use (examples: "A", "B", "1", "2",... )
        self.funcionamiento = ""  # type: str

        # Main Coin name (ex: BTC). All pairs will be altstr_ALTCOIN (ex: BTC_NEO)
        self.altstr = ""  # type: str

        # Money to invest in each alt coin
        self.saldo_inv = 0  # type: float

        # Quantity of money to invest in the bot amount all alts
        self.full_invest_quantity = 0  # type: float

        # Config read from file
        self.config = None

        # String list of alts to works with, read from config file (ex: ['LTC', 'BCC', 'NEO'])
        self.working_alts = []  # type: List[str]

        # Max number of cycles
        self.cycles = 0  # type: int

        ##############################################
        #         Global Strategy parameters         #
        ##############################################
        self.margin_increment_24h = 0  # type: float
        self.current_margin_increment = 0  # type: float
        self.stop_loss = 0  # type: float
        self.profit_margin_alts = 0.0  # type: float
        self.max_alts_to_trade = 0  # type: int

        ##############################################
        #    MACD + RSI Strategy custom parameters   #
        ##############################################
        self.macd_short_period = None  # type: int
        self.macd_long_period = None  # type: int
        self.macd_smoothing = None  # type: int

        ##############################################
        # Bollinger Bands Strategy custom parameters #
        ##############################################
        self.coin_selection_min_volume = 0  # type: int
        # Those % are in multiply value (ie: 10% -> 0.1)
        self.bbands_crossing_share = 0  # type: float
        self.market_state_24h_share = 0  # type: float
        self.market_state_12h_share = 0  # type: float
        self.market_state_5h_share = 0  # type: float
        # Those % are in full value (ie: 10% -> 10)
        self.coin_selection_min_24_increment = 0  # type: float
        self.coin_selection_max_24_increment = 0  # type: float
