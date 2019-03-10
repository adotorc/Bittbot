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
from typing import List

from api import Api
from api.bittrex import Bittrex
from api.poloniex import Poloniex
from domain import Parameters
from domain.TickerData import TickerData
from utils import Config
from utils import ConfigGenerator
from utils.LoggingUtils import LoggingUtils
from utils.ConfigTelegram import ConfigTelegram
from worker.BotWorker import BotWorker


class BittBot(object):
    def __init__(self) -> None:
        self.params = Parameters.Parameters()
        self.api = None
        self.apikey = None
        self.logger = LoggingUtils()

    def run(self):
        try:
            self.read_config()
            self.logger.logging_empty_line()
            self.logger.logging_info("BITTBOT version {}.{}.{}".format(Config.VERSION_MAJOR, Config.VERSION_MINOR, Config.VERSION_REVISION))

            self.remove_invalid_alt_pairs()
            self.params.funcionamiento = Config.get_strategy_type()  # Get operation type

            if self.params.funcionamiento == Config.API_KEYS_GENERATOR:
                Config.ask_user_api_keys()

            elif self.params.funcionamiento == Config.CONFIG_GENERATOR:
                config_generator = ConfigGenerator.ConfigGenerator(self.params)
                config_generator.run()

            elif self.params.funcionamiento == Config.CONFIG_TELEGRAM:
                config_telegram = ConfigTelegram()
                config_telegram.run()

            elif self.params.funcionamiento in [Config.STRATEGY_AUTO_MARGIN, Config.STRATEGY_MACD_RSI, Config.STRATEGY_MANUAL_INCREMENT_24H_ALL_ALTS, Config.STRATEGY_BBANDS]:
                bot = BotWorker(self.params, self.api)
                bot.run()

            else:
                self.logger.logging_error("[ERROR] {} No es una opción no válida.".format(self.params.funcionamiento))

        except Exception:
            self.logger.logging_exception("Bittbot Crashed")
            sys.exit(1)
        except KeyboardInterrupt:
            self.logger.logging_info("Bittbot interrumpido por teclado.")
            sys.exit(0)

    def read_config(self):
        self.logger.configure_logger()
        if Config.is_help_parameter_set():
            self.logger.print_help()
            sys.exit(1)

        self.params.coins_trader = []
        api_keys = Config.read_api_keys_config()

        self.params.config_file = Config.get_config_file()
        self.params.config = Config.read_config(self.params.config_file)
        if self.params.config["Exchange"] == "Bittrex":
            external_api = Bittrex.Bittrex(api_keys["Bittrex_ApiKey"], api_keys["Bittrex_ApiSecret"])
            self.params.api_key = api_keys["Bittrex_ApiKey"]
        elif self.params.config["Exchange"] == "Poloniex":
            external_api = Poloniex.Poloniex(api_keys["Poloniex_ApiKey"], api_keys["Poloniex_ApiSecret"])
            self.params.api_key = api_keys["Poloniex_ApiKey"]
        else:
            self.logger.logging_info("Exchange {} not supported.".format(self.params.config["Exchange"]))
            self.logger.logging_info("Valid options are Poloniex and Bittrex")
            sys.exit(1)
        self.api = Api.Api(self.params, external_api)
        self.params.altstr = self.params.config["Alt_Coin"]
        self.params.working_alts = self.params.config["WorkingAlts"]

    def remove_invalid_alt_pairs(self):
        ticker = self.api.get_full_ticker()  # type: List[TickerData]

        not_existing_alts = []
        for alt in self.params.working_alts:
            alt_pair = self.params.altstr + '_' + alt
            found = False
            for ticker_alt in ticker:
                if ticker_alt.marketName == alt_pair:
                    found = True
            if not found:
                not_existing_alts.append(alt)
                continue
        if len(not_existing_alts) > 0:
            self.logger.logging_line_char("-")
            for al in not_existing_alts:
                self.logger.logging_warning('LA COMBINACION {}_{} NO EXISTE EN EL EXCHANGE, ELIMINANDOLA DE LA LISTA'.format(self.params.altstr, al))
                self.params.working_alts.remove(al)
            self.logger.logging_line_char("-")
