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

from api import Api
from api.bittrex import Bittrex
from api.poloniex import Poloniex
from domain import InfoAlt
from domain.TickerData import TickerData
from domain.Parameters import Parameters


class ConfigGenerator(object):

    def __init__(self, params: Parameters):
        self.params = params
        self.api = None
        self.main_alt = ""
        self.exchange = ""

    def run(self):
        self.exchange = self.ask_for_exchange()
        external_api = Bittrex.Bittrex("", "") if self.exchange == "Bittrex" else Poloniex.Poloniex("", "")
        self.api = Api.Api(self.params, external_api)

        self.main_alt = input('Introduce la alt base sobre la que quieres operar (ex: BTC): ')

        alts = self.populate_alts_from_ticker()
        if len(alts) == 0:
            print("[ERROR] No hay ningun par con la altcoin {}. Estas seguro que la has escrito bien?".format(self.main_alt))
            return
        selected = self.select_alts(alts)
        self.generate_config_file(selected)

    def ask_for_exchange(self):
        exchange = ''
        while exchange != "Bittrex" and exchange != "Poloniex":
            exchange = input('Introduce el exchange (Poloniex o Bittrex): ')
        return exchange

    def populate_alts_from_ticker(self):
        alts = []
        ticker = self.api.get_full_ticker()  # type: List[TickerData]
        for ticker_alt in ticker:
            if ticker_alt.marketName.find(self.main_alt) != 0:  # We want ALT_*** only, so we want it in position 0
                continue
            alt = InfoAlt.InfoAlt()
            alt.n_alt = ticker_alt.marketName
            alt.baseVolume = ticker_alt.baseVolume
            alt.high24hr = ticker_alt.high
            alt.low24hr = ticker_alt.low
            alt.percentChange = ticker_alt.percentChange
            alt.lowestAsk = ticker_alt.ask
            alt.highestBid = ticker_alt.bid
            alt.last = ticker_alt.last
            alts.append(alt)

        return alts

    def select_alts(self, alts):
        alts.sort(key=lambda x: x.baseVolume, reverse=True)
        selected = []
        print("\n***********************************************************************************************")
        print("*** Ahora se mostraran los pares de alts con tu moneda principal de mayor a menor Volumen. ***")
        print("*** Podras seleccionar las alts que quieras usar en la nueva config contestando s, n o p.   ***")
        print("*** \t[s]: si                                                                             ***")
        print("*** \t[n]: no                                                                             ***")
        print("*** \t[p]: parar de mostrar más alts                                                      ***")
        print("***********************************************************************************************\n")
        for coin in alts:
            res = input("[{}] Volumen: {}, percentage: {:.2f}%, 24high: {}, 24low: {}, last: {}? (s/n/p): ".format(coin.n_alt, coin.baseVolume, coin.percentChange, coin.high24hr, coin.low24hr, coin.last))
            if res == "p":
                break
            elif res == "s":
                pair_splitted = coin.n_alt.split('_')
                selected.append(pair_splitted[1])
            elif res == "n":
                continue
        return selected

    def generate_config_file(self, selected):
        new_config = {"Exchange": self.exchange, "Alt_Coin": self.main_alt, "Coins": selected, "Blacklisted_Coins": {}}
        print("")
        filename = input("Especifica el nombre del nuevo fichero de configuración:")
        if len(filename) == 0:
            return
        import json
        with open(filename, 'w') as outfile:
            json.dump(new_config, outfile, indent=4)
