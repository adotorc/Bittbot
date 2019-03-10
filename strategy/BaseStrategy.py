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

import abc

from api.Api import Api
from domain.InfoAlt import InfoAlt
from domain.MarketHistoric import MarketHistoric
from domain.Parameters import Parameters
from utils.Telegram import Telegram


class BaseStrategy(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def __init__(self, params: Parameters, api: Api, telegram_bot: Telegram, market_historic: MarketHistoric) -> None:
        pass

    @abc.abstractmethod
    def get_needed_parameters(self) -> None:
        pass

    @abc.abstractmethod
    def show_config_summary(self) -> None:
        pass

    @abc.abstractmethod
    def telegram_config_summary(self) -> None:
        pass

    @abc.abstractmethod
    def pre_cycles_iterator(self) -> None:
        pass

    @abc.abstractmethod
    def pre_coins_interator(self) -> None:
        pass

    @abc.abstractmethod
    def should_buy_coin(self, coin: InfoAlt) -> bool:
        pass

    @abc.abstractmethod
    def buy_order_completed(self, coin: InfoAlt) -> None:
        pass

    @abc.abstractmethod
    def sell_order_completed(self, coin: InfoAlt) -> None:
        pass

    @abc.abstractmethod
    def post_coins_interator(self) -> None:
        pass

    @abc.abstractmethod
    def post_cycles_iterator(self) -> None:
        pass

    @abc.abstractmethod
    def buy_order_placed_at_exchange(self, coin: InfoAlt) -> None:
        pass

    @abc.abstractmethod
    def sell_order_placed_at_exchange(self, coin: InfoAlt) -> None:
        pass
