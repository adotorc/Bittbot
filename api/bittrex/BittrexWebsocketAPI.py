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

import threading
from time import sleep

from bittrex_websocket.websocket_client import BittrexSocket
from utils.LoggingUtils import LoggingUtils


class BittrexWebsocketAPI(BittrexSocket):

    def __init__(self, callback, api):
        super().__init__()
        self.callback = callback
        self.api = api
        self.act_tick = None
        self.logger = LoggingUtils()
        self.connected = None
        thread = threading.Thread(target=self.run_server)
        thread.daemon = True
        thread.start()

    def run_server(self):
        while True:
            if not self.connect_websocket():
                self.logger.logging_warning("Se ha producido un error usando Websockets.")
            while self.connected:
                sleep(1)
            self.logger.logging_warning("Hemos perdido la connexión con el Websocket, reintentando en 10 segundos...")
            sleep(10)

    def connect_websocket(self):
        try:
            self.subscribe_to_summary_deltas()
            self.connected = True
        except Exception:
            self.connected = False
        return self.connected

    async def on_error(self, msg):
        print(msg)
        self.disconnect()
        self.connected = False

    async def on_public(self, msg):
        self.callback(msg)
