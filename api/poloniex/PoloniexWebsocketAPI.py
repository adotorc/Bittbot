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

import websocket
import threading
import time
import json


class PoloniexWebsocketAPI(object):

    url = 'wss://api2.poloniex.com/'

    def __init__(self, callback, alt_id_relation):
        self.callback = callback
        self.alt_id_relation = alt_id_relation

        thread = threading.Thread(target=self.run_server)
        thread.daemon = True
        thread.start()

    def run_server(self):
        websocket.enableTrace(True)
        ws = websocket.WebSocketApp("wss://api2.poloniex.com", on_message=self.on_message, on_error=self.on_error, on_close=self.on_close)
        ws.on_open = self.on_open
        while True:
            try:
                ws.run_forever()
            except Exception:
                pass
            ws.close()
            time.sleep(5)

    def on_message(self, ws, message):
        ticker_alt = json.loads(message)
        if len(ticker_alt) == 3:
            alt = ticker_alt[2]
            coin_name = self.alt_id_relation[alt[0]]
            ticker = {coin_name: {}}
            ticker[coin_name]["id"] = str(alt[0])
            ticker[coin_name]["last"] = str(alt[1])
            ticker[coin_name]["lowestAsk"] = str(alt[2])
            ticker[coin_name]["highestBid"] = str(alt[3])
            ticker[coin_name]["percentChange"] = str(alt[4])
            ticker[coin_name]["baseVolume"] = str(alt[5])
            ticker[coin_name]["quoteVolume"] = str(alt[6])
            ticker[coin_name]["high24hr"] = str(alt[8])
            ticker[coin_name]["low24hr"] = str(alt[9])
            self.callback(ticker)

    def on_error(self, ws, error):
        pass

    def on_close(self, ws):
        pass

    def on_open(self, ws):
        # Subscribe to channel 1002 (Ticker Channel)
        ws.send(json.dumps({'command': 'subscribe', 'channel': 1002}))
