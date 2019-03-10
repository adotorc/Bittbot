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

import telebot

from utils import Config


class Telegram(object):

    def __init__(self):
        config = Config.read_telegram_config()
        self.bot = None
        if config is not None:
            self.bot = telebot.TeleBot(config["Token"])
            self.user_id = config["UserId"]
            self.chat_id = config["ChatId"]
            self.register_actions()

    def register_actions(self):
        # Handles all text messages that contains the commands '/start' or '/help'.
        @self.bot.message_handler(commands=['start', 'help'])
        def handle_start_help(message):
            self.start_help_command(message)

        @self.bot.message_handler(func=lambda message: True)
        def normal_message(message):
            self.refuse_interaction(message)

    def run(self):
        if self.bot is not None:
            self.bot.polling()

    def start_help_command(self, message):
        if not self.is_valid_user(message.from_user.id):
            self.bot.send_message(message.chat.id, "No tienes permisos para usar este bot")
            return
        self.bot.send_message(message.chat.id, "Bienvenidos al bot de Telegram de Bittbot.")
        self.bot.send_message(message.chat.id, "Te enviaré notificaciones cuando se produzcan eventos importantes en el bot.")

    def refuse_interaction(self, message):
        if not self.is_valid_user(message.from_user.id):
            self.bot.send_message(message.chat.id, "No tienes permisos para usar este bot")

    def send_message(self, text):
        if self.bot is not None:
            self.bot.send_message(self.chat_id, text)

    def is_valid_user(self, user_id):
        if user_id in [self.user_id]:
            return True
        return False
